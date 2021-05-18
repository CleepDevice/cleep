#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.rendererprofile import RendererProfile

class NamedMessageProfile(RendererProfile):
    """
    Named message profile

    This message has an unique name that allows renderers to update the previous message
    """
    def __init__(self):
        RendererProfile.__init__(self)
        # message to display
        self.message = None
        # unique message id to allow message identification
        self.name = None

