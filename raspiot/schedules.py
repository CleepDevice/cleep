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

class Schedules():
    CONF_DIR = 'schedules.conf'

    def __init__(self):
        self.__configLock = Lock()
        self.config = self.__loadConfig()
        logging.debug(self.config)

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

    def setSchedules(self, zone, items):
        """Configure schedules"""
        #format: [ {u'hrDay': u'Monday', u'day': 1, u'schedules': [{u'start': u'00:00', u'end': u'00:00', u'mode':<id>}, ...]}, ... ]
        config = {0:[], 1:[], 2:[], 3:[], 4:[], 5:[], 6:[]}
        error = False
        msg = ''
        try:
            #logging.debug('RECEIVED ITEMS')
            #logging.debug(items);
            for item in items:
                #logging.debug("item")
                #logging.debug(item)
                if config.has_key(item['day']):
                    for schedule in item['schedules']:
                        #logging.debug("schedule")
                        #logging.debug(schedule)
                        #TODO check times
                        #TODO check duplicates
                        #logging.debug('Add this schedule to config[%d]' % item['day'])
                        #logging.debug(config[item['day']])
                        config[item['day']].append(schedule)
                else:
                    #invalid config, do nothing
                    raise Exception('Invalid specified config, nothing done')

            #set config for zone
            self.config[zone] = config

            #save config
            #logging.debug('GENERATED CONFIG')
            #logging.debug(self.config)
            self.__saveConfig(self.config)
            #reload config
            self.config = self.__loadConfig()
        except:
            logger.exception('Exception setting schedules:')
            error = True
            msg = 'Internal error'
        return error, msg, self.config
        
    def getSchedules(self):
        """Return all outputs"""
        logging.debug(self.config)
        return False, '', self.config


if __name__ == '__main__':
    #testu
    s = schedules()

