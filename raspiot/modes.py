#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import glob
import uuid as moduuid
import json
from threading import Lock

#logging.basicConfig(filename='agosqueezebox.log', level=logging.INFO, format="%(asctime)s %(levelname)s : %(message)s")
#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
logger = logging.getLogger(__name__)

class Modes():
    CONF_DIR = 'modes.conf'

    def __init__(self):
        self.__configLock = Lock()
        self.config = self.__loadConfig()

    def __loadConfig(self):
        """load config file"""
        self.__configLock.acquire(True)
        out = None
        try:
            if os.path.exists(self.CONF_DIR):
                f = open(self.CONF_DIR, 'r')
                raw = f.read()
                f.close()
            else:
                #no conf file yet. Create default one
                f = open(self.CONF_DIR, 'w')
                default = {}
                raw = json.dumps(default)
                f.write(raw)
                f.close()
            out = json.loads(raw)
        except:
            logger.exception('Unable to load config file %s:' % self.CONF_DIR)
        self.__configLock.release()
        return out

    def __saveConfig(self, config):
        """save config file"""
        self.__configLock.acquire(True)
        out = False
        try:
            f = open(self.CONF_DIR, 'w')
            f.write(json.dumps(config))
            f.close()
            self.config = config
            out = True
        except:
            logger.exception('Unable to write config file %s:' % self.CONF_DIR)
        self.__configLock.release()
        return out

    def setModes(self, items):
        """Configure modes"""
        config = {}
        try:
            for item in items:
                config[item['id']] = {'name':item['name'], 'setpoint':item['setpoint'], 'on':item['on']}
            #save config
            self.__saveConfig(config)
        except:
            logger.exception('Exception setting outputs:')
        return False, '', None
        
    def getModes(self):
        """Return all modes"""
        return False, '', self.config

