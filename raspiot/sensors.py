#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from bus import MessageRequest, MessageResponse, MissingParameter, InvalidParameter
from raspiot import RaspIot, CommandError
from task import Task
import time

__all__ = ['Sensors']

class Sensors(RaspIot):
    MODULE_CONFIG_FILE = 'sensors.conf'
    MODULE_DEPS = ['gpios']

    ONEWIRE_PATH = '/sys/bus/w1/devices/'
    ONEWIRE_SLAVE = 'w1_slave'
    TEMPERATURE_READING = 600 #in seconds
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

        #members
        self.__tasks = {}

        #load sensors
        for sensor in self._config['sensors'].keys():
            if self._config['sensors'][sensor]['type']=='motion':
                #motion sensor
                #nothing to do
                pass
            elif self._config['sensors'][sensor]['type']=='temperature':
                #temperature sensor
                self.__launch_temperature_task(self._config['sensors'][sensor])

    def stop(self):
        """
        Stop module
        """
        RaspIot.stop(self)
        #stop tasks
        for t in self.__tasks:
            self.__tasks[t].stop()

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
                    if event['event']=='event.gpio.on':

                        #check if task already running
                        if not sensor['on']:
                            #sensor not yet triggered, trigger it
                            self.logger.debug(' +++ Motion sensor "%s" turned on' % sensor['name'])

                            #motion sensor triggered
                            sensor['lastupdate'] = now
                            sensor['on'] = True
                            self.__save_config()

                            #new motion event
                            req = MessageRequest()
                            req.event = 'event.motion.on'
                            req.params = {'sensor':sensor['name'], 'lastupdate':now}
                            self.push(req)

                    elif event['event']=='event.gpio.off':
                        if sensor['on']:
                            #sensor is triggered, need to stop it
                            self.logger.debug(' --- Motion sensor "%s" turned off' % sensor['name'])

                            #motion sensor triggered
                            #duration = now - sensor['']
                            sensor['lastupdate'] = now
                            sensor['on'] = False
                            sensor['lastduration'] = event['params']['duration']
                            self.__save_config()

                            #new motion event
                            req = MessageRequest()
                            req.event = 'event.motion.off'
                            req.params = {'sensor': sensor['name'], 'duration':sensor['lastduration'], 'lastupdate':now}
                            self.push(req)
                        
            else:
                self.logger.debug('No sensor found')

    def __save_config(self):
        """
        Save current config
        """
        self._save_config(self._get_config())

    def __search_by_gpio(self, gpio):
        """
        Search sensor by gpio
        @param gpio: gpio to search
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

    def __scan_onewire_bus(self):
        """
        Scan for devices connected on 1wire bus
        @return dict of 1wire devices {'device name': 'device full path', ...}
        """
        out = {}
        devices = glob.glob(os.path.join(Sensors.ONEWIRE_PATH, '28*'))
        for device in devices:
            try:
                path = os.path.join(device, Sensors.ONEWIRE_SLAVE)
                out[device] = path
            except:
                self.logger.exception('Error during 1wire bus scan:')

        return out

    def __read_onewire_temperature(self, device):
        """
        Read temperature from 1wire device
        @param device: path to 1wire device
        @return (temperature celsius, temperature fahrenheit)
        """
        tempC = None
        tempF = None
        try:
            if os.path.exists(device):
                f = open(device, 'r')
                raw = f.readlines()
                f.close()
                equals_pos = raw[1].find('t=')
                if equals_pos!=-1:
                    tempString = raw[1][equals_pos+2:]
                    tempC = float(tempString) / 1000.0
                    tempF = tempC * 9.0 / 5.0 + 32.0
        except:
            self.logger.exception('Unable to read 1wire device file "%s":' % device)

        return (tempC, tempF)

    def __read_temperature(self, sensor):
        """
        Read temperature
        @param sensor: sensor to use
        """
        if sensor:
            #sensor specified, init variables
            tempC = None
            tempF = None

            #read temperature according to sensor kind
            if sensor['kind']=='1wire':
                (tempC, tempF) = self.__read_onewire_temperature(sensor['device'])
                if tempC and tempF:
                    #update sensor
                    sensor['temperature_c'] = tempC
                    sensor['temperature_f'] = tempF
                    sensor['lastupdate'] = time.time()

            #broadcast event
            if tempC and tempF:
                req = MessageRequest()
                req.event = 'event.temperature.value'
                req.params = {'sensor': sensor['name'], 'celsius':tempC, 'fahrenheit':tempF}
                self.push(req)

    def __launch_temperature_task(self, sensor):
        """
        Launch temperature reading task
        @param sensor: sensor name
        """
        if self.__tasks.has_key(sensor):
            #sensor has already task
            self.logger.warning('Sensor "%s" has already task running' % sensor)
            return False

        #launch task
        self.__tasks[sensor['name']] = Task(sensor['duration'], self.__read_temperature, [sensor])
        self.__tasks[sensor['name']].start()

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

    def get_onewire_devices(self):
        """
        Scan onewire bus and return found devices
        """
        return self.__scan_onewire_bus()

    def add_ds18b20(self, name, path, duration):
        """
        Add new 1wire temperature sensor (DS18B20)
        @param name: sensor name
        @param path: onewire device path
        @param duration: duration between temperature reading
        @return True if sensor added
        """
        #check values
        if not name:
            raise MissingParameter('Name parameter is missing')
        elif not path:
            raise MissingParameter('Path parameter is missing')
        elif not duration:
            raise MissingParameter('Duration parameter is missing')
        elif name in self.get_sensors():
            raise InvalidParameter('Name is already used')
        else:
            #try to read temperature
            (tempC, tempF) = self.__read_onewire_temperature(path)

            #sensor is valid, save new entry
            config = self._get_config()
            config['sensors'][name] = {
                'name': name,
                'device': path,
                'type': 'temperature',
                'kind': '1wire',
                'duration': duration,
                'lastupdate': time.time(),
                'temperature_c': tempC,
                'temperature_f': tempF
            }
            self._save_config(config)

            #launch temperature reading task
            self.__launch_temperature_task(config['sensors'][name])

            return True

        return False

    def add_motion(self, name, gpio, reverted):
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
        elif reverted is None:
            raise MissingParameter('Reverted parameter is missing')
        elif gpio in used_gpios:
            raise InvalidParameter('Gpio is already used')
        elif name in self.get_sensors():
            raise InvalidParameter('Name is already used')
        elif gpio not in self.raspi_gpios:
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
            config = self._get_config()
            config['sensors'][name] = {
                'name': name,
                'gpios': [gpio],
                'type': 'motion',
                'on': False,
                'reverted': reverted,
                'lastupdate': 0,
                'lastduration': 0
            }
            self._save_config(config)

            return True

        return False

    def delete_sensor(self, name):
        """
        Delete specified sensor
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
                req.command = 'delete_gpio'
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
