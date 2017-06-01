#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.formatters.formatter import Formatter
from raspiot.libs.profiles import *
import time

__all__ = ['TimeDisplayAddOrReplaceMessageFormatter', '']


class TimeDisplayAddOrReplaceMessageFormatter(Formatter):
    """
    Time data to DisplayAddOrReplaceProfile
    """
    def __init__(self):
        Formatter.__init__(self, 'system.time.now', DisplayAddOrReplaceMessageProfile())

    def format(self, event_values):
        """
        Format event to profile
        """
        profile = DisplayAddOrReplaceMessageProfile()
        profile.uuid = 'currenttime'

        #append current time
        profile.message = '%02d:%02d - %02d/%02d/%d' % (event_values['hour'], event_values['minute'], event_values['day'], event_values['month'], event_values['year'])

        return profile

class TimeSoundTextFormatter(Formatter):
    """
    Current time data to TextToSpeechProfile
    """
    def __init__(self):
        Formatter(.__init__(self, 'system.time.now', TextToSpeechProfile())

    def format(self, event_values):
        """
        Format event to profile
        """
        profile = TextToSpeechProfile()

        if event_values['minute']==0:
            profile.text = 'It\'s %d o\'clock' % event_values['hour']
        #http://www.anglaisfacile.com/exercices/exercice-anglais-2/exercice-anglais-3196.php


class SunsetSoundTextFormatter(Formatter):
    """
    Sunset data to TextToSpeechProfile
    """
    def __init__(self):
        Formatter.__init__(self, 'system.time.sunset', TextToSpeechProfile())

    def format(self, event_values):
        """
        Format event to profile
        """
        profile = TextToSpeechProfile()
        profile.text = 'It\'s sunset!'

        return profile

class SunriseSoundTextFormatter(Formatter):
    """
    Sunrise data to TextToSpeechProfile
    """
    def __init__(self):
        Formatter.__init__(self, 'system.time.sunrise', TextToSpeechProfile())

    def format(self, event_values):
        """
        Format event to profile
        """
        profile = TextToSpeechProfile()
        profile.text = 'It\'s sunrise!'

        return profile

