#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.bus import MissingParameter, InvalidParameter
from raspiot.raspiot import RaspIot, CommandError
from raspiot.libs.task import Task
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

    def __init__(self, bus, debug_enabled):
        #init
        RaspIot.__init__(self, bus, debug_enabled)

        #members
        self.__tasks = {}
        self.raspi_gpios = {}

    def _start(self):
        """
        Start module
        """
        #raspi gpios
        self.raspi_gpios = self.get_raspi_gpios()

        #launch temperature reading task
        devices = self.get_module_devices()
        for uuid in devices:
            if devices[uuid]['type']=='temperature':
                self.__launch_temperature_task(devices[uuid])
        #for sensor in self._config['sensors'].keys():
        #    if self._config['sensors'][sensor]['type']=='motion':
        #        #motion sensor, nothing to do
        #        pass
        #    elif self._config['sensors'][sensor]['type']=='temperature':
        #        #temperature sensor
        #        self.__launch_temperature_task(self._config['sensors'][sensor])

    def _stop(self):
        """
        Stop module
        """
        #stop tasks
        for t in self.__tasks:
            self.__tasks[t].stop()

    def __search_by_gpio(self, gpio_uuid):
        """
        Search sensor connected to specified gpio_uuid
        @param gpio_uuid: gpio uuid to search
        @return Sensor data or None if nothing found
        """
        devices = self.get_module_devices()
        for uuid in devices:
            for gpio in devices[uuid]['gpios']:
                if gpio['gpio_uuid']==gpio_uuid:
                    #sensor found
                    return devices[uuid]

        #nothing found
        return None

    def __process_motion_sensor(self, event, sensor):
        """
        Process motion event
        """
        #get current time
        now = int(time.time())

        if event['event']=='gpios.gpio.on':
            #check if task already running
            if not sensor['on']:
                #sensor not yet triggered, trigger it
                self.logger.debug(' +++ Motion sensor "%s" turned on' % sensor['name'])

                #motion sensor triggered
                sensor['lastupdate'] = now
                sensor['on'] = True
                self._update_device(sensor['uuid'], sensor)

                #new motion event
                self.send_event('sensors.motion.on', {'sensor':sensor['name'], 'lastupdate':now}, sensor['uuid'])

        elif event['event']=='gpios.gpio.off':
            if sensor['on']:
                #sensor is triggered, need to stop it
                self.logger.debug(' --- Motion sensor "%s" turned off' % sensor['name'])

                #motion sensor triggered
                sensor['lastupdate'] = now
                sensor['on'] = False
                sensor['lastduration'] = event['params']['duration']
                self._update_device(sensor['uuid'], sensor)

                #new motion event
                self.send_event('sensors.motion.off', {'sensor': sensor['name'], 'duration':sensor['lastduration'], 'lastupdate':now}, sensor['uuid'])

    def event_received(self, event):
        """
        Event received
        """
        self.logger.debug('*** event received: %s' % str(event))
        #drop startup events
        if event['startup']:
            self.logger.debug('Drop startup event')
            return 

        if event['event'] in ('gpios.gpio.on', 'gpios.gpio.off'):
            #drop gpio init
            if event['params']['init']:
                self.logger.debug('Drop gpio init event')
                return

            #get uuid event
            #gpio = event['params']['gpio']
            gpio_uuid = event['uuid']

            #search sensor
            sensor = self.__search_by_gpio(gpio_uuid)
            self.logger.debug('Found sensor: %s' % sensor)

            #process event
            if sensor:
                if sensor['type']=='motion':
                    #motion sensor
                    self.__process_motion_sensor(event, sensor)
            else:
                raise Exception('Sensor using gpio %s was not found!' % gpio_uuid)

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
                self.send_event('sensors.temperature.value', {'sensor': sensor['name'], 'celsius':tempC, 'fahrenheit':tempF}, sensor['uuid'])

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

    def get_module_config(self):
        """
        Get full module configuration
        """
        config = {}
        config['raspi_gpios'] = self.get_raspi_gpios()
        return config

    def get_raspi_gpios(self):
        """
        Get raspi gpios
        """
        resp = self.send_command('get_raspi_gpios', 'gpios')
        if resp['error']:
            self.logger.error(resp['message'])
            return {}
        else:
            return resp['data']

    def get_assigned_gpios(self):
        """
        Return assigned gpios
        """
        resp = self.send_command('get_assigned_gpios', 'gpios')
        if resp['error']:
            self.logger.error(resp['message'])
            return {}
        else:
            return resp['data']

    def get_onewire_devices(self):
        """
        Scan onewire bus and return found devices
        """
        return self.__scan_onewire_bus()

    def add_ds18b20(self, name, path, duration, offset):
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
            #config['sensors'][name] = {
            #    'name': name,
            #    'gpios': [gpio],
            #    'type': 'motion',
            #    'on': False,
            #    'reverted': reverted,
            #    'lastupdate': 0,
            #    'lastduration': 0
            #}
            config['sensors'][name] = {
                'name': name,
                'device': path,
                'type': 'temperature',
                'subtype': '1wire',
                'duration': duration,
                'offset': offset,
                'lastupdate': time.time(),
                'temperature_c': tempC,
                'temperature_f': tempF
            }
            self._save_config(config)

            #launch temperature reading task
            self.__launch_temperature_task(config['sensors'][name])

        return True

    def add_motion(self, name, gpio, reverted):
        """
        Add new motion sensor
        @param name: sensor name
        @param gpio: sensor gpio
        @param reverted: set if gpio is reverted or not (bool)
        @return True if sensor added successfully
        """
        #get assigned gpios
        assigned_gpios = self.get_assigned_gpios()

        #check values
        if not name:
            raise MissingParameter('Name parameter is missing')
        elif not gpio:
            raise MissingParameter('Gpio parameter is missing')
        elif reverted is None:
            raise MissingParameter('Reverted parameter is missing')
        elif gpio in assigned_gpios:
            raise InvalidParameter('Gpio is already used')
        elif self._search_device('name', name) is not None:
            raise InvalidParameter('Name is already used')
        elif gpio not in self.raspi_gpios:
            raise InvalidParameter('Gpio does not exist for this raspberry pi')
        else:
            #configure gpio
            params = {
                'name': name+'_motion',
                'gpio': gpio,
                'mode': 'in',
                'keep': False,
                'reverted':reverted
            }
            #resp = self.push(req)
            resp_gpio = self.send_command('add_gpio', 'gpios', params)
            if resp_gpio['error']:
                raise RaspIot.CommandError(resp['message'])
            resp_gpio = resp_gpio['data']
                
            #gpio was added and sensor is valid, add new sensor
            data = {
                'name': name,
                'gpios': [{'gpio':gpio, 'gpio_uuid':resp_gpio['uuid']}],
                'type': 'motion',
                'on': False,
                'reverted': reverted,
                'lastupdate': 0,
                'lastduration': 0,
            }
            if self._add_device(data) is None:
                raise CommandError('Unable to add sensor')

        return True

    def delete_sensor(self, uuid):
        """
        Delete specified sensor
        @param uuid: sensor identifier
        @return True if deletion succeed
        """
        device = self._get_device(uuid)
        if not uuid:
            raise MissingParameter('Uuid parameter is missing')
        elif device is None:
            raise InvalidParameter('Sensor "%s" doesn\'t exist' % name)
        else:
            #unconfigure gpios
            for gpio in device['gpios']:
                resp = self.send_command('delete_gpio', 'gpios', {'uuid':gpio['gpio_uuid']})
                if resp['error']:
                    raise RaspIot.CommandError(resp['message'])

            #sensor is valid, remove it
            if not self._delete_device(device['uuid']):
                raise CommandError('Unable to delete sensor')

        return True

    def update_sensor(self, uuid, name, reverted):
        """
        Update specified sensor
        @param uuid: sensor identifier
        @param name: sensor name
        @param reverted: set if gpio is reverted or not (bool)
        @return True if device update is successful
        """
        device = self._get_device(uuid)
        if not uuid:
            raise MissingParameter('Uuid parameter is missing')
        elif device is None:
            raise InvalidParameter('Sensor "%s" doesn\'t exist' % name)
        if not name:
            raise MissingParameter('Name parameter is missing')
        elif reverted is None:
            raise MissingParameter('Reverted parameter is missing')
        elif self._search_device('name', name) is not None:
            raise InvalidParameter('Name is already used')
        else:
            #update sensor
            device['name'] = name
            device['reverted'] = reverted
            if not self._update_device(uuid, device):
                raise CommandError('Unable to update sensor')

        return True

if __name__ == '__main__':
    #testu
    o = Sensor()
    print o.get_raspi_gpios()
