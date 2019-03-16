#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.events.rendererProfile import RendererProfile

class DisplayAddOrReplaceMessageProfile(RendererProfile):
    """
    Display profile.
    Handles single message with message id to replace
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.message = None
        self.uuid = None

