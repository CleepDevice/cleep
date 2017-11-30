#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.events.event import Event

class Systemalertmemory(Event):
    """
    System.alert.memory event
    """

    EVENT_NAME = u'system.alert.memory'
    EVENT_SYSTEM = True

    def __init__(self):
        """
        Constructor
        """
        Event.__init__(self)

    def _check_params(self, params):
        """
        Check event parameters

        Args:
            params (dict): event parameters

        Return:
            bool: True if params are valid, False otherwise
        """
        return all(key in [u'percent', u'threshold'] for key in params.keys())

