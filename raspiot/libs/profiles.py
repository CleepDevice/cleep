#!/usr/bin/env python
# -*- coding: utf-8 -*-

class ProviderProfile():
    """ 
    Base provider profile class
    It implements to_dict and __str__ functions
    """
    def __init__(self):
        pass

    def __str__(self):
        """ 
        Returns printable profile string
        """
        #exclude private members
        members = [item for item in self.__dict__.keys() if not item.startswith('_')]
        return '%s: %s' % (self.__class__.__name__, members)

    def to_dict(self):
        """ 
        Returns profile as dictionary (with member values and without private members)

        Returns:
            dict: profile
        """
        return {k:v for k,v in self.__dict__.iteritems() if not k.startswith('_')}


class SmsProfile(ProviderProfile):
    """
    Default sms profile
    """
    def __init__(self):
        ProviderProfile.__init__(self)
        self.message = None

class EmailProfile(ProviderProfile):
    """
    Default email profile
    """
    def __init__(self):
        ProviderProfile.__init__(self)
        self.subject = None
        self.message = None
        self.recipients = []
        self.attachment = None

class PushProfile(ProviderProfile):
    """
    Default email profile
    """
    def __init__(self):
        ProviderProfile.__init__(self)
        self.title = None
        self.priority = None
        self.message = None
        self.devices = []
        self.attachment = None
        self.timestamp = None

class DisplayMessageProfile(ProviderProfile):
    """
    Display profile.
    Handles single message
    """
    def __init__(self):
        ProviderProfile.__init__(self)
        self.message = None

class DisplayLimitedTimeMessageProfile(ProviderProfile):
    """
    Display profile.
    Handles single message with start and end range datetime
    """
    def __init__(self):
        ProviderProfile.__init__(self)
        self.message = None
        self.start = 0
        self.end = 0

class DisplayAddOrReplaceMessageProfile(ProviderProfile):
    """
    Display profile.
    Handles single message with message id to replace
    """
    def __init__(self):
        ProviderProfile.__init__(self)
        self.message = None
        self.uuid = None


