#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rendererProfile import RendererProfile

class AlertSmsProfile(RendererProfile):
    """
    Default sms profile
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.message = None

