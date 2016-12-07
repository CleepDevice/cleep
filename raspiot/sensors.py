#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from bus import MessageRequest, MessageResponse, MissingParameter, InvalidParameter
from raspiot import RaspIot, CommandError
from task import Task

__all__ = ['Sensors']

class Sensors(RaspIot):
    MODULE_CONFIG_FILE = 'sensors.conf'
    MODULE_DEPS = ['gpios']

    ONEWIRE_PATH = '/sys/bus/w1/devices/'
    ONEWIRE_SLAVE = 'w1_slave'

    def __init__(self, bus):
        #init
        RaspIot.__init__(self, bus)
        self.logger = logging.getLogger(self.__class__.__name__)

        #raspi gpios
        self.raspi_gpios = self.get_raspi_gpios()

    """
    def __scan_onewire_devices(self):
        """
        Scan for devices connected on 1wire bus
        """
        devices = glob.glob(os.path.join(Sensors.ONEWIRE_PATH, '28*'))
        for device in devices:
            try:
                path = os.path.join(device, Sensors.ONEWIRE_SLAVE)
                f = open(path, 'r')
                raw = f.readlines()
                f.close()
                equals_pos = raw[1].find('t=')
                if equals_pos != -1:
                    
            except:
    """


    def get_raspi_gpios(self):
        """
        Get raspi gpios
        """
        req = MessageRequest()
        req.to = 'gpios'
        req.command = 'get_raspi_gpios'
        resp = self.push(req)
        if resp['error']:
            self.logger.error(resp['message'])
            return {}
        else:
            return resp['data']

    def get_used_gpios(self):
        """
        Return used gpios
        """
        req = MessageRequest()
        req.to = 'gpios'
        req.command = 'get_gpios'
        resp = self.push(req)
        if resp['error']:
            self.logger.error(resp['message'])
            return {}
        else:
            return resp['data']

    def get_sensors(self):
        """
        Return full config (shutter)
        """
        return self._config

    def add_ds18b20(self, name):
        """
        Add new motion sensor
        @param name: sensor name
        @param gpio: sensor gpio
        @return True if sensor added
        """
        #get used gpios
        used_gpios = self.get_used_gpios()

        #check values
        if not name:
            raise MissingParameter('Name parameter is missing')
        elif not gpio:
            raise MissingParameter('Gpio parameter is missing')
        elif gpio in used_gpios:
            raise InvalidParameter('Gpio is already used')
        elif name in self.get_devices():
            raise InvalidParameter('Name is already used')
        elif shutter_open not in self.raspi_gpios:
            raise InvalidParameter('Gpio does not exist for this raspberry pi')
        else:
            #configure gpio
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'add_gpio'
            req.params = {'name':name+'_motion', 'gpio':gpio, 'mode':'in', 'keep':False}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])
                
            #sensor is valid, save new entry
            self.logger.debug('MOTION name=%s gpio=%s' % (str(name), str(gpio)))
            config = self.get_devices()
            config[name] = {'name':name, 'gpios':[gpio], 'type':'motion'}
            self._save_config(config)
            return True
        return False

    def add_motion(self, name, gpio):
        """
        Add new motion sensor
        @param name: sensor name
        @param gpio: sensor gpio
        @return True if sensor added
        """
        #get used gpios
        used_gpios = self.get_used_gpios()

        #check values
        if not name:
            raise MissingParameter('Name parameter is missing')
        elif not gpio:
            raise MissingParameter('Gpio parameter is missing')
        elif gpio in used_gpios:
            raise InvalidParameter('Gpio is already used')
        elif name in self.get_devices():
            raise InvalidParameter('Name is already used')
        elif shutter_open not in self.raspi_gpios:
            raise InvalidParameter('Gpio does not exist for this raspberry pi')
        else:
            #configure gpio
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'add_gpio'
            req.params = {'name':name+'_motion', 'gpio':gpio, 'mode':'in', 'keep':False}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])
                
            #sensor is valid, save new entry
            self.logger.debug('MOTION name=%s gpio=%s' % (str(name), str(gpio)))
            config = self.get_devices()
            config[name] = {'name':name, 'gpios':[gpio], 'type':'motion'}
            self._save_config(config)
            return True
        return False

    def del_sensor(self, name):
        """
        Del specified sensor
        @param name: sensor name
        @return True if deletion succeed
        """
        config = self.get_devices()
        if not name:
            raise MissingParameter('"name" parameter is missing')
        elif name not in config:
            raise InvalidParameter('Sensor "%s" doesn\'t exist' % name)
        else:
            #unconfigure gpios
            for gpio in config[name]['gpios']:
                req = MessageRequest()
                req.to = 'gpios'
                req.command = 'del_gpio'
                req.params = {'gpio':gpio}
                resp = self.push(req)
                if resp['error']:
                    raise CommandError(resp['message'])

            #sensor is valid, remove it
            del config[name]
            self._save_config(config)

if __name__ == '__main__':
    #testu
    o = Sensor()
    print o.get_raspi_gpios()
