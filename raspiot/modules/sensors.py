#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.utils import MissingParameter, InvalidParameter, CommandError
from raspiot.raspiot import RaspIotMod
from raspiot.libs.task import Task
import time
import glob

__all__ = ['Sensors']

class Sensors(RaspIotMod):

    MODULE_CONFIG_FILE = 'sensors.conf'
    MODULE_DEPS = ['gpios']
    MODULE_DESCRIPTION = 'Implements easily and quickly sensors you need (temperature, motion, light...)'
    MODULE_LOCKED = False

    ONEWIRE_PATH = '/sys/bus/w1/devices/'
    ONEWIRE_SLAVE = 'w1_slave'
    TEMPERATURE_READING = 600 #in seconds
    DEFAULT_CONFIG = {
        'sensors': {}
    }

    TYPE_TEMPERATURE = 'temperature'
    TYPE_MOTION = 'motion'

    def __init__(self, bus, debug_enabled):
        """
        Constructor
        @param bus: bus instance
        @param debug_enabled: debug status
        """
        #init
        RaspIotMod.__init__(self, bus, debug_enabled)

        #members
        self.__tasks = {}
        self.raspi_gpios = {}

    def _start(self):
        """
        Start module
        """
        #raspi gpios
        self.raspi_gpios = self.get_raspi_gpios()

        #launch temperature reading tasks
        devices = self.get_module_devices()
        for uuid in devices:
            if devices[uuid]['type']==self.TYPE_TEMPERATURE:
                self.__start_temperature_task(devices[uuid])

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
        #self.logger.debug('*** event received: %s' % str(event))
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
            gpio_uuid = event['uuid']

            #search sensor
            sensor = self.__search_by_gpio(gpio_uuid)
            self.logger.debug('Found sensor: %s' % sensor)

            #process event
            if sensor:
                if sensor['type']==self.TYPE_MOTION:
                    #motion sensor
                    self.__process_motion_sensor(event, sensor)

    def get_onewire_devices(self):
        """
        Scan for devices connected on 1wire bus
        @return array of dict(<onewire device>, <onewire path>)
        """
        onewires = []

        devices = glob.glob(os.path.join(Sensors.ONEWIRE_PATH, '28*'))
        for device in devices:
            try:
                onewires.append({
                    'device': os.path.basename(device),
                    'path': os.path.join(device, Sensors.ONEWIRE_SLAVE)
                })
            except:
                self.logger.exception('Error during 1wire bus scan:')
                raise CommandError('Unable to scan onewire bus')

        return onewires

    def __read_onewire_temperature(self, sensor):
        """
        Read temperature from 1wire device
        @param sensor: path to 1wire device
        @return tuple(<celsius>, <fahrenheit>) or (None, None) if error occured
        """
        tempC = None
        tempF = None

        self.logger.debug('sensor: %s' % sensor)

        try:
            if os.path.exists(sensor['path']):
                f = open(sensor['path'], 'r')
                raw = f.readlines()
                f.close()
                equals_pos = raw[1].find('t=')

                if equals_pos!=-1:
                    tempString = raw[1][equals_pos+2:].strip()

                    #check value
                    if tempString=='85000' or tempString=='-62':
                        #invalid value
                        raise Exception('Invalid temperature "%s"' % tempString)

                    #convert temperatures
                    tempC = float(tempString) / 1000.0
                    tempF = tempC * 9.0 / 5.0 + 32.0

                    #apply offsets
                    tempC += sensor['offsetcelsius']
                    tempF += sensor['offsetfahrenheit']

                else:
                    #no temperature found in file
                    raise Exception('No temperature found for onewire %s' % sensor['path'])

            else:
                #onewire device doesn't exist
                raise Exception('Onewire device %s doesn\'t exist anymore' % sensor['path'])

        except:
            self.logger.exception('Unable to read 1wire device file "%s":' % sensor['path'])

        return (tempC, tempF)

    def __read_temperature(self, sensor):
        """
        Read temperature
        @param sensor: sensor object
        """
        if sensor['subtype']=='onewire':
            (tempC, tempF) = self.__read_onewire_temperature(sensor)
            self.logger.debug('Read temperature: %s°C - %s°F' % (tempC, tempF))
            if tempC is not None and tempF is not None:
                #temperature values are valid, update sensor values
                sensor['celsius'] = tempC
                sensor['fahrenheit'] = tempF
                sensor['lastupdate'] = int(time.time())
                if not self._update_device(sensor['uuid'], sensor):
                    self.logger.error('Unable to update device %s' % sensor['uuid'])

                #and send event
                now = int(time.time())
                self.send_event('sensors.temperature.update', {'sensor':sensor['name'], 'celsius':tempC, 'fahrenheit':tempF, 'lastupdate':now}, sensor['uuid'])

        else:
            self.logger.warning('Unknown temperature subtype "%s"' % sensor['subtype'])

    def __start_temperature_task(self, sensor):
        """
        start temperature reading task
        @param sensor: sensor object
        """
        if self.__tasks.has_key(sensor['uuid']):
            #sensor has already task
            self.logger.warning('Temperature sensor "%s" has already task running' % sensor['uuid'])
            return

        #start task
        self.logger.debug('Start temperature task (refresh every %s seconds) for sensor %s ' % (str(sensor['interval']), sensor['uuid']))
        self.__tasks[sensor['uuid']] = Task(float(sensor['interval']), self.__read_temperature, [sensor])
        self.__tasks[sensor['uuid']].start()

    def __stop_temperature_task(self, sensor):
        """
        Stop temperature reading task
        @param sensor: sensor object
        """
        if not self.__tasks.has_key(sensor['uuid']):
            #sensor hasn't already task
            self.logger.warning('Temperature sensor "%s" has no task to stop' % sensor['uuid'])
            return

        #stop task
        self.logger.debug('Stop temperature task for sensor %s' % sensor['uuid'])
        self.__tasks[sensor['uuid']].stop()
        del self.__tasks[sensor['uuid']]

    def __compute_temperature_offset(self, offset, offset_unit):
        """
        Compute temperature offset
        @param offset: offset value
        @param offset_unit: determine if specific offset is in celsius or fahrenheit
        @return tuple(<offset celsius>, <offset fahrenheit>)
        """
        if offset==0:
            #no offset
            return (0, 0)
        elif offset_unit=='celsius':
            #compute fahrenheit offset
            return (offset, offset*1.8+32)
        else:
            #compute celsius offset
            return ((offset-32)/1.8, offset)

    def __get_gpio_uses(self, gpio):
        """
        Return number of gpio uses
        @param uuid: device uuid (string)
        @return list of gpios or empty list if nothing found
        """
        devices = self._get_devices()
        uses = 0
        for uuid in devices:
            for gpio_ in devices[uuid]['gpios']:
                if gpio==gpio_['gpio']:
                    uses += 1

        return uses

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

    def add_temperature_onewire(self, name, device, path, interval, offset, offset_unit, gpio='GPIO4'):
        """
        Add new onewire temperature sensor (DS18B20)
        @param name: sensor name
        @param device: onewire device as returned by get_onewire_devices function
        @param path: onewire path as returned by get_onewire_devices function
        @param interval: interval between temperature reading (seconds)
        @param offset: temperature offset
        @param offset_unit: temperature offset unit (string 'celsius' or 'fahrenheit')
        @param gpio: onewire gpio (for now this parameter is useless because forced to default onewire gpio GPIO4)
        @return True if sensor added
        """
        #check values
        if name is None or len(name)==0:
            raise MissingParameter('Name parameter is missing')
        elif self._search_device('name', name) is not None:
            raise InvalidParameter('Name "%s" is already used' % name)
        elif device is None or len(device)==0:
            raise MissingParameter('Device parameter is missing')
        elif path is None or len(path)==0:
            raise MissingParameter('Path parameter is missing')
        elif interval is None:
            raise MissingParameter('Interval parameter is missing')
        elif interval<=0:
            raise InvalidParameter('Interval must be greater than 60')
        elif offset is None:
            raise MissingParameter('Offset parameter is missing')
        elif offset<0:
            raise InvalidParameter('Offset must be positive')
        elif offset_unit is None or len(offset_unit)==0:
            raise MissingParameter('Offset_unit paramter is missing')
        elif offset_unit not in ('celsius', 'fahrenheit'):
            raise InvalidParameter('Offset_unit must be equal to "celsius" or "fahrenheit"')
        elif gpio is None or len(gpio)==0:
            raise MissingParameter('Gpio parameter is missing')
        else:
            #compute offsets
            (offsetC, offsetF) = self.__compute_temperature_offset(offset, offset_unit)

            #configure gpio
            params = {
                'name': name+'_onewire',
                'gpio': gpio,
                'usage': 'onewire'
            }
            resp_gpio = self.send_command('reserve_gpio', 'gpios', params)
            if resp_gpio['error']:
                raise CommandError(resp_gpio['message'])
            resp_gpio = resp_gpio['data']

            #sensor is valid, save new entry
            sensor = {
                'name': name,
                'gpios': [{'gpio':gpio, 'gpio_uuid':resp_gpio['uuid']}],
                'device': device,
                'path': path,
                'type': self.TYPE_TEMPERATURE,
                'subtype': 'onewire',
                'interval': interval,
                'offsetcelsius': offsetC,
                'offsetfahrenheit': offsetF,
                'offset': offset,
                'offsetunit': offset_unit,
                'lastupdate': int(time.time()),
                'celsius': None,
                'fahrenheit': None
            }

            #read temperature
            (tempC, tempF) = self.__read_onewire_temperature(sensor)
            sensor['celsius'] = tempC
            sensor['fahrenheit'] = tempF

            #save sensor
            sensor = self._add_device(sensor)

            #launch temperature reading task
            self.__start_temperature_task(sensor)

        return True

    def update_temperature_onewire(self, uuid, name, interval, offset, offset_unit):
        """
        Update onewire temperature sensor
        @param uuid: sensor identifier
        @param name: sensor name
        @param interval: interval between reading (seconds)
        @param offset_unit: temperature offset unit (string 'celsius' or 'fahrenheit')
        @param offset: temperature offset
        @return True if device update is successful
        """
        device = self._get_device(uuid)
        if not uuid:
            raise MissingParameter('Uuid parameter is missing')
        elif device is None:
            raise InvalidParameter('Sensor "%s" doesn\'t exist' % name)
        elif name is None or len(name)==0:
            raise MissingParameter('Name parameter is missing')
        elif name!=device['name'] and self._search_device('name', name) is not None:
            raise InvalidParameter('Name "%s" is already used' % name)
        elif interval is None:
            raise MissingParameter('Interval parameter is missing')
        elif interval<=0:
            raise InvalidParameter('Interval must be greater than 60')
        elif offset is None:
            raise MissingParameter('Offset parameter is missing')
        elif offset<0:
            raise InvalidParameter('Offset must be positive')
        elif offset_unit is None or len(offset_unit)==0:
            raise MissingParameter('Offset_unit paramter is missing')
        elif offset_unit not in ('celsius', 'fahrenheit'):
            raise InvalidParameter('Offset_unit must be equal to "celsius" or "fahrenheit"')
        else:
            #compute offsets
            (offsetC, offsetF) = self.__compute_temperature_offset(offset, offset_unit)

            #update sensor
            device['name'] = name
            device['interval'] = interval
            device['offset'] = offset
            device['offsetunit'] = offset_unit
            device['offsetcelsius'] = offsetC
            device['offsetfahrenheit'] = offsetF
            if not self._update_device(uuid, device):
                raise commanderror('Unable to update sensor')

            #stop and launch temperature reading task
            self.__stop_temperature_task(device)
            self.__start_temperature_task(device)

        return True

    def add_motion_generic(self, name, gpio, reverted):
        """
        Add new generic motion sensor
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
            raise InvalidParameter('Name "%s" is already used' % name)
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
            resp_gpio = self.send_command('add_gpio', 'gpios', params)
            if resp_gpio['error']:
                raise CommandError(resp_gpio['message'])
            resp_gpio = resp_gpio['data']
                
            #gpio was added and sensor is valid, add new sensor
            data = {
                'name': name,
                'gpios': [{'gpio':gpio, 'gpio_uuid':resp_gpio['uuid']}],
                'type': self.TYPE_MOTION,
                'subtype': 'generic',
                'on': False,
                'reverted': reverted,
                'lastupdate': 0,
                'lastduration': 0,
            }
            if self._add_device(data) is None:
                raise CommandError('Unable to add sensor')

        return True

    def update_motion_generic(self, uuid, name, reverted):
        """
        Update generic motion sensor
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
        elif name!=device['name'] and self._search_device('name', name) is not None:
            raise InvalidParameter('Name "%s" is already used' % name)
        elif not name:
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
                raise commanderror('Unable to update sensor')

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
            #stop task if necessary
            if device['type']==self.TYPE_TEMPERATURE:
                self.__stop_temperature_task(device)

            #unconfigure gpios
            for gpio in device['gpios']:
                #is a reserved gpio (onewire?)
                resp = self.send_command('is_reserved_gpio', 'gpios', {'uuid': gpio['gpio_uuid']})
                self.logger.debug('is_reserved_gpio: %s' % resp)
                if resp['error']:
                    raise CommandError(resp['message'])
                
                #if gpio is reserved, check if no other sensor is using it
                delete = True
                if resp['data']==True:
                    if self.__get_gpio_uses(gpio['gpio'])>1:
                        #more than one devices are using this gpio, disable gpio unconfiguration
                        self.logger.debug('More than one device is using gpio, disable gpio deletion')
                        delete = False

                #unconfigure gpio
                if delete:
                    self.logger.debug('Unconfigure gpio %s' % gpio['gpio_uuid'])
                    resp = self.send_command('delete_gpio', 'gpios', {'uuid':gpio['gpio_uuid']})
                    if resp['error']:
                        raise CommandError(resp['message'])

            #sensor is valid, remove it
            if not self._delete_device(device['uuid']):
                raise CommandError('Unable to delete sensor')
            self.logger.debug('Device %s deleted sucessfully' % uuid)

        return True


if __name__ == '__main__':
    #testu
    o = Sensor()
    print o.get_raspi_gpios()
