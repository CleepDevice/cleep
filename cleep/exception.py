#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cleep exceptions
"""

__all__ = ['CommandError', 'CommandInfo', 'NoResponse', 'NoMessageAvailable', 'ResourceNotAvailable',
           'InvalidParameter', 'MissingParameter', 'InvalidMessage', 'InvalidModule', 'Unauthorized',
           'BusError']

class CommandError(Exception):
    """
    Exception used when module command failed.
    Message will be toasted on UI.
    """
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message
    def __str__(self):
        return '%s' % self.message

class CommandInfo(Exception):
    """
    Exception used to toast a message from backend on UI while command succeed.
    Message will be toasted on ui
    """
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message
    def __str__(self):
        return '%s' % self.message

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
        self.message = 'No response from %s (%.1f seconds) for request: %s' % (self.to, self.timeout or 0.0, self.value)
    def __str__(self):
        return self.message

class NoMessageAvailable(Exception):
    """
    Exception raised when no message is available.
    Typically when bus pull process reaches end of timeout and no message was received, it will raise this exception.
    """
    def __init__(self):
        Exception.__init__(self)
        self.message = 'No message available'
    def __str__(self):
        return self.message

class ResourceNotAvailable(Exception):
    """
    Exception raised when no requested Cleep resource is not available.
    See CleepResource for more information.
    """
    def __init__(self, resource):
        Exception.__init__(self)
        self.resource = resource
        self.message = 'Resource %s not available' % self.resource
    def __str__(self):
        return self.message

class InvalidParameter(Exception):
    """
    InvalidParameter is raised when invalid command parameter is detected
    """
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message
    def __str__(self):
        return '%s' % self.message

class MissingParameter(Exception):
    """
    MissingParameter is raised when missing command parameter is detected
    """
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message
    def __str__(self):
        return '%s' % self.message

class InvalidMessage(Exception):
    """
    InvalidMessage is raised when an invalid message is sent to bus.
    """
    def __init__(self):
        Exception.__init__(self)
        self.message = 'Invalid message'
    def __str__(self):
        return self.message

class InvalidModule(Exception):
    """
    InvalidModule is raised when an unknown application is requested
    """
    def __init__(self, module):
        Exception.__init__(self)
        self.module = module
        self.message = 'Invalid application "%s" (not loaded or unknown)' % self.module
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
        return '%s' % self.message

class BusError(Exception):
    """
    Generic bus error exception
    """
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message
    def __str__(self):
        return '%s' % self.message

class NotReady(Exception):
    """
    NotReady is raised when the application is not ready
    """
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message
    def __str__(self):
        return self.message

