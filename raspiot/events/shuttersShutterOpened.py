#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.events.event import Event

class Shuttersshutteropened(Event):
    """
    Shutters.shutter.opened event
    """

    EVENT_NAME = u'shutters.shutter.opened'
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
        return all(key in [u'shutter', u'lastupdate'] for key in params.keys())

