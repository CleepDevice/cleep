#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cleep exceptions
"""

__all__ = [u'CommandError', u'CommandInfo', u'NoResponse', u'NoMessageAvailable', u'InvalidParameter', u'ResourceNotAvailable'
           u'NoCityFound', u'InvalidParameter', u'MissingParameter', u'InvalidMessage', u'InvalidModule', u'Unauthorized', u'BusError',
           u'ForcedException']

class CommandError(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return u'%s' % self.message

class CommandInfo(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return u'%s' % self.message

class NoResponse(Exception):
    def __init__(self, to, timeout, value):
        self.value = value
        self.timeout = timeout
        self.to = to
        self.message = 'No response from %s (%.1f seconds) for request: %s' % (self.to, self.timeout, self.value)
    def __str__(self):
        return self.message

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
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return u'%s' % self.message

class MissingParameter(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return u'%s' % self.message

class InvalidMessage(Exception):
    def __init__(self):
        self.message = u'Invalid message'
    def __str__(self):
        return self.message

class InvalidModule(Exception):
    def __init__(self, module):
        self.module = module
        self.message = u'Invalid module "%s" (not loaded or unknown)' % self.module
    def __str__(self):
        return self.message

class Unauthorized(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return u'%s' % self.message

class BusError(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return u'%s' % self.message

class ForcedException(Exception):
    def __init__(self, code=-1):
        self.code = code
        self.message = u'ForcedException(%s)' % self.code
    def __str__(self):
        return self.message

