#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file shares some constants and classes
"""

from cleep.exception import InvalidMessage
import copy

__all__ = ['CORE_MODULES', 'CATEGORIES', 'PeerInfos',
           'ExecutionStep', 'MessageResponse', 'MessageRequest']

"""
CONSTANTS
"""
CORE_MODULES = [
    'system',
    'update',
    'audio',
    'network',
    'cleepbus',
    'parameters'
]

class CATEGORIES(object):
    """
    Cleep application categories
    """
    #generic application
    APPLICATION = 'APPLICATION'
    #mobile application for car, bike, hiking...
    MOBILE = 'MOBILE'
    #application to configure and use hardware (soundcard, display...)
    DRIVER = 'DRIVER'
    #home automation application (shutter, light...)
    HOMEAUTOMATION = 'HOMEAUTOMATION'
    #media application (music player, video player...)
    MEDIA = 'MEDIA'
    #application based on online service (sms broker, weather provider...)
    SERVICE = 'SERVICE'

    ALL = ['APPLICATION', 'MOBILE', 'DRIVER', 'HOMEAUTOMATION', 'MEDIA', 'SERVICE']

    def __init__(self):
        pass





class ExecutionStep(object):
    """
    Cleep execution steps
    """
    #boot step (init logger, brokers...)
    BOOT = 0
    #init modules (constructor)
    INIT = 1
    #configure modules (_configure)
    CONFIG = 2
    #application and all modules are running
    RUN = 3
    #stopping cleep
    STOP = 4

    def __init__(self):
        self.step = self.BOOT





class PeerInfos():
    """
    Stores peer informations
    """
    def __init__(self,
                 uuid=None,
                 ident=None,
                 hostname=None,
                 ip=None,
                 port=80,
                 ssl=False,
                 macs=None,
                 cleepdesktop=False
                ):
        """
        Constructor

        Args:
            uuid (string): peer uuid provided by cleep
            ident (string): peer identifier provided by external bus
            hostname (string): peer hostname
            ip (string): peer ip
            port (int): peer access port
            ssl (bool): peer has ssl enabled
            macs (list): list of macs addresses
            cleepdesktop (bool): is cleepdesktop peer

        Notes:
            Uuid is mandatory because device can change identifier after each connection.

            Id is the identifier provided by your external bus implementation.

            Hostname is mandatory because it is used to display user friendly peer name

            Mac addresses are mandatory because they are used to identify a peer that has been reinstalled (and
            has lost its previous uuid)
        """
        self.uuid = uuid
        self.ident = ident
        self.hostname = hostname
        self.ip = ip
        self.port = port
        self.ssl = ssl
        self.macs = macs
        self.cleepdesktop = cleepdesktop
        self.online = False
        self.extra = {}

    def to_dict(self, with_extra=False):
        """
        Return peer infos as dict

        Args:
            with_extra (bool): add extra data

        Returns:
            dict: peer infos
        """
        out = {
            'uuid': self.uuid,
            'ident': self.ident,
            'hostname': self.hostname,
            'ip': self.ip,
            'port': self.port,
            'ssl': self.ssl,
            'macs': self.macs,
            'cleepdesktop': self.cleepdesktop,
            'online': self.online,
        }
        with_extra and out.update({'extra': self.extra})
        return out

    def __str__(self):
        """
        To string method

        Returns:
            string: peer infos as string
        """
        infos = self.to_dict(True)
        infos['online'] = self.online
        return '%s' % infos

    def fill_from_dict(self, peer_infos):
        """
        Fill infos from dict

        Args:
            peer_infos (dict): peer informations
        """
        if not isinstance(peer_infos, dict):
            raise Exception('peer_infos must be a dict')
        self.uuid = peer_infos.get('uuid', None)
        self.ident = peer_infos.get('ident', None)
        self.hostname = peer_infos.get('hostname', None)
        self.ip = peer_infos.get('ip', None)
        self.port = peer_infos.get('port', None)
        self.ssl = peer_infos.get('ssl', False)
        self.macs = peer_infos.get('macs', None)
        self.cleepdesktop = peer_infos.get('cleepdesktop', False)
        self.extra = copy.deepcopy(peer_infos.get('extra', {}))





class MessageResponse(object):
    """
    Object that holds message response

    A response is composed of:

        * an error flag: True if error, False otherwise
        * a message: a message about request
        * some data: data returned by the request

    """
    def __init__(self, error=False, message='', data=None, broadcast=False):
        """
        Constructor

        Args:
            error (bool): error flag (default False)
            message (string): response message (default empty string)
            data (any): response data (default None)
            broadcast (bool): response comes from broadcast (default False)
        """
        self.error = error
        self.message = message
        self.data = data
        self.broadcast = broadcast

    def __str__(self):
        """
        Stringify
        """
        return '{error:%r, message:"%s", data:%s, broadcast:%r}' % (
            self.error,
            self.message,
            str(self.data),
            self.broadcast
        )

    def to_dict(self):
        """
        Return message response
        """
        return {'error':self.error, 'message':self.message, 'data':self.data}





class MessageRequest(object):
    """
    Object that holds message request

    A message request is composed of:

        * in case of a command:

            * a command name
            * command parameters
            * the command sender

        * in case of an event:

            * an event name
            * event parameters
            * propagate flag to say if event can be propagated out of the device
            * a device id
            * a startup flag that indicates this event was sent during cleep startup

    Attribute peer_infos is filled when message comes from oustide. This field must also be filled when
    message is intented to be sent to outside.

    Members:
        command (string): command name
        event (string): event name
        propagate (bool): True if event can be propagated out of the device [event only]
        params (dict): list of event or command parameters
        to (string): message module recipient
        sender (string): message sender [command only]
        device_id (string): internal virtual device identifier [event only]
        peer_infos (PeerInfos): peer informations. Must be filled if message comes from outside the device

    Notes:
        A message cannot be a command and an event, priority to command if both are specified.
    """
    def __init__(self):
        """
        Constructor
        """
        self.command = None
        self.event = None
        self.propagate = False
        self.params = {}
        self.to = None
        self.sender = None
        self.device_id = None
        self.peer_infos = None
        self.command_uuid = None
        self.timeout = None

    def __str__(self):
        """
        Stringify function
        """
        if self.command:
            return '{command:%s, params:%s, to:%s, sender:%s, device_id:%s, peer_infos:%s, command_uuid:%s, timeout:%s}' % (
                self.command,
                str(self.params),
                self.to,
                self.sender,
                self.device_id,
                self.peer_infos.to_dict() if self.peer_infos else None,
                self.command_uuid,
                self.timeout,
            )
        elif self.event:
            return '{event:%s, propagate:%s, params:%s, to:%s, device_id:%s, peer_infos:%s, command_uuid:%s}' % (
                self.event,
                self.propagate,
                str(self.params),
                self.to,
                self.device_id,
                self.peer_infos.to_dict() if self.peer_infos else None,
                self.command_uuid,
            )

        return 'Invalid message'

    def is_broadcast(self):
        """
        Return broadcast status

        Returns:
            bool: True if the request is broadcast
        """
        return True if self.to is None else False

    def is_command(self):
        """
        Return true if message is a command. If not it is an event

        Returns:
            bool: True if message is a command, otherwise it is an event
        """
        return True if self.command else False

    def is_external_event(self):
        """
        Return True if event comes from external device

        Returns:
            bool: True if event comes from external device
        """
        return True if self.peer_infos is not None else False

    def to_dict(self, startup=False, external_sender=None):
        """
        Convert message request to dict object

        Params:
            startup (bool): True if the message is startup message
            external_sender (string): specify module name that handles message from external bus

        Raise:
            InvalidMessage if message is not valid
        """
        if self.command and not self.peer_infos:
            # internal command
            return {
                'command': self.command,
                'params': self.params,
                'to': self.to,
                'sender': self.sender,
                'broadcast': self.is_broadcast(),
            }

        elif self.event and not self.peer_infos:
            # internal event
            return {
                'event': self.event,
                'params': self.params,
                'startup': startup,
                'device_id': self.device_id,
                'sender': self.sender,
            }

        elif self.event and self.peer_infos:
            # external event
            return {
                'event': self.event,
                'params': self.params,
                'startup': False,
                'device_id': None,
                'sender': external_sender,
                'peer_infos': self.peer_infos.to_dict(),
                'command_uuid': self.command_uuid,
            }

        elif self.command and self.peer_infos:
            # external command
            return {
                'command': self.command,
                'params': self.params,
                'to': self.to,
                'sender': external_sender,
                'broadcast': self.is_broadcast(),
                'peer_infos': self.peer_infos.to_dict(),
                'command_uuid': self.command_uuid,
                'timeout': self.timeout,
            }

        else:
            raise InvalidMessage()

    def fill_from_message(self, message):
        """
        Fill instance from other message

        Args:
            message (MessageRequest): message request instance
        """
        if not isinstance(message, MessageRequest):
            raise Exception('Parameter "message" must be a MessageRequest instance')

        self.command = message.command
        self.event = message.event
        self.propagate = message.propagate
        self.params = copy.deepcopy(message.params)
        self.to = message.to
        self.sender = message.sender
        self.device_id = message.device_id
        self.peer_infos = None
        self.command_uuid = message.command_uuid
        if message.peer_infos:
            self.peer_infos = PeerInfos()
            self.peer_infos.fill_from_peer_infos(message.peer_infos)

    def fill_from_dict(self, message):
        """
        Fill instance from other message

        Args:
            message (dict): message request infos
        """
        if not isinstance(message, dict):
            raise Exception('Parameter "message" must be a dict')

        self.command = message.get('command', None)
        self.event = message.get('event', None)
        self.propagate = message.get('propagate', False)
        self.params = copy.deepcopy(message.get('params', {}))
        self.to = message.get('to', None)
        self.sender = message.get('sender', None)
        self.device_id = message.get('device_id', None)
        self.command_uuid = message.get('command_uuid', None)
        self.timeout = message.get('timeout', 5.0)
        self.peer_infos = None
        if message.get('peer_infos', None):
            self.peer_infos = PeerInfos()
            self.peer_infos.fill_from_dict(message.get('peer_infos'))

