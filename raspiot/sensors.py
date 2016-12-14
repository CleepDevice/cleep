#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from bus import MessageRequest, MessageResponse, MissingParameter, InvalidParameter
from raspiot import RaspIot, CommandError
from task import CountTask
import time

__all__ = ['Sensors']

class Sensors(RaspIot):
    MODULE_CONFIG_FILE = 'sensors.conf'
    MODULE_DEPS = ['gpios']

    ONEWIRE_PATH = '/sys/bus/w1/devices/'
    ONEWIRE_SLAVE = 'w1_slave'
    DEFAULT_CONFIG = {
        'sensors': {}
    }

    def __init__(self, bus):
        #init
        RaspIot.__init__(self, bus)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

        #check config
        self._check_config(Sensors.DEFAULT_CONFIG)

        #raspi gpios
        self.raspi_gpios = self.get_raspi_gpios()

    def __search_by_gpio(self, gpio):
        """
        Search sensor by gpio
        @return sensor object or None if nothing found
        """
        found_sensor = None
        sensors = self.get_sensors()
        for sensor in sensors:
            for gpio_ in sensors[sensor]['gpios']:
                if gpio_==gpio:
                    #found gpio
                    found_sensor = sensors[sensor]
                    break
        return found_sensor

    def event_received(self, event):
        """
        Event received
        """
        self.logger.debug('*** event received: %s' % str(event))
        #drop startup events
        if event['startup']:
            self.logger.debug('Drop startup event')
            return 

        if event['event'] in ('event.gpio.on', 'event.gpio.off'):
            #drop gpio init
            if event['params']['init']:
                self.logger.debug('Drop gpio init event')
                return

            #get current time
            now = int(time.time())

            #get event gpio
            gpio = event['params']['gpio']

            #search sensor
            sensor = self.__search_by_gpio(gpio)
            #self.logger.debug('Found sensor: %s' % sensor)

            #process event
            if sensor:
                if sensor['type']=='motion':
                    #motion sensor
                    
                    #if (event['event']=='event.gpio.on' and sensor['on_state']==1) or (event['event']=='event.gpio.off' and sensor['on_state']==0):
                    if event['event']=='event.gpio.on':

                        #check if task already running
                        if not sensor['on']:
                            #sensor not yet triggered, trigger it
                            self.logger.debug(' +++ Motion sensor "%s" turned on' % sensor['name'])

                            #motion sensor triggered
                            sensor['timestamp'] = now
                            sensor['on'] = True

                            #new motion event
                            req = MessageRequest()
                            req.event = 'event.motion.on'
                            req.params = {'sensor': sensor['name']}
                            self.push(req)

                    elif event['event']=='event.gpio.off':
                        if sensor['on']:
                            #sensor is triggered, need to stop it
                            self.logger.debug(' --- Motion sensor "%s" turned off' % sensor['name'])

                            #motion sensor triggered
                            duration = now - sensor['timestamp']
                            sensor['timestamp'] = 0
                            sensor['on'] = False

                            #new motion event
                            req = MessageRequest()
                            req.event = 'event.motion.off'
                            req.params = {'sensor': sensor['name'], 'duration':duration}
                            self.push(req)
                        
            else:
                self.logger.debug('No sensor found')

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
                    pass
            except:
                self.logger.exception('')

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
        return self._config['sensors']

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
        elif name in self.get_sensors():
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
            config = self._get_config()
            config['sensors'][name] = {
                'name':name,
                'gpios':[gpio],
                'type':'motion'
            }
            self._save_config(config)
            return True
        return False

    def add_motion(self, name, gpio, on_duration, on_state):
        """
        Add new motion sensor
        @param name: sensor name
        @param gpio: sensor gpio
        @param on_duration: time to stay on (in sec)
        @param on_state: set gpio state when on (0 for LOW, 1 fo HIGH)
        @return True if sensor added
        """
        #get used gpios
        used_gpios = self.get_used_gpios()

        #check values
        if not name:
            raise MissingParameter('Name parameter is missing')
        elif not gpio:
            raise MissingParameter('Gpio parameter is missing')
        elif not on_duration:
            raise MissingParameter('On duration parameter is missing')
        elif not on_state:
            raise MissingParameter('On state parameter is missing')
        elif gpio in used_gpios:
            raise InvalidParameter('Gpio is already used')
        elif name in self.get_sensors():
            raise InvalidParameter('Name is already used')
        elif gpio not in self.raspi_gpios:
            raise InvalidParameter('Gpio does not exist for this raspberry pi')
        elif on_duration <= 0:
            raise InvalidParameter('On duration must be positive value')
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
            config = self._get_config()
            config['sensors'][name] = {
                'name': name,
                'gpios': [gpio],
                'type': 'motion',
                'on': False,
                'on_duration': 30.0,
                'on_state': on_state,
                'timestamp': 0
            }
            self._save_config(config)

            return True

        return False

    def del_sensor(self, name):
        """
        Del specified sensor
        @param name: sensor name
        @return True if deletion succeed
        """
        config = self._get_config()
        if not name:
            raise MissingParameter('"name" parameter is missing')
        elif name not in config:
            raise InvalidParameter('Sensor "%s" doesn\'t exist' % name)
        else:
            #unconfigure gpios
            for gpio in config['sensors'][name]['gpios']:
                req = MessageRequest()
                req.to = 'gpios'
                req.command = 'del_gpio'
                req.params = {'gpio':gpio}
                resp = self.push(req)
                if resp['error']:
                    raise CommandError(resp['message'])

            #sensor is valid, remove it
            del config['sensors'][name]
            self._save_config(config)

if __name__ == '__main__':
    #testu
    o = Sensor()
    print o.get_raspi_gpios()
