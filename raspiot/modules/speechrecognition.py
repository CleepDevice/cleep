#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import os
from raspiot.raspiot import RaspIotModule
from raspiot.libs.alsa import Alsa
from raspiot.libs.snowboy import Snowboy
from threading import Thread
from raspiot.utils import MissingParameter, InvalidParameter, CommandError

__all__ = ['Speechrecognition']

class BuildPersonalVoiceModelTask(Thread):
    """
    Build snowboy personal voice model can take more than 1 minute, so we must parallelize its process
    """
    def __init__(self, token, recordings, end_of_training_callback, logger):
        """
        Constructor

        Args:
            token (string): api token
            recordings (list): list of 3 recordings
            end_of_training_callback (callback): function called when training is terminated (params: error (bool), model filepath (string))
            logger (logger): logger instance
        """
        Thread.__init__(self)
        Thread.daemon = True

        #members
        self.logger = logger
        self.callback = end_of_training_callback
        self.token = token
        self.recordings = recordings

    def run(self):
        """
        Task
        """
        error = None
        voice_model = None
        snowboy = Snowboy(self.token)
        try:
            voice_model = snowboy.train(self.recordings[0], self.recordings[1], self.recordings[2])
            self.logger.debug(u'Generated voice model: %s' % voice_model)

        except:
            self.logger.exception('Error during snowboy training:')
            error = snowboy.get_last_error()

        #end of process callback
        self.callback(error, voice_model)

class SpeechRecognitionProcess(Thread):
    """
    Speech recognition process
    """
    def __init__(self, logger):
        """
        Constructor

        Args:
            logger (logger): logger instance
        """
        Thread.__init__(self)
        Thread.daemon = True

        #members
        self.logger = logger
        self.running = True

    def stop(self):
        """
        Stop recognition process
        """
        self.running = False

    def run(self):
        """
        Speechrecognition process
        """
        while self.running:
            pass
            time.sleep(1.0)

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
        u'providerid': None,
        u'providerapikeys': {},
        u'serviceenabled': True
    }

    PROVIDERS = [
        {u'id':0, u'label':u'Microsoft Bing Speech', u'enabled':True},
        {u'id':1, u'label':u'Google Cloud Speech', u'enabled':False},
    ]

    VOICE_MODEL_PATH = u'/opt/raspiot/speechrecognition'

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
        self.__training_task = None
        self.__recognition_task = None

        #events
        self.trainingOkEvent = self._get_event('speechrecognition.training.ok')
        self.trainingKoEvent = self._get_event('speechrecognition.training.ko')

    def _configure(self):
        """
        Configure module
        """
        #make sure voice model path exists
        if not os.path.exists(self.VOICE_MODEL_PATH):
            os.makedirs(self.VOICE_MODEL_PATH)

    def get_module_config(self):
        """
        Return module configuration
        """
        #build provider list (with apikey)
        providers = []
        for provider in self.PROVIDERS:
            #deep copy entry
            entry = {
                u'id': provider[u'id'],
                u'provider': provider[u'label'],
                u'enabled': provider[u'enabled'],
                u'apikey': None
            }

            #fill apikey if configured
            if str(provider[u'id']) in self._config[u'providerapikeys'].keys():
                entry[u'apikey'] = self._config[u'providerapikeys'][str(provider[u'id'])]

            #save entry
            providers.append(entry)

        return {
            u'providerid': self._config[u'providerid'],
            u'providers': providers,
            u'hotwordtoken': self._config[u'hotwordtoken'],
            u'hotwordrecordings': self.__get_hotword_recording_status(),
            u'hotwordmodel': self._config[u'hotwordmodel'] is not None,
            u'serviceenabled': self._config[u'serviceenabled'],
            u'hotwordtraining': self.__training_task is not None
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

    def __check_provider(self, provider_id):
        """
        Check if provider is valid

        Args:
            provider_id (int): provider id

        Return:
            bool: True if provider is valid
        """
        for provider in self.PROVIDERS:
            if provider[u'id']==provider_id and provider[u'enabled']:
                #provider is valid
                return True

        #provider was not found or is not enabled
        return False

    def set_provider(self, provider_id, apikey):
        """
        Set speechtotext provider

        Args:
            provider_id (int): provider id
            apikey (string): provider apikey
        """
        if provider_id is None:
            raise MissingParameter(u'Parameter provider is missing')
        if not self.__check_provider(provider_id):
            raise InvalidParameter(u'Specified provider is not valid. Please check list of supported provider.')
        if apikey is None or len(apikey.strip())==0:
            raise MissingParameter(u'Parameter apikey is missing')

        config = self._get_config()
        config[u'providerid'] = provider_id
        config[u'providerapikeys'][provider_id] = apikey

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
        #check params
        if self.__training_task is not None:
            raise CommandError(u'This action is disabled during voice model building')

        #save token
        config = self._get_config()
        config[u'hotwordtoken'] = token
        if not self._save_config(config):
            return False

        return True

    def __build_hotword(self):
        """
        Launch hotword training process
        """
        #check params
        if self.__training_task is not None:
            self.logger.debug(u'Try to launch voice model training while one is already running')
            raise CommandError(u'This action is disabled during voice model building')

        #launch model training
        self.__training_task = BuildPersonalVoiceModelTask(self._config[u'hotwordtoken'], self._config[u'hotwordfiles'], self.__end_of_training, self.logger)
        self.__training_task.start()

    def __end_of_training(self, error, voice_model_path):
        """
        Called when training process is terminated

        Args:
            error (string): Error message if error occured, None if no error occured
            voice_model_path (string): path to generated voice model
        """
        #reset variables
        self.__training_task = None

        #check errors
        if error is not None:
            #send error event to ui
            self.trainingKoEvent.send(to=u'rpc', params={u'error': error})
            
        #finalize training
        try:
            #get config
            config = self._get_config()

            #move files
            model = os.path.join(self.VOICE_MODEL_PATH, 'voice_model.pmdl')
            os.rename(voice_model_path, model)
            record1 = os.path.join(self.VOICE_MODEL_PATH, 'record1.wav')
            os.rename(config[u'hotwordfiles'][0], record1)
            record2 = os.path.join(self.VOICE_MODEL_PATH, 'record2.wav')
            os.rename(config[u'hotwordfiles'][1], record2)
            record3 = os.path.join(self.VOICE_MODEL_PATH, 'record3.wav')
            os.rename(config[u'hotwordfiles'][2], record3)

            #update config
            config[u'hotwordfiles'][0] = record1
            config[u'hotwordfiles'][1] = record2
            config[u'hotwordfiles'][2] = record3
            config[u'hotwordmodel'] = model
            self._save_config(config)

            #send event to ui model is generated
            self.trainingOkEvent.send(to=u'rpc')

        except:
            self.logger.exception('Exception during model training:')

            #send error event to ui
            self.trainingKoEvent.send(to=u'rpc', params={u'error': u'unable to move files'})

    def record_hotword(self):
        """
        Record hot-word and when all recordings are done, train personal model

        Return:
            tuple: status of hotword recordings::
                (True, False, False)
        """
        #check params
        if self.__training_task is not None:
            raise CommandError(u'This action is disabled during voice model building')

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

        #train if all recordings are ready
        if train:
            #launch hotword building
            self.__build_hotword()

        return self.__get_hotword_recording_status()

    def build_hotword(self):
        """
        Launch hotword model training manually
        """
        #check params
        if self.__training_task is not None:
            raise CommandError(u'This action is disabled during voice model building')

        #launch hotword building
        self.__build_hotword()

    def reset_hotword(self):
        """
        Clear all recorded file and personnal model
        """
        #check params
        if self.__training_task is not None:
            raise CommandError(u'This action is disabled during voice model building')

        #reset hotword
        try:
            config = self._get_config()
            if config[u'hotwordfiles'][0] and os.path.exists(config[u'hotwordfiles'][0]):
                os.remove(config[u'hotwordfiles'][0])
            if config[u'hotwordfiles'][1] and os.path.exists(config[u'hotwordfiles'][1]):
                os.remove(config[u'hotwordfiles'][1])
            if config[u'hotwordfiles'][2] and os.path.exists(config[u'hotwordfiles'][2]):
                os.remove(config[u'hotwordfiles'][2])
            if config[u'hotwordmodel'] and os.path.exists(config[u'hotwordmodel']):
                os.remove(config[u'hotwordmodel'])

        except:
            self.logger.exception(u'Error occured during hotword resetting:')
            raise CommandError(u'Internal error during reset')

        return True

    def enable_service(self):
        """
        Enable service
        """
        config = self._get_config()
        config[u'serviceenabled'] = True
        if not self._save_config(config):
            return False

        return True

    def disable_service(self):
        """
        Disable service
        """
        config = self._get_config()
        config[u'serviceenabled'] = False
        if not self._save_config(config):
            return False

        return True



