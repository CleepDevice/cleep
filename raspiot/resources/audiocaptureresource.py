#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.cleepresource import CleepResource

class AudioCaptureResource(CleepResource):
    """
    Audio capture resource definition
    """
    RESOURCE_NAME = u'audio.capture'

