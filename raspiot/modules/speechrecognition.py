#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import os
from raspiot.raspiot import RaspIotModule
from raspiot.libs.alsa import Alsa

__all__ = ['Speechrecognition']


class Speechrecognition(RaspIotModule):
    """
    Speechrecognition module implements SpeechToText feature using snowboy for local hotword detection
    and online services to translate user speech to text
    """

    MODULE_CONFIG_FILE = u'speechrecognition.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Control your device using voice'
    MODULE_LOCKED = False
    MODULE_TAGS = [u'audio', u'speech', u'stt', 'speechtotext']
    MODULE_COUNTRY = None
    MODULE_LINK = None

    DEFAULT_CONFIG = {
        u'hotwordtoken': None,
        u'hotwordfiles': [None, None, None],
        u'hotwordmodel': None,
        u'provider': None,
        u'apikeys': {}
    }

    PROVIDERS = [
        u'Microsoft Bing Speech',
        u'Google Cloud Speech'
    ]

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

    def _configure(self):
        """
        Configure module
        """
        pass

    def get_module_config(self):
        """
        Return module configuration
        """
        #apikeys dict to list
        apikeys = []
        for provider in self._config[u'apikeys']:
            apikeys.append({
                u'provider': provider,
                u'apikey': self._config[u'apikeys'][provider]
            })

        return {
            u'provider': self._config[u'provider'],
            u'apikeys': self._config[u'apikeys'],
            u'providers': self.PROVIDERS,
            u'hotwordtoken': self._config[u'hotwordtoken'],
            u'hotwordrecordings': self.__get_hotword_recording_status(),
            u'hotwordmodel': self._config[u'hotwordmodel'] is not None
        }

    def __get_hotword_recording_status(self):
        """
        Return hotword recording status

        Return:
            tuple: tuple of 3 values representing current hotword recording status::
                (True, False, False)
        """
        config = self._get_config()
        record1 = config[u'hotwordfiles'][0] is not None and os.path.exists(config[u'hotwordfiles'][0])
        record2 = False
        record3 = False
        if record1:
            record2 = config[u'hotwordfiles'][1] is not None and os.path.exists(config[u'hotwordfiles'][1])
            if record2:
                record3 = config[u'hotwordfiles'][2] is not None and os.path.exists(config[u'hotwordfiles'][2])

        return (record1, record2, record3)

    def set_provider(self, provider, apikey):
        """
        Set speechtotext provider

        Args:
            provider (string): provider name
            apikey (string): provider apikey
        """
        if provider is None or len(provider.strip())==0:
            raise MissingParameter(u'Parameter provider is missing')
        if provider not in self.PROVIDERS:
            raise InvalidParameter(u'Specified provider is not allowed. Please check list of supported provider.')
        if apikey is None or len(apikey.strip())==0:
            raise MissingParameter(u'Parameter apikey is missing')

        config = self._get_config()
        config[u'provider'] = provider
        config[u'apikeys'][provider] = apikey

        if not self._save_config(config):
            return False

        return True

    def set_hotword_token(self, token):
        """
        Set hot-word api token

        Args:
            token (string): snowboy api token

        Return:
            bool: True if token saved successfully
        """
        config = self._get_config()
        config[u'hotwordtoken'] = token
        if not self._save_config(config):
            return False

        return True

    def record_hotword(self):
        """
        Record hot-word and when all recordings are done, train personal model

        Return:
            tuple: status of hotword recordings::
                (True, False, False)
        """
        #record sound
        record = self.alsa.record_sound(timeout=5.0)

        #save recording
        record1, record2, record3 = self.__get_hotword_recording_status()
        train = False
        config = self._get_config()
        if not record1:
            config[u'hotwordfiles'][0] = record
        elif not record2:
            config[u'hotwordfiles'][1] = record
        elif not record3:
            config[u'hotwordfiles'][2] = record
            train = True
        self._save_config(config)

        #train if all recordings ready
        if train:
            #TODO
            pass

        return self.__get_hotword_recording_status()

    def reset_hotword(self):
        """
        Clear all recorded file and personnal model
        """
        config = self._get_config()
        if config[u'hotwordfiles'][0] and os.path.exists(config[u'hotwordfiles'][0]):
            os.remove(config[u'hotwordfiles'][0])
        if config[u'hotwordfiles'][1] and os.path.exists(config[u'hotwordfiles'][1]):
            os.remove(config[u'hotwordfiles'][1])
        if config[u'hotwordfiles'][2] and os.path.exists(config[u'hotwordfiles'][2]):
            os.remove(config[u'hotwordfiles'][2])
        if config[u'hotwordmodel'] and os.path.exists(config[u'hotwordmodel']):
            os.remove(config[u'hotwordmodel'])

        return True

