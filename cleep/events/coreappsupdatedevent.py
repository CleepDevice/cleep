#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class CoreAppsUpdatedEvent(Event):
    """
    Core.apps.updated event
    """

    EVENT_NAME = 'core.apps.updated'
    EVENT_PROPAGATE = False
    EVENT_PARAMS = []

    def __init__(self, params):
        """
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)

