#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.rendererprofile import RendererProfile

class AlertProfile(RendererProfile):
    """
    Alert profile.

    Used to trigger an alert for renderer that support it
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.subject = None
        self.message = None
        self.attachment = None
        self.timestamp = None

