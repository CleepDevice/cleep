#!/usr/bin/env python
# -*- coding: utf-8 -*-

class DisplayMessageProfile(RendererProfile):
    """
    Display profile.
    Handles single message
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.message = None

