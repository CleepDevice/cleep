#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
from .driver import Driver

class AudioDriver(Driver):
    """
    Audio driver base class
    """

    OUTPUT_TYPE_UNKNOWN = 0
    OUTPUT_TYPE_JACK = 1 
    OUTPUT_TYPE_HDMI = 2 
    OUTPUT_TYPE_HAT = 3 #HAT soundcard like hifiberry or respaker
    OUTPUT_TYPE_EXT = 4 #external audio device like USB soundcard

    def __init__(self, driver_name, config):
        """
        Constructor

        Args:
            driver_name (string): driver name
            config (dict): driver configuration::

                {
                    output_type (int): output type (see OUTPUT_TYPE_XXX values)
                    playback_volume (string): alsa control name for the playback volume
                    playback_volume_data (tuple): (key, pattern) to get playback volume value
                    capture_volume (string): alsa control name for the capture volume
                    capture_volume_data (tuple): (key, pattern) to get capture volume value
                }

        """
        Driver.__init__(self, Driver.DRIVER_AUDIO, driver_name, config)

    def _check_configuration(self, config):
        """
        Check driver configuration
        """
        if u'output_type' not in config:
            raise Exception(u'Field "output_type" is missing in audio driver configuration')
        if u'playback_volume' not in config:
            raise Exception(u'Field "playback_volume" is missing in audio driver configuration')
        if u'playback_volume_data' not in config:
            raise Exception(u'Field "playback_volume_data" is missing in audio driver configuration')
        if u'capture_volume' not in config:
            raise Exception(u'Field "capture_volume" is missing in audio driver configuration')
        if u'capture_volume_data' not in config:
            raise Exception(u'Field "capture_volume_data" is missing in audio driver configuration')

