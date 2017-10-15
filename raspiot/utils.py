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

class BusNotReady(Exception):
    def __str__(self):
        return u'Bus is not ready yet. Please handle system.application.ready event before sending events.'

class InvalidModule(Exception):
    def __init__(self, module):
        self.module = module
    def __str__(self):
        return u'Invalid module %s (not loaded or unknown)' % module

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

    def __str__(self):
        return u'{error:%r, message:%s, data:%s}' % (self.error, self.message, unicode(self.data))

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
       - a device uuid
       - a startup flag that indicates this event was sent during raspiot startup
    """
    def __init__(self):
        self.command = None
        self.event = None
        self.params = {}
        self.to = None
        self.from_ = None
        self.uuid = None

    def __str__(self):
        if self.command:
            return u'{command:%s, params:%s, to:%s}' % (self.command, unicode(self.params), self.to)
        elif self.event:
            return u'{event:%s, params:%s, to:%s}' % (self.event, unicode(self.params), self.to)
        else:
            return u'Invalid message'

    def is_broadcast(self):
        """
        Return True if the request is broadcast
        """
        if self.to==None:
            return True
        else:
            return False

    def to_dict(self, startup=False):
        """
        Return useful dict with data filled
        Internaly usage
        @raise InvalidMessage if message is not valid
        """
        if self.command:
            return {u'command':self.command, u'params':self.params, u'from':self.from_}
        elif self.event:
            return {u'event':self.event, u'params':self.params, u'startup':startup, u'uuid':self.uuid}
        else:
            raise InvalidMessage()

