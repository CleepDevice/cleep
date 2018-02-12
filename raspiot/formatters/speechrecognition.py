#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.formatters.formatter import Formatter
from raspiot.profiles import *
import time

__all__ = [u'SpeechRecognitionHotwordDetectedFormatter', u'SpeechRecognitionHotwordReleasedFormatter', u'SpeechRecognitionCommandDetectedFormatter', u'SpeechRecognitionCommandErrorFormatter']

class SpeechRecognitionHotwordDetectedFormatter(Formatter):
    """
    SpeechRecognition hotword detected to SpeechRecognitionHotwordProfile
    """
    def __init__(self, events_factory):
        """
        Constuctor

        Args:
            events_factory (EventsFactory): events factory instance
        """
        Formatter.__init__(self, events_factory, u'speechrecognition.hotword.detected', SpeechRecognitionHotwordProfile())

    def _fill_profile(self, event_values, profile):
        """
        Fill profile with event data
        """
        profile.detected = True

        return profile

class SpeechRecognitionHotwordReleasedFormatter(Formatter):
    """
    SpeechRecognition hotword released to SpeechRecognitionHotwordProfile
    """
    def __init__(self, events_factory):
        """
        Constuctor

        Args:
            events_factory (EventsFactory): events factory instance
        """
        Formatter.__init__(self, events_factory, u'speechrecognition.hotword.released', SpeechRecognitionHotwordProfile())

    def _fill_profile(self, event_values, profile):
        """
        Fill profile with event data
        """
        profile.detected = False

        return profile

class SpeechRecognitionCommandDetectedFormatter(Formatter):
    """
    SpeechRecognition command detected to SpeechRecognitionCommandProfile
    """
    def __init__(self, events_factory):
        """
        Constuctor

        Args:
            events_factory (EventsFactory): events factory instance
        """
        Formatter.__init__(self, events_factory, u'speechrecognition.command.detected', SpeechRecognitionCommandProfile())

    def _fill_profile(self, event_values, profile):
        """
        Fill profile with event data
        """
        profile.error = False

        return profile

class SpeechRecognitionCommandErrorFormatter(Formatter):
    """
    SpeechRecognition command error to SpeechRecognitionCommandProfile
    """
    def __init__(self, events_factory):
        """
        Constuctor

        Args:
            events_factory (EventsFactory): events factory instance
        """
        Formatter.__init__(self, events_factory, u'speechrecognition.command.error', SpeechRecognitionCommandProfile())

    def _fill_profile(self, event_values, profile):
        """
        Fill profile with event data
        """
        profile.error = True

        return profile
