#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.formatters.formatter import Formatter
from raspiot.libs.profiles import *
import time

__all__ = ['DisplayAddOrReplaceMessageFormatter']

"""
class DisplayLimitedDateFormatter(Formatter):
    Openweathermap data to DisplayLimitedTimeMessageProfile
    def __init__(self):
        Formatter.__init__(self, 'openweathermap.weather.update', DisplayLimitedTimeMessageProfile())

    def format(self, event_values):
        Format event to profile
        profile = DisplayLimitedTimeMessageProfile()

        #append current weather conditions
        if event_values.has_key('condition'):
            profile.message = event_values['condition']

        #append current temperature
        if event_values.has_key('celsius'):
            profile.message += ' %s' % int(round(event_values['celsius']))

        #start and end datetime
        profile.start = int(time.time())
        profile.end = profile.start + 1800 #same time than in openweathermap module

        return profile
"""

class OwmDisplayAddOrReplaceMessageFormatter(Formatter):
    """
    Openweathermap data to DisplayAddOrReplaceProfile
    """
    def __init__(self):
        Formatter.__init__(self, 'openweathermap.weather.update', DisplayAddOrReplaceMessageProfile())

    def format(self, event_values):
        """
        Format event to profile
        """
        profile = DisplayAddOrReplaceMessageProfile()
        profile.uuid = 'openweathermap'

        #append current weather conditions
        if event_values.has_key('condition'):
            profile.message = event_values['condition']

        #append current temperature
        if event_values.has_key('celsius'):
            profile.message += ' %sC' % event_values['celsius']

        return profile


