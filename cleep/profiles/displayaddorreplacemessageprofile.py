#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.rendererprofile import RendererProfile

class DisplayAddOrReplaceMessageProfile(RendererProfile):
    """
    Display profile.

    Handles single message with message id to replace.
    """
    def __init__(self):
        RendererProfile.__init__(self)
        #message to display
        self.message = None
        #message unique id to allow message replacement
        self.uuid = None

