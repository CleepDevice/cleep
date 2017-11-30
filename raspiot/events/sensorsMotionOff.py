#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.events.event import Event

class Sensorsmotionoff(Event):
    """
    Sensors.motion.off event
    """

    EVENT_NAME = u'sensors.motion.off'
    EVENT_SYSTEM = False

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
        return all(key in [u'sensor', u'lastupdate', u'duration'] for key in params.keys())

