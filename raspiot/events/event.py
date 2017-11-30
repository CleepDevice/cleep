#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Event():
    """
    Base event class
    """

    def __init__(self, bus):
        """
        Construtor

        Args:
            bus (MessageBus): message bus instance
        """
        self.bus = bus
        if not hasattr(self, EVENT_NAME):
            raise NotImplementedError(u'EVENT_NAME class member must be declared')

    def _check_params(self, params):
        """
        Check event parameters

        Args:
            params (dict): event parameters

        Return:
            bool: True if params are valid, False otherwise
        """
        raise NotImplementedError(u'_check_params method must implemented')

    def send(self, params=None, device_id=None, to=None):
        """
        Send event

        Args:
            params (dict): event parameters
            device_id (string): device id that send event. If not specified event cannot be monitored
            to (string): event recipient. If not specified, event will be broadcasted

        Return:
            bool: True if event send, False if params are invalid
        """
        if self._check_params(params):
            self.bus.send_event(self.EVENT_NAME, params=params, device_id=device_id, to=to)
            return True

        else:
            self.logger.error('Invalid event parameters specified: %s' % params)
            return False

