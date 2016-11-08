#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import glob
import uuid as moduuid
import json
from threading import Lock
import RPi.GPIO as GPIO
from bus import BusClient
from webserver import dictToList

#logging.basicConfig(filename='agosqueezebox.log', level=logging.INFO, format="%(asctime)s %(levelname)s : %(message)s")
#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
logger = logging.getLogger(__name__)

# RASPI GPIO numbering scheme:
# @see http://raspi.tv/2013/rpi-gpio-basics-4-setting-up-rpi-gpio-numbering-systems-and-inputs
# GPIO#   Pin#  Dedicated I/O
# GPIO2   3     
# GPIO3   5     
# GPIO4   7     *
# GPIO7   26    
# GPIO8   24    
# GPIO9   21    
# GPIO10  19    
# GPIO11  23    
# GPIO14  8     
# GPIO15  10    
# GPIO17  11    *
# GPIO18  12    *
# GPIO22  15    *
# GPIO23  16    *
# GPIO24  18    *
# GPIO25  22    *
# GPIO27  13    *

class Outputs(BusClient):
    CONF_DIR = 'outputs.conf'
    GPIOS = {   'GPIO4' : 7,
                'GPIO17': 11,
                'GPIO18': 12,
                'GPIO22': 15,
                'GPIO23': 16,
                'GPIO24': 18,
                'GPIO25': 22,
                'GPIO27': 13,
                'GPIO2' : 3,
                'GPIO3' : 5,
                'GPIO7 ': 26,
                'GPIO8' : 24,
                'GPIO9' : 21,
                'GPIO10': 19,
                'GPIO11': 23,
                'GPIO14': 8,
                'GPIO15': 10
    } #first items are dedicated GPIO ports. Then possible GPIO ports

    def __init__(self, bus):
        BusClient.__init__(self, bus)
        self.__configLock = Lock()
        self.config = self.__loadConfig()

        #configure RasPi
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        for outputId in self.config:
            self.__configureGpio(self.config[outputId]['pin'])

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

    def __configureGpio(self, gpio):
        """Configure GPIO pin"""
        try:
            logger.debug('Configure GPIO pin #%d' % gpio)
            GPIO.setup(gpio, GPIO.OUT)
            GPIO.output(gpio, GPIO.HIGH)
            return True
        except:
            logger.exception('Exception during GPIO configuration:')
            return False

    def getGpios(self):
        """
        Return available GPIO pins
        """
        return self.GPIOS.keys()

    def getConfiguredGpios(self):
        """
        Return configured gpios
        """

    def setOutputs(self, items):
        """Configure outputs"""
        #check outputs
        #format: [ ['<output number>','<gpio pin number>'], [...] ]
        #[{u'gpio': u'GPIO2', u'id': 0}, {u'gpio': u'GPIO2', u'id': 1}]
        config = {}
        try:
            gpios = []
            outputs = []
            for item in items:
                if outputs.count(item['id'])==0 and gpios.count(item['gpio'])==0:
                    #no duplicates
                    outputs.append(item['id'])
                    gpios.append(item['gpio'])
                    config[item['id']] = {'gpio':item['gpio'], 'pin':self.GPIOS[item['gpio']], 'on':False}
                    self.__configureGpio(self.GPIOS[item['gpio']])
                else:
                    logger.warning('Duplicates found, item dropped! [%s]' % item)
            #save config
            self.__saveConfig(config)
            #reload config
            self.config = self.__loadConfig()
        except:
            logger.exception('Exception setting outputs:')
        return False, '', None
        
    def getOutputs(self):
        """Return all outputs"""
        return dictToList(self.config)

    def turnOn(self, outputId, gpio):
        """Turn on specified gpio"""
        try:
            outputId = str(outputId)
            if not self.GPIOS.has_key(gpio):
                return 'Gpio "%s" not found' % gpio, None
            if not self.config.has_key(outputId):
                return 'Output id "%s" not found' % outputId, None
                
            logger.debug('turn on GPIO %d' % self.GPIOS[gpio])
            GPIO.output(self.GPIOS[gpio], GPIO.LOW)
            self.config[outputId]['on'] = True
            return False, '', True
        except:
            logger.exception('Exception on turnOn:')
            return True, 'Failed to turn on', None

    def turnOff(self, outputId, gpio):
        """Turn off specified gpio"""
        try:
            outputId = str(outputId)
            if not self.GPIOS.has_key(gpio):
                return True, 'Gpio "%s" not found' % gpio, None
            if not self.config.has_key(outputId):
                return True, 'Output id "%s" not found' % outputId, None
            
            logger.debug('turn off GPIO %d' % self.GPIOS[gpio])
            GPIO.output(self.GPIOS[gpio], GPIO.HIGH)
            self.config[outputId]['on'] = False
            return False, '', False
        except:
            logger.exception('Exception on turnOn:')
            return True, 'Failed to turn off', None


if __name__ == '__main__':
    #testu
    o = Outputs()
    print o.getGpios()
