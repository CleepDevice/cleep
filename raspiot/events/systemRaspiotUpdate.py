#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.events.event import Event
import logging

class Systemraspiotupdate(Event):
    """
    System.raspiot.update event
    """

    EVENT_NAME = u'system.raspiot.update'
    EVENT_SYSTEM = True

    def __init__(self, bus, formatters_factory, events_factory):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_factory (FormattersFactory): formatters factory instance
            events_factory (EventsFactory): events factory instance
        """
        Event.__init__(self, bus, formatters_factory, events_factory)

        #logger
        self.logger = logging.getLogger(self.__class__.__name__)

    def _check_params(self, params):
        """
        Check event parameters

        Args:
            params (dict): event parameters

        Return:
            bool: True if params are valid, False otherwise
        """
        #check params
        if not isinstance(params, dict):
            self.logger.error(u'Parameter "params" is not a dict for event "%s"' % self.EVENT_NAME)

        keys = [
            u'status'
        ]
        return all(key in keys for key in params.keys())

