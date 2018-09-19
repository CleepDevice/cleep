#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rendererprofile import RendererProfile

class SpeechRecognitionHotwordProfile(RendererProfile):
    """
    Speechrecognition hotword profile
    Handles hotword detected and released
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.detected = True

