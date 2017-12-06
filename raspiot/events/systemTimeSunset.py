#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.events.event import Event

class Systemtimesunset(Event):
    """
    System.time.sunset event
    """

    EVENT_NAME = u'system.time.sunset'
    EVENT_SYSTEM = False

    def __init__(self, bus, events_factory):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            events_factory (EventsFactory): events factory instance
        """
        Event.__init__(self, bus, events_factory)

    def _check_params(self, params):
        """
        Check event parameters

        Args:
            params (dict): event parameters

        Return:
            bool: True if params are valid, False otherwise
        """
        return True
