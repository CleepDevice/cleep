#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.events.event import Event

class Developerpyremotedevstarted(Event):
    """
    Developer.pyremotedev.started event
    """

    EVENT_NAME = u'developer.pyremotedev.started'
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
        #no params
        return True


