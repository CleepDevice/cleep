#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rendererprofile import RendererProfile

class AlertEmailProfile(RendererProfile):
    """
    Default email profile
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.subject = None
        self.message = None
        self.recipients = []
        self.attachment = None

