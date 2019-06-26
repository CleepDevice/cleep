#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rendererProfile import RendererProfile

class SpeechRecognitionCommandProfile(RendererProfile):
    """
    Speechrecognition command profile
    Handles speechrecognition detected and error command
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.error = False


