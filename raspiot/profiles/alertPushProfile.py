#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.rendererprofile import RendererProfile

class AlertPushProfile(RendererProfile):
    """
    Default email profile
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.title = None
        self.priority = None
        self.message = None
        self.devices = []
        self.attachment = None
        self.timestamp = None

