#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.rendererprofile import RendererProfile

class DisplayRangeMessageProfile(RendererProfile):
    """
    Display profile.

    Handles message with start and end range
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.message = None
        self.start = 0
        self.end = 0

