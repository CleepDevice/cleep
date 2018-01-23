#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import os
from raspiot.raspiot import RaspIotModule
from raspiot.libs.alsa import Alsa
from raspiot.libs.asoundrc import Asoundrc

__all__ = ['Audio']


class Audio(RaspIotModule):
    """
    Audio module is in charge of configuring audio on raspberry pi
    """

    MODULE_CONFIG_FILE = None
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Configure audio on your device'
    MODULE_LOCKED = False
    MODULE_TAGS = [u'audio', u'sound']
    MODULE_COUNTRY = None
    MODULE_LINK = None

    TEST_SOUND = u'/opt/raspiot/sounds/connected.wav'

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        self.alsa = Alsa()
        self.asoundrc = Asoundrc()

    def get_module_config(self):
        """
        Return module configuration
        """
        #get all stuff
        current_config = self.asoundrc.get_configuration()
        playback_devices = self.alsa.get_playback_devices()
        capture_devices = self.alsa.get_capture_devices()
        volumes = self.alsa.get_volumes()

        #improve configuration content
        card_name = None
        if current_config is not None:
            for name in playback_devices.keys():
                if playback_devices[name][u'cardid']==current_config[u'cardid']:
                    card_name = name
                    break
        current_config[u'cardname'] = card_name

        return {
            u'config': current_config,
            u'volumes': volumes,
            u'devices': {
                u'playback': playback_devices,
                u'capture': capture_devices
            }
        }

    def set_default_device(self, card_id, device_id):
        """
        Set default audio device

        Args:
            card_id (int): card identifier
            device_id (int): device identifier

        Return:
            bool: True if device saved successfully
        """
        #check values
        playback_devices = self.alsa.get_playback_devices()
        found = False
        for device in playback_devices.keys():
            if playback_devices[device][u'cardid']==card_id and playback_devices[device][u'deviceid']==device_id:
                found = True
                break
        if not found:
            raise InvalidParameter(u'Specified device is not installed')

        #save new device
        return self.asoundrc.set_default_device(card_id, device_id)
    
    def set_volumes(self, playback, capture):
        """
        Update volume

        Args:
            playback (int): playback volume percentage
            capture (int): capture volume percentage

        Return:
            dict: current volume::
                {
                    playback (int)
                    capture (int)
                }
        """
        return self.alsa.set_volumes(playback, capture)

    def test_playing(self):
        """
        Play test sound to make sure audio card is correctly configured
        """
        if not self.alsa.play_sound(self.TEST_SOUND):
            raise CommandError(u'Unable to play test sound: internal error.')

    def test_recording(self):
        """
        Record sound during few seconds and play it
        """
        sound = self.alsa.record_sound(timeout=5.0)
        self.logger.debug(u'Recorded sound: %s' % sound)
        self.alsa.play_sound(sound)

        #purge file
        time.sleep(1.0)
        os.remove(sound)




