#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.events.event import Event

class Openweathermapweatherupdate(Event):
    """
    Openweathermap.weather.update event
    """

    EVENT_NAME = u'openweathermap.weather.update'
    EVENT_SYSTEM = False

    def __init__(self, bus):
        """
        Constructor

        Args:
            bus (MessageBus): message bus instance
        """
        Event.__init__(self, bus)

    def _check_params(self, params):
        """
        Check event parameters

        Args:
            params (dict): event parameters

        Return:
            bool: True if params are valid, False otherwise
        """
        keys = [
            u'icon',
            u'condition',
            u'code',
            u'celsius',
            u'fahrenheit',
            u'pressure',
            u'humidity',
            u'wind_speed',
            u'wind_degrees',
            u'wind_direction'
        ]
        return all(key in keys for key in params.keys())

