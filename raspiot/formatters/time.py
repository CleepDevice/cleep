#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.formatters.formatter import Formatter
from raspiot.profiles import *
import time

__all__ = [u'TimeDisplayAddOrReplaceMessageFormatter', u'TimeSoundTextFormatter', u'SunsetSoundTextFormatter', u'SunriseSoundTextFormatter']


class TimeDisplayAddOrReplaceMessageFormatter(Formatter):
    """
    Time data to DisplayAddOrReplaceProfile
    """
    def __init__(self, events_factory):
        """
        Constuctor

        Args:
            events_factory (EventsFactory): events factory instance
        """
        Formatter.__init__(self, events_factory, u'system.time.now', DisplayAddOrReplaceMessageProfile())

    def _fill_profile(self, event_values, profile):
        """
        Fill profile with event data
        """
        profile.uuid = u'currenttime'

        #append current time
        profile.message = u':clock: %02d:%02d %02d/%02d/%d' % (event_values[u'hour'], event_values[u'minute'], event_values[u'day'], event_values[u'month'], event_values[u'year'])

        return profile


class TimeSoundTextFormatter(Formatter):
    """
    Current time data to TextToSpeechProfile
    """
    def __init__(self, events_factory):
        """
        Constructor

        Args:
            events_factory (EventsFactory): events factory instance
        """
        Formatter.__init__(self, events_factory, u'system.time.now', TextToSpeechProfile())

    def _fill_profile(self, event_values, profile):
        """
        Fill profile with event data

        Args:
            event_values (dict): event values
            profile (Profile): profile instance

        Note:
            http://www.anglaisfacile.com/exercices/exercice-anglais-2/exercice-anglais-3196.php
        """
        if event_values[u'hour']==0 and event_values[u'minute']==0:
            profile.text = u'It\'s midnight'
        if event_values[u'hour']==12 and event_values[u'minute']==0:
            profile.text = u'It\'s noon'
        elif event_values[u'minute']==0:
            profile.text = u'It\'s %d o\'clock' % event_values[u'hour']
        elif event_values['minute']==15:
            profile.text = u'It\'s quarter past %d' % event_values[u'hour']
        elif event_values[u'minute']==45:
            profile.text = u'It\'s quarter to %d' % (event_values[u'hour']+1)
        elif event_values[u'minute']==30:
            profile.text = u'It\'s half past %d' % event_values[u'hour']
        elif event_values[u'minute']<30:
            profile.text = u'It\'s %d past %d' % (event_values[u'minute'], event_values[u'hour'])
        elif event_values[u'minute']>30:
            profile.text = u'It\'s %d to %d' % (60-event_values[u'minute'], event_values[u'hour']+1)

        return profile


class SunsetSoundTextFormatter(Formatter):
    """
    Sunset data to TextToSpeechProfile
    """
    def __init__(self, events_factory):
        """
        Constructor

        Args:
            events_factory (EventsFactory): events factory instance
        """
        Formatter.__init__(self, events_factory, u'system.time.sunset', TextToSpeechProfile())

    def _fill_profile(self, event_values, profile):
        """
        Fill profile with event data

        Args:
            event_values (dict): event values
            profile (Profile): profile instance
        """
        profile.text = u'It\'s sunset!'

        return profile


class SunriseSoundTextFormatter(Formatter):
    """
    Sunrise data to TextToSpeechProfile
    """
    def __init__(self, events_factory):
        """
        Contructor

        Args:
            events_factory (EventsFactory): events factory instance
        """
        Formatter.__init__(self, events_factory, u'system.time.sunrise', TextToSpeechProfile())

    def _fill_profile(self, event_values, profile):
        """
        Fill profile with event data

        Args:
            event_values (dict): event values
            profile (Profile): profile instance
        """
        profile.text = u'It\'s sunrise!'

        return profile

