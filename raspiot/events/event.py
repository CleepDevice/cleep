#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import MessageRequest

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
        if not hasattr(self, u'EVENT_NAME'):
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

    #def send(self, params=None, device_id=None, to=None):
    #    """
    #    Send event#
    #    Args:
    #        params (dict): event parameters
    #        device_id (string): device id that send event. If not specified event cannot be monitored
    #        to (string): event recipient. If not specified, event will be broadcasted

    #    Return:
    #        bool: True if event send, False if params are invalid
    #    """
    #    if self._check_params(params):
    #        self.bus.send_event(self.EVENT_NAME, params=params, device_id=device_id, to=to)
    #        return True

    #    else:
    #        self.logger.error('Invalid event parameters specified: %s' % params)
    #        return False

    def send(self, params=None, device_id=None, to=None):
        """ 
        Push event message on bus.

        Args:
            params (dict): event parameters.
            device_id (string): device id that send event. If not specified event cannot be monitored.
            to (string): event recipient. If not specified, event will be broadcasted.

        Returns:
            None: event always returns None.
        """
        if self._check_params(params):
            request = MessageRequest()
            request.to = to
            request.event = self.EVENT_NAME
            request.device_id = device_id
            request.params = params

            return self.bus.push(request, None)

        else:
            raise Exception(u'Invalid event parameters specified: %s' % (params.keys()))


