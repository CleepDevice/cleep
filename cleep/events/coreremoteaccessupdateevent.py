#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event


class CoreRemoteAccessUpdateEvent(Event):
    """
    Fired when the set of public remote-access URLs changes on this device.

    Propagated on the external bus so already-connected peers (e.g. cleep-desktop)
    can update without waiting for a new ZRE HELLO.
    """

    EVENT_NAME = "core.remoteaccess.update"
    EVENT_PROPAGATE = True
    EVENT_PARAMS = ["urls"]

    def __init__(self, params):
        """
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)
