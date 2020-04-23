#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cleep exceptions
"""

__all__ = [u'CommandError', u'CommandInfo', u'NoResponse', u'NoMessageAvailable', u'ResourceNotAvailable',
           u'InvalidParameter', u'MissingParameter', u'InvalidMessage', u'InvalidModule', u'Unauthorized',
           u'BusError', u'ForcedException']

class CommandError(Exception):
    """
    Exception used when module command failed.
    Message will be toasted on UI.
    """
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message
    def __str__(self):
        return u'%s' % self.message

class CommandInfo(Exception):
    """
    Exception used to toast a message from backend on UI while command succeed.
    Message will be toasted on ui
    """
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message
    def __str__(self):
        return u'%s' % self.message

class NoResponse(Exception):
    """
    Exception raised when no response is received while it does.
    Typically when a command takes too long to be processed and timeout is reached.
    """
    def __init__(self, to, timeout, value):
        Exception.__init__(self)
        self.value = value
        self.timeout = timeout
        self.to = to
        self.message = 'No response from %s (%.1f seconds) for request: %s' % (self.to, self.timeout, self.value)
    def __str__(self):
        return self.message

class NoMessageAvailable(Exception):
    """
    Exception raised when no message is available.
    Typically when bus pull process reaches end of timeout and no message was received, it will raise this exception.
    """
    def __init__(self):
        Exception.__init__(self)
        self.message = u'No message available'
    def __str__(self):
        return self.message

class ResourceNotAvailable(Exception):
    """
    Exception raised when no requested Cleep resource is not available.
    See RaspIotResource for more information.
    """
    def __init__(self, resource):
        Exception.__init__(self)
        self.resource = resource
    def __str__(self):
        return u'Resource %s not available' % self.resource

class InvalidParameter(Exception):
    """
    InvalidParameter is raised when invalid command parameter is detected
    """
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message
    def __str__(self):
        return u'%s' % self.message

class MissingParameter(Exception):
    """
    MissingParameter is raised when missing command parameter is detected
    """
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message
    def __str__(self):
        return u'%s' % self.message

class InvalidMessage(Exception):
    """
    InvalidMessage is raised when an invalid message is sent to bus.
    """
    def __init__(self):
        Exception.__init__(self)
        self.message = u'Invalid message'
    def __str__(self):
        return self.message

class InvalidModule(Exception):
    """
    InvalidModule is raised when an unknown module is requested
    """
    def __init__(self, module):
        Exception.__init__(self)
        self.module = module
        self.message = u'Invalid module "%s" (not loaded or unknown)' % self.module
    def __str__(self):
        return self.message

class Unauthorized(Exception):
    """
    Generic Unauthorized exception is raised when there is a problem with credentials.
    """
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message
    def __str__(self):
        return u'%s' % self.message

class BusError(Exception):
    """
    Generic bus error exception
    """
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message
    def __str__(self):
        return u'%s' % self.message

class ForcedException(Exception):
    """
    Specific exception used internally to volontary stop current process.
    """
    def __init__(self, code=-1):
        Exception.__init__(self)
        self.code = code
        self.message = u'ForcedException(%s)' % self.code
    def __str__(self):
        return self.message

