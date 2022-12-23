#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.rendererprofile import RendererProfile

class AlarmProfile(RendererProfile):
    """
    Alarm profile.

    Used to trigger an alert for renderer that support it
    """

    STATUS_UNKNOWN = 'unknown'
    STATUS_SCHEDULED = 'scheduled'
    STATUS_UNSCHEDULED = 'unscheduled'
    STATUS_TRIGGERED = 'triggered'
    STATUS_STOPPED = 'stopped'
    STATUS_SNOOZED = 'snoozed'

    def __init__(self):
        RendererProfile.__init__(self)
        self.hour = None
        self.minute = None
        self.timeout = None
        self.volume = None
        self.count = None # scheduled alarm count
        self.status = self.STATUS_UNKNOWN
        self.repeat = False
        self.shuffle = False

