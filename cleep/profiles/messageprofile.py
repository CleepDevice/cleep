#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.rendererprofile import RendererProfile

class DisplayMessageProfile(RendererProfile):
    """
    Display message profile.

    Handles a message
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.message = None

