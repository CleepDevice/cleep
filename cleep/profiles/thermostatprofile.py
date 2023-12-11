#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.rendererprofile import RendererProfile

class ThermostatProfile(RendererProfile):
    """
    Thermostat profile
    """

    MODE_STOP = 'stop'
    MODE_COMFORT1 = 'comfort1'
    MODE_COMFORT2 = 'comfort2'
    MODE_COMFORT3 = 'comfort3'
    MODE_ECO = 'eco'
    MODE_ANTIFROST = 'antifrost'

    def __init__(self):
        RendererProfile.__init__(self)
        self.device_uuid = None
        self.mode = None

