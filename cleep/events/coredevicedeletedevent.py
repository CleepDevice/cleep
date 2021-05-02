#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class CoreDeviceDeletedEvent(Event):
    """
    Core.device.deleted event
    """

    EVENT_NAME = 'core.device.deleted'
    EVENT_PROPAGATE = False
    EVENT_PARAMS = []

    def __init__(self, params):
        """
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)

