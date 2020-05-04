#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file shares some constants and classes
"""

from raspiot.exception import InvalidMessage

__all__ = [u'CORE_MODULES', u'CATEGORIES',
           u'ExecutionStep', u'MessageResponse', u'MessageRequest']

"""
CONSTANTS
"""
CORE_MODULES = [
    u'system',
    u'audio',
    u'network',
    u'cleepbus',
    u'parameters'
]

class CATEGORIES(object):
    """
    Cleep application categories
    """
    #generic application
    APPLICATION = u'APPLICATION'
    #mobile application for car, bike, hiking...
    MOBILE = u'MOBILE'
    #application to configure and use hardware (soundcard, display...)
    DRIVER = u'DRIVER'
    #home automation application (shutter, light...)
    HOMEAUTOMATION = u'HOMEAUTOMATION'
    #media application (music player, video player...)
    MEDIA = u'MEDIA'
    #application based on online service (sms broker, weather provider...)
    SERVICE = u'SERVICE'

    ALL = [u'APPLICATION', u'MOBILE', u'DRIVER', u'HOMEAUTOMATION', u'MEDIA', u'SERVICE']

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

class MessageResponse(object):
    """
    Object that holds message response
    A response is composed of:
     - an error flag: True if error, False otherwise
     - a message: a message about request
     - some data: data returned by the request
    """
    def __init__(self):
        self.error = False
        self.message = u''
        self.data = None
        self.broadcast = False

    def __str__(self):
        return u'{error:%r, message:"%s", data:%s, broadcast:%r}' % (
            self.error,
            self.message,
            str(self.data),
            self.broadcast
        )

    def to_dict(self):
        """
        Return message response
        """
        return {u'error':self.error, u'message':self.message, u'data':self.data}

class MessageRequest(object):
    """
    Object that holds message request
    A message request is composed of:
     - in case of a command:
       - a command name
       - command parameters
       - the command sender
     - in case of an event:
       - an event name
       - event parameters
       - core_event flag to say if event is a core event (and may not be pushed away from device)
       - a device id
       - a startup flag that indicates this event was sent during raspiot startup
       - peer infos if message comes from external device
    """
    def __init__(self):
        """
        Constructor
        """
        self.command = None
        self.event = None
        self.core_event = False
        self.params = {}
        self.to = None
        self.sender = None
        self.device_id = None
        self.peer_infos = None

    def __str__(self):
        """
        Stringify function
        """
        if self.command:
            return u'{command:%s, params:%s, to:%s, sender:%s}' % (
                self.command,
                str(self.params),
                self.to, self.sender
            )
        elif self.event:
            return u'{event:%s, core_event:%s, params:%s, to:%s, device_id:%s, peer_infos:%s}' % (
                self.event,
                self.core_event,
                str(self.params),
                self.to,
                self.device_id,
                self.peer_infos
            )

        return u'Invalid message'

    def is_broadcast(self):
        """
        Return broadcast status

        Return:
            bool: True if the request is broadcast
        """
        return True if self.to is None else False

    def is_external_event(self):
        """
        Return True if event comes from external device

        Return:
            bool: True if event comes from external device
        """
        return True if self.peer_infos is not None else False

    def to_dict(self, startup=False):
        """
        Convert message request to dict object

        Params:
            startup (bool): True if the message is startup message

        Raise:
            InvalidMessage if message is not valid
        """
        if self.command:
            # command
            return {
                u'command': self.command,
                u'params': self.params,
                u'to': self.to,
                u'sender': self.sender,
                u'broadcast': self.is_broadcast()
            }

        elif self.event and not self.peer_infos:
            # internal event
            return {
                u'event': self.event,
                u'params': self.params,
                u'startup': startup,
                u'device_id': self.device_id,
                u'sender': self.sender
            }

        elif self.event and self.peer_infos:
            # external event
            return {
                u'event': self.event,
                u'params': self.params,
                u'startup': False,
                u'device_id': None,
                u'sender': u'PEER',
                u'peer_infos': self.peer_infos
            }

        else:
            raise InvalidMessage()

