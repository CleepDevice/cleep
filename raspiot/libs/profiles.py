#!/usr/bin/env python
# -*- coding: utf-8 -*-

class RendererProfile():
    """ 
    Base renderer profile class
    It implements to_dict and __str__ functions
    """
    def __init__(self):
        pass

    def __str__(self):
        """ 
        Returns printable profile string
        """
        #exclude private members
        members = [item for item in self.__dict__.keys() if not item.startswith(u'_')]
        return u'%s: %s' % (self.__class__.__name__, members)

    def to_dict(self):
        """ 
        Returns profile as dictionary (with member values and without private members)

        Returns:
            dict: profile
        """
        return {k:v for k,v in self.__dict__.iteritems() if not k.startswith(u'_')}


class SmsProfile(RendererProfile):
    """
    Default sms profile
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.message = None

class EmailProfile(RendererProfile):
    """
    Default email profile
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.subject = None
        self.message = None
        self.recipients = []
        self.attachment = None

class PushProfile(RendererProfile):
    """
    Default email profile
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.title = None
        self.priority = None
        self.message = None
        self.devices = []
        self.attachment = None
        self.timestamp = None

class DisplayMessageProfile(RendererProfile):
    """
    Display profile.
    Handles single message
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.message = None

class DisplayLimitedTimeMessageProfile(RendererProfile):
    """
    Display profile.
    Handles single message with start and end range datetime
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.message = None
        self.start = 0
        self.end = 0

class DisplayAddOrReplaceMessageProfile(RendererProfile):
    """
    Display profile.
    Handles single message with message id to replace
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.message = None
        self.uuid = None

class TextToSpeechProfile(RendererProfile):
    """
    Sound profile
    TextToSpeech message
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.text = None

