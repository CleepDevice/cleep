#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
import io
import requests
import os
import uuid
import raspiot.libs.internals.tools as Tools
from raspiot.utils import MissingParameter

class Snowboy():
    """
    Snowboy library
    """

    SNOWBOY_TRAIN_V1 = u'https://snowboy.kitt.ai/api/v1/train/'
    STT_LANGS = {
        u'ar': u'Arabic',
        u'zh': u'Chinese',
        u'nl': u'Dutch',
        u'en': u'English', 
        u'fr': u'French',
        u'dt': u'German',
        u'hi': u'Hindi',
        u'it': u'Italian',
        u'jp': u'Japanese',
        u'ko': u'Korean',
        u'fa': u'Persian',
        u'pl': u'Polish',
        u'pt': u'Portuguese',
        u'ru': u'Russian',
        u'es': u'Spanish',
        u'ot': u'Other'
    }
    AGE_GROUP = [u'0_9', u'10_19', u'20_29', u'30_39', u'40_49', u'50_59', u'60+']
    GENDER = [u'F', u'M']
        
    def __init__(self, cleep_filesystem, token=None):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            token (string): api token
        """
        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        self.cleep_filesystem = cleep_filesystem
        self.token = token

    def set_api_token(self, token):
        """
        Set api token

        Args:
            token (string): api token
        """
        if token is None or len(token)==0:
            raise MissingParameter(u'Parameter token is missing')

        self.token = token

    def train(self, record1, record2, record3, hotword=u'unknown'):
        """
        Train to get personal voice model

        Note:
            Code inspired from http://docs.kitt.ai/snowboy/#api-v1-train

        Args:
            record1 (string): path to first voice recording
            record2 (string): path to second voice recording
            record3 (string): path to last voice recording
            hotword (string): hotword corresponding to recordings

        Return:
            string: path to personal voice model (note that generated file is never deleted by the library)
        """
        #check params
        if record1 is None or not os.path.exists(record1):
            raise MissingParameter('Parameter record1 is invalid')
        if record2 is None or not os.path.exists(record1):
            raise MissingParameter('Parameter record2 is invalid')
        if record3 is None or not os.path.exists(record1):
            raise MissingParameter('Parameter record3 is invalid')
        if hotword is None or len(hotword)==0:
            raise MissingParameter('Parameter hotword is invalid')
        if self.token is None or len(self.token.strip())==0:
            raise MissingParameter('Please set snowboy api token before training')
        
        #prepare data
        #TODO append other data (age_group, gender, microphone and language)
        data = {
            u'name': hotword,
            u'token': self.token,
            u'microphone': 'raspberry',
            u'language': 'ot',
            u'universal_hotword': {
                u'language': 'ot'
            },
            u'voice_samples': [
                {u'wave': Tools.file_to_base64(record1)},
                {u'wave': Tools.file_to_base64(record2)},
                {u'wave': Tools.file_to_base64(record3)}
            ]
        }

        #post
        voice_model_path = '%s.pmdl' % os.path.join('/tmp', str(uuid.uuid4()))
        self.logger.debug('Personal voice model will be stored to %s' % voice_model_path)
        try:
            resp = requests.post(self.SNOWBOY_TRAIN_V1, json=data)
            if resp.status_code!=201:
                self.logger.debug('Train response %s: %s' % (resp.status_code, resp.content))
            if resp.ok:
                fd = self.cleep_filesystem.open(voice_model_path, u'wb')
                fd.write(resp.content)
                self.cleep_filesystem.close(fd)
                self.logger.info('Personal voice model wrote to %s' % voice_model_path)

                return voice_model_path
        except:
            self.logger.exception('Failed to train at %s with %s' % (self.SNOWBOY_TRAIN_V1, data))
            raise Exception(u'Error during personal voice model build')


