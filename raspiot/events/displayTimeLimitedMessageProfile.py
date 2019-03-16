#!/usr/bin/env python
# -*- coding: utf-8 -*-

class DisplayTimeLimitedMessageProfile(RendererProfile):
    """
    Display profile.
    Handles single message with start and end range datetime
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.message = None
        self.start = 0
        self.end = 0

