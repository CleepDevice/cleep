#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.events.rendererProfile import RendererProfile

class SoundTextToSpeechProfile(RendererProfile):
    """
    Sound profile
    TextToSpeech message
    """
    def __init__(self):
        RendererProfile.__init__(self)
        self.text = None

