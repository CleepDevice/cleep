#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.formatters.formatter import Formatter
from raspiot.rendering.profiles import *
import time

__all__ = [u'OwmDisplayAddOrReplaceMessageFormatter']

class OwmDisplayAddOrReplaceMessageFormatter(Formatter):
    """
    Openweathermap data to DisplayAddOrReplaceProfile
    """
    def __init__(self):
        Formatter.__init__(self, u'openweathermap.weather.update', DisplayAddOrReplaceMessageProfile())

    def format(self, event_values):
        """
        Format event to profile
        """
        profile = DisplayAddOrReplaceMessageProfile()
        profile.uuid = u'openweathermap'

        #append current weather conditions
        if event_values.has_key(u'condition'):
            profile.message = event_values[u'condition']

        #append current temperature
        if event_values.has_key(u'celsius'):
            profile.message += u' %s%sC' % (event_values['celsius'], u'\N{DEGREE SIGN}')

        return profile


