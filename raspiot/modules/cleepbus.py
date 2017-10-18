#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.raspiot import RaspIotModule
from raspiot.libs.externalbus import PyreBus
from raspiot.libs.hostname import Hostname
from raspiot import __version__ as VERSION
import raspiot
import time

__all__ = [u'Cleepbus']


class Cleepbus(RaspIotModule):

    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Enable communications between all your Cleep devices through your home network'
    MODULE_LOCKED = True
    MODULE_URL = None
    MODULE_TAGS = ['bus']
    MODULE_COUNTRY = 'any'

    def __init__(self, bus, debug_enabled, join_event):
        """
        Constructor

        Args:
            bus (MessageBus): MessageBus instance
            debug_enabled (bool): flag to set debug level to logger
        """
        RaspIotModule.__init__(self, bus, debug_enabled, join_event)

        #members
        #self.external_bus = PyreBus(self.__on_message_received, self.__on_peer_connected, self.__on_peer_disconnected, debug_enabled, None)
        self.external_bus = PyreBus(self.__on_message_received, self.__on_peer_connected, self.__on_peer_disconnected, True, None)
        self.devices = {}
        self.hostname = Hostname()

    def _configure(self):
        """
        Configure module
        """
        if self.external_bus:
            version = VERSION
            hostname = self.hostname.get_hostname()
            #TODO handle port when security module developped
            port = 80
            #TODO handle SSL option when credentials supported in cleepdesktop
            ssl = False
            #TODO get mac address, useless for now
            mac = 'xx:xx:xx:xx:xx:xx'
            self.external_bus.configure(version, mac, hostname, port, ssl, False)

    def _stop(self):
        """
        Stop module
        """
        #stop bus
        if self.external_bus:
            self.external_bus.stop()

    def _custom_process(self):
        """
        Custom process for cleep bus: get new message on external bus
        """
        self.external_bus.run_once()

    def get_network_devices(self):
        """
        Return all Cleep devices found on the network

        Returns:
            dict: devices
        """
        #TODO return list of online devices
        return self.devices

    def __on_message_received(self, message):
        """
        Handle received message from external bus

        Args:
            message (ExternalBusMessage): external bus message instance
        """
        self.logger.debug('Message received on external bus: %s' % message)
        if message.event:
            #broadcast event to all modules
            self.send_event(message.event, message.params)

        else:
            #command received
            #TODO not implemented and useful ?
            pass

    def __on_peer_connected(self, peer_id, infos):
        """
        Device is connected

        Args:
            peer_id (string): peer identifier
            infos (dict): device informations (ip, port, ssl...)
        """
        self.logger.debug('Peer %s connected: %s' % (peer_id, infos))

    def __on_peer_disconnected(self, peer_id):
        """
        Device is disconnected
        """
        self.logger.debug('Peer %s disconnected' % peer_id)

    def event_received(self, event):
        """
        Watch for specific event

        Args:
            event (MessageRequest): event data
        """
        #handle received event and transfer it to external buf if necessary
        self.logger.debug('Received event %s' % event.event)


