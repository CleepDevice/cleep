#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.formatters.formatter import Formatter
from raspiot.libs.profiles import *
import time

__all__ = ['TimeDisplayAddOrReplaceMessageFormatter', 'TimeSoundTextFormatter', 'SunsetSoundTextFormatter', 'SunriseSoundTextFormatter']


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
        Formatter.__init__(self, 'system.time.now', TextToSpeechProfile())

    def format(self, event_values):
        """
        Format event to profile

        Note:
            http://www.anglaisfacile.com/exercices/exercice-anglais-2/exercice-anglais-3196.php
        """
        profile = TextToSpeechProfile()

        if event_values['hour']==0 and event_values['minute']==0:
            profile.text = 'It\'s midnight'
        if event_values['hour']==12 and event_values['minute']==0:
            profile.text = 'It\'s noon'
        elif event_values['minute']==0:
            profile.text = 'It\'s %d o\'clock' % event_values['hour']
        elif event_values['minute']==15:
            profile.text = 'It\'s quarter past %d' % event_values['hour']
        elif event_values['minute']==45:
            profile.text = 'It\'s quarter to %d' % (event_values['hour']+1)
        elif event_values['minute']==30:
            profile.text = 'It\'s half past %d' % event_values['hour']
        elif event_values['minute']<30:
            profile.text = 'It\'s %d past %d' % (event_values['minute'], event_values['hour'])
        elif event_values['minute']>30:
            profile.text = 'It\'s %d to %d' % (60-event_values['minute'], event_values['hour']+1)

        return profile


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

