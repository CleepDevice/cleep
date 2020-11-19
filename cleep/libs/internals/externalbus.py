#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.common import MessageRequest
import logging
import uuid
from threading import Event

class ExternalBus():
    """
    ExternalBus base class

    External bus is only based on event handling.
    This way of doing forces developper to handle async requests only.
    This also reduces bus complexity.

    This class provides:
        - peers list handling
        - base bus functions canvas (not implementation)
        - internal logger with debug enabled or not
    """

    COMMAND_RESPONSE_EVENT = 'external.command.response'

    def __init__(self, on_message_received, on_peer_connected, on_peer_disconnected, debug_enabled, crash_report):
        """
        Constructor

        Args:
            on_message_received (callback): function called when message is received on bus
            on_peer_connected (callback): function called when new peer connected
            on_peer_disconnected (callback): function called when peer is disconnected
            debug_enabled (bool): True if debug is enabled
            crash_report (CrashReport): crash report instance
        """
        # members
        self.debug_enabled = debug_enabled
        self.crash_report = crash_report
        self._on_message_received = on_message_received
        self.on_peer_connected = on_peer_connected
        self.on_peer_disconnected = on_peer_disconnected
        self.__command_events = {}

        # logging
        self.logger = logging.getLogger(self.__class__.__name__)
        if self.debug_enabled:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.WARN)

    def run(self):
        """
        Run external bus process

        Warning:
            Must be implemented
        """
        raise NotImplementedError('run function is not implemented in "%s"' % self.__class__.__name__)

    def run_once(self):
        """
        Run external bus process once

        Warning:
            Must be implemented
        """
        raise NotImplementedError('run_once function is not implemented in "%s"' % self.__class__.__name__)

    def __ack_command_message(self, message):
        """
        Ack command message if it is a waiting command

        Args:
            message (MessageRequest): message request

        Returns:
            bool: True if command message was acked, False otherwise
        """
        self.logger.info('Ack_command_message: %s' % message)
        if message.command_uuid in self.__command_events:
            if self._command_events[message.command_uuid]['event'].is_set():
                # timeout already occured, we can delete command event
                self.logger.info('=====> delete command event [1]')
                del self.__command_events[message.command_uuid]
            else:
                # timeout not occured, set event. It will be deleted later after event response is sent
                self.__commands_events[message.command_uuid]['event'].set()
            return True

        return False

    def on_message_received(self, peer_id, message):
        """
        On message received event

        Args:
            peer_id (string): peer identifier
            message (MessageRequest): message request
        """
        if not self.__ack_command_message(message):
            # it was not a command message response, process message
            self._on_message_received(peer_id, message)

    def send_command_response(self, request, response):
        """
        Send command response to peer

        Args:
            request (MessageRequest): message request
            response (MessageResponse): message response
        """
        # convert response to request
        self.logger.trace('request: %s' % request)
        self.logger.trace('response: %s' % response)
        message = MessageRequest()
        message.event = ExternalBus.COMMAND_RESPONSE_EVENT
        message.params = response.to_dict() # store message response in event params
        message.command_uuid = request.command_uuid
        message.peer_infos = request.peer_infos

        # and send created request
        self.logger.info('Send command response: %s' % message)
        self._send_message(message)

    def send_message(self, message, timeout=5.0):
        """
        Send message (broadcast or to recipient) to outside

        Args:
            message (MessageRequest): message request instance
        """
        if message.is_command():
            # it's a command, fill request with command identifier and timeout
            message.command_uuid = str(uuid.uuid4())
            message.timeout = timeout
            self.__command_events[message.command_uuid] = {
                'event': Event(),
                'response': None
            }

            self._send_message(message)

            timeout_occured = self.__command_events[message.command_uuid]['event'].wait(timeout)
            self.__command_events[message.command_uuid]['event'].set()
            response = self.__command_events[message.command_uuid]['response']
            if not timeout_occured:
                # command response received in time, clean command event
                self.logger.info('=====> delete command event [2]')
                del self.__command_events[message.command_uuid]
            return response

        else:
            # it's an event
            if message.peer_infos and message.peer_infos.peer_uuid:
                self._send_message(message)
            else:
                self._broadcast_message(message)

    def _broadcast_message(self, message):
        """
        broadcast event message to all connected peers

        Args:
            message (MessageRequest): message instance

        Warning:
            Must be implemented
        """
        raise NotImplementedError('broadcast_message function is not implemented "%s"' % self.__class__.__name__)

    def _send_message(self, message):
        """
        Send event message to specified peer

        Args:
            message (MessageRequest): message instance

        Warning:
            Must be implemented
        """
        raise NotImplementedError('send_message function is not implemented "%s"' % self.__class__.__name__)

