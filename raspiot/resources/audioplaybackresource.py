#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.cleepresource import CleepResource

class AudioPlaybackResource(CleepResource):
    """
    Audio playback resource definition
    """
    RESOURCE_NAME = u'audio.playback'

