#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = [u'CommandError', u'CommandInfo', u'NoResponse', u'NoMessageAvailable', u'InvalidParameter', u'MissingParameter', 
           u'InvalidMessage', u'Unauthorized', u'BusError', u'MessageResponse', u'MessageRequest']

class CommandError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return u'%s' % self.value

class CommandInfo(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return u'%s' % self.value

class NoResponse(Exception):
    def __init__(self, to, timeout, value):
        self.value = value
        self.timeout = timeout
        self.to = to
    def __str__(self):
        return u'No response from %s (%d seconds) for request: %s' % (self.to, self.timeout, self.value)

class NoMessageAvailable(Exception):
    def __str__(self):
        return u'No message available'

class ResourceNotAvailable(Exception):
    def __init__(self, resource):
        self.resource = resource
    def __str__(self):
        return u'Resource %s not available' % self.resource

class NoCityFound(Exception):
    def __str__(self):
        return u'No city found'

class InvalidParameter(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return u'%s' % self.value

class MissingParameter(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return u'%s' % self.value

class InvalidMessage(Exception):
    def __str__(self):
        return u'Invalid message'

class InvalidModule(Exception):
    def __init__(self, module):
        self.module = module
    def __str__(self):
        return u'Invalid module %s (not loaded or unknown)' % self.module

class Unauthorized(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return u'%s' % self.value

class BusError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return u'%s' % self.value

class MessageResponse():
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
        return u'{error:%r, message:%s, data:%s, broadcast:%r}' % (self.error, self.message, unicode(self.data), self.broadcast)

    def to_dict(self):
        """ 
        Return message response
        """
        return {u'error':self.error, u'message':self.message, u'data':self.data}

class MessageRequest():
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
        self.params = {}
        self.to = None
        self.from_ = None
        self.device_id = None
        self.peer_infos = None

    def __str__(self):
        """
        Stringify function
        """
        if self.command:
            return u'{command:%s, params:%s, to:%s}' % (self.command, unicode(self.params), self.to)
        elif self.event:
            return u'{event:%s, params:%s, to:%s, peer_infos:%s}' % (self.event, unicode(self.params), self.to, self.peer_infos)
        else:
            return u'Invalid message'

    def is_broadcast(self):
        """
        Return broadcast status

        Return:
            bool: True if the request is broadcast
        """
        if self.to==None:
            return True
        else:
            return False

    def is_external_event(self):
        """
        Return True if event comes from external device

        Return:
            bool: True if event comes from external device
        """
        if self.peer_infos is not None:
            return True

        return False

    def to_dict(self, startup=False):
        """
        Convert message request to dict object

        Params:
            startup (bool): True if the message is startup message

        Raise:
            InvalidMessage if message is not valid
        """
        if self.command:
            return {u'command':self.command, u'params':self.params, u'from':self.from_, u'broadcast': self.is_broadcast()}

        elif self.event:
            if not self.peer_infos:
                return {u'event':self.event, u'params':self.params, u'startup':startup, u'device_id':self.device_id, u'from':self.from_}
            else:
                return {u'event':self.event, u'params':self.params, u'startup':False, u'device_id':None, u'from':u'PEER', u'peer_infos':self.peer_infos}

        else:
            raise InvalidMessage()
