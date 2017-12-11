#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.events.event import Event

class Gpiosgpioon(Event):
    """
    Gpios.gpio.on event
    """

    EVENT_NAME = u'gpios.gpio.on'
    EVENT_SYSTEM = False

    def __init__(self, bus, formatters_factory, events_factory):
        """
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_factory (FormattersFactory): formatters factory instance
            events_factory (EventsFactory): events factory instance
        """
        Event.__init__(self, bus, formatters_factory, events_factory)

    def _check_params(self, params):
        """
        Check event parameters

        Args:
            params (dict): event parameters

        Return:
            bool: True if params are valid, False otherwise
        """
        return all(key in [u'gpio', u'init'] for key in params.keys())

