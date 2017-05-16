#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import glob
import uuid as moduuid
import json
from threading import Lock, Thread
import RPi.GPIO as GPIO
from raspiot.utils import InvalidParameter, Unauthorized, MissingParameter, CommandError
from raspiot.raspiot import RaspIotModule
import time

__all__ = ['Gpios']


class GpioInputWatcher(Thread):
    """
    Class that watches for changes on specified input pin
    We don't use GPIO lib implemented threaded callback due to a bug when executing a timer within callback function.

    Note:
        This object doesn't configure pin!
    """

    DEBOUNCE = 0.20

    def __init__(self, pin, uuid, on_callback, off_callback, level=GPIO.LOW):
        """
        Constructor

        Params: 
            pin (int): gpio pin number
            uuid (string): device uuid
            on_callback (function): on callback
            off_callback (function): off callback
            level (GPIO.LOW|GPIO.HIGH): triggered level
        """
        #init
        Thread.__init__(self)
        Thread.daemon = True
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)
        self.__debug_pin = None
        self.uuid = uuid

        #members
        self.continu = True
        self.pin = pin
        self.level = level
        self.debounce = GpioInputWatcher.DEBOUNCE
        self.on_callback = on_callback
        self.off_callback = off_callback

    def stop(self):
        """
        Stop process
        """
        self.continu = False

    def run(self):
        """
        Run watcher
        """
        last_level = None
        time_on = 0
        try:
            while self.continu:
                #get level
                level = GPIO.input(self.pin)
                if self.pin==self.__debug_pin:
                    self.logger.debug('thread=%s level=%s last_level=%s' % (str(self.ident), str(level), str(last_level)))

                if last_level is None:
                    #first run, nothing to do except init values
                    pass

                elif level!=last_level and level==self.level:
                    if self.pin==self.__debug_pin:
                        self.logger.debug('input %s on' % str(self.pin))
                    time_on = time.time()
                    self.on_callback(self.uuid)
                    time.sleep(self.debounce)

                elif level!=last_level:
                    if self.pin==self.__debug_pin:
                        self.logger.debug('input %s off' % str(self.pin))
                    if self.off_callback:
                        self.off_callback(self.uuid, time.time()-time_on)
                    time.sleep(self.debounce)

                else:
                    time.sleep(0.125)

                #update last level
                last_level = level
        except:
            self.logger.exception('Exception in GpioInputWatcher')



# RASPI GPIO numbering scheme:
# @see http://raspi.tv/2013/rpi-gpio-basics-4-setting-up-rpi-gpio-numbering-systems-and-inputs
# GPIO#   Pin#  Dedicated I/O
# --------A/B----------------
# GPIO2   3                     
# GPIO3   5     
# GPIO4   7     *
# GPIO14  8     
# GPIO15  10    
# GPIO17  11    *
# GPIO18  12    *
# GPIO27  13    *
# GPIO22  15    *
# GPIO23  16    *
# GPIO24  18    *
# GPIO10  19    
# GPIO9   21    
# GPIO25  22    *
# GPIO11  23    
# GPIO8   24    
# GPIO7   26    
# -------A+/B+/B2/Zero/B3--------
# GPIO0   27    
# GPIO1   28
# GPIO5   29    *
# GPIO6   31    *
# GPIO12  32    *
# GPIO13  33    *
# GPIO19  35
# GPIO16  36
# GPIO26  37    *
# GPIO20  38
# GPIO21  40
class Gpios(RaspIotModule):
    """
    Raspberry pi gpios class
    """

    MODULE_CONFIG_FILE = 'gpios.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = 'Gives you access to raspberry pins to configure your inputs/ouputs as you wish.'
    MODULE_LOCKED = False
    MODULE_URL = None
    MODULE_TAGS = []

    GPIOS_REV1 = {'GPIO0' : 3,
                  'GPIO1' : 5,
                  'GPIO4' : 7,
                  'GPIO14': 8,
                  'GPIO15': 10,
                  'GPIO17': 11,
                  'GPIO18': 12,
                  'GPIO21': 13,
                  'GPIO22': 15,
                  'GPIO23': 16,
                  'GPIO24': 18,
                  'GPIO10': 19,
                  'GPIO9' : 21,
                  'GPIO25': 22,
                  'GPIO11': 23,
                  'GPIO8' : 24,
                  'GPIO7' : 26
    }
    GPIOS_REV2 = {'GPIO4' : 7,
                  'GPIO17': 11,
                  'GPIO18': 12,
                  'GPIO22': 15,
                  'GPIO23': 16,
                  'GPIO24': 18,
                  'GPIO25': 22,
                  'GPIO27': 13,
                  'GPIO2' : 3,
                  'GPIO3' : 5,
                  'GPIO7' : 26,
                  'GPIO8' : 24,
                  'GPIO9' : 21,
                  'GPIO10': 19,
                  'GPIO11': 23,
                  'GPIO14': 8,
                  'GPIO15': 10
    }
    GPIOS_REV3 = {'GPIO5' : 29,
                  'GPIO6' : 31,
                  'GPIO12': 32,
                  'GPIO13': 33,
                  'GPIO26': 37,
                  'GPIO0' : 27,
                  'GPIO1' : 28,
                  'GPIO19': 35,
                  'GPIO16': 36,
                  'GPIO20': 38,
                  'GPIO21': 40
    }
    PINS_REV1 = {1 : '3.3V',
                 2 : '5V',
                 3 : 'GPIO0',
                 4 : '5V',
                 5 : 'GPIO1',
                 6 : 'GND',
                 7 : 'GPIO4',
                 8 : 'GPIO14',
                 9 : 'GND',
                 10: 'GPIO15',
                 11: 'GPIO17',
                 12: 'GPIO18',
                 13: 'GPIO21',
                 14: 'GND',
                 15: 'GPIO22',
                 16: 'GPIO23',
                 17: '3.3V',
                 18: 'GPIO24',
                 19: 'GPIO10',
                 20: 'GND',
                 21: 'GPIO9',
                 22: 'GPIO25',
                 23: 'GPIO11',
                 24: 'GPIO8',
                 25: 'GND',
                 26: 'GPIO7'
    }
    PINS_REV2 = {1 : '3.3V',
                 2 : '5V',
                 3 : 'GPIO2',
                 4 : '5V',
                 5 : 'GPIO3',
                 6 : 'GND',
                 7 : 'GPIO4',
                 8 : 'GPIO14',
                 9 : 'GND',
                 10: 'GPIO15',
                 11: 'GPIO17',
                 12: 'GPIO18',
                 13: 'GPIO27',
                 14: 'GND',
                 15: 'GPIO22',
                 16: 'GPIO23',
                 17: '3.3V',
                 18: 'GPIO24',
                 19: 'GPIO10',
                 20: 'GND',
                 21: 'GPIO9',
                 22: 'GPIO25',
                 23: 'GPIO11',
                 24: 'GPIO8',
                 25: 'GND',
                 26: 'GPIO7'
    }
    PINS_REV3 = {1: '3.3V',
                 2: '5V',
                 3: 'GPIO2',
                 4: '5V',
                 5: 'GPIO3',
                 6: 'GND',
                 7: 'GPIO4',
                 8: 'GPIO14',
                 9: 'GND',
                 10: 'GPIO15',
                 11: 'GPIO17',
                 12: 'GPIO18',
                 13: 'GPIO27',
                 14: 'GND',
                 15: 'GPIO22',
                 16: 'GPIO23',
                 17: '3.3V',
                 18: 'GPIO24',
                 19: 'GPIO10',
                 20: 'GND',
                 21: 'GPIO9',
                 22: 'GPIO25',
                 23: 'GPIO11',
                 24: 'GPIO8',
                 25: 'GND',
                 26: 'GPIO7',
                 27: 'DNC',
                 28: 'DNC',
                 29: 'GPIO5',
                 30: 'GND',
                 31: 'GPIO6',
                 32: 'GPIO12',
                 33: 'GPIO13',
                 34: 'GND',
                 35: 'GPIO19',
                 36: 'GPIO16',
                 37: 'GPIO26',
                 38: 'GPIO20',
                 39: 'GND',
                 40: 'GPIO21'
    }

    MODE_INPUT = 'input'
    MODE_OUTPUT = 'output'
    MODE_RESERVED = 'reserved'

    INPUT_DROP_THRESHOLD = 0.150 #in ms

    USAGE_ONEWIRE = 'onewire'
    USAGE_LIRC = 'lirc'

    def __init__(self, bus, debug_enabled):
        """
        Constructor

        Params:
            bus: message bus instance
            debug_enabled: debug status
        """
        RaspIotModule.__init__(self, bus, debug_enabled)

        #members
        self.__input_watchers = []

        #configure raspberry pi
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)

    def _start(self):
        """
        Start module
        """
        #configure gpios
        devices = self.get_module_devices()
        for uuid in devices:
            self.__configure_gpio(devices[uuid])

    def _stop(self):
        """
        Stop module
        """
        #stop input watchers
        for w in self.__input_watchers:
            w.stop()

        #cleanup gpios
        GPIO.cleanup()

    def __configure_gpio(self, device):
        """
        Configure GPIO (internal use)

        Params:
            device: device object
        
        Returns:
            bool: True if gpio is configured False otherwise
        """
        self.logger.debug('configuregpio: device=%s' % (device))

        #check if gpio is not reserved
        if device['mode']==self.MODE_RESERVED:
            self.logger.debug('Reserved gpio is not configured')
            return True

        try:
            #get gpio pin
            if device['mode']==self.MODE_OUTPUT:
                self.logger.debug('Configure gpio %s pin %d as OUTPUT' % (device['gpio'], device['pin']))
                #configure it
                if device['on']:
                    initial = GPIO.LOW
                    event = 'gpios.gpio.on'
                else:
                    initial = GPIO.HIGH
                    event = 'gpios.gpio.off'
                self.logger.debug('event=%s initial=%s' % (str(event), str(initial)))
                GPIO.setup(device['pin'], GPIO.OUT, initial=initial)

                #and broadcast gpio status at startup
                self.logger.debug('broadcast event %s for gpio %s' % (event, device['gpio']))
                self.send_event(event, {'gpio':'gpio', 'init':True}, device['uuid'])

            elif device['mode']==self.MODE_INPUT:
                if not device['reverted']:
                    self.logger.debug('Configure gpio %s (pin %s) as INPUT' % (device['gpio'], device['pin']))
                else:
                    self.logger.debug('Configure gpio %s (pin %s) as INPUT reverted' % (device['gpio'], device['pin']))

                #configure it
                GPIO.setup(device['pin'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

                #and launch input watcher
                if not device['reverted']:
                    w = GpioInputWatcher(device['pin'], device['uuid'], self.__input_on_callback, self.__input_off_callback, GPIO.LOW)
                else:
                    w = GpioInputWatcher(device['pin'], device['uuid'], self.__input_on_callback, self.__input_off_callback, GPIO.HIGH)
                self.__input_watchers.append(w)
                w.start()

            return True

        except:
            self.logger.exception('Exception during GPIO configuration:')
            return False

    def __input_on_callback(self, uuid):
        """
        Callback when input is turned on (internal use)

        Params: 
            uuid (string): device uuid
        """
        self.logger.debug('on_callback for gpio %s triggered' % uuid)
        device = self._get_device(uuid)
        if device is None:
            raise Exception('Device %s not found' % uuid)

        #broadcast event
        self.send_event('gpios.gpio.on', {'gpio':device['gpio'], 'init':False}, uuid)

    def __input_off_callback(self, uuid, duration):
        """
        Callback when input is turned off

        Params: 
            uuid (string): device uuid
            duration (float): trigger duration
        """
        self.logger.debug('off_callback for gpio %s triggered' % uuid)
        device = self._get_device(uuid)
        if device is None:
            raise Exception('Device %s not found' % uuid)

        #broadcast event
        self.send_event('gpios.gpio.off', {'gpio':device['gpio'], 'init':False, 'duration':duration}, uuid)

    def get_module_config(self):
        """
        Return module full config
        """
        config = {}

        #merge available gpios with assigned ones
        gpios = {}
        all_gpios = self.get_raspi_gpios()
        devices = self.get_module_devices()
        for gpio in all_gpios:
            #get gpio assigned infos
            assigned = False
            owner = None
            for uuid in devices:
                if devices[uuid]['gpio']==gpio:
                    assigned = True
                    owner = devices[uuid]['owner']
                    break

            #add new entry
            gpios[gpio] = {
                'gpio': gpio,
                'pin': all_gpios[gpio],
                'assigned': assigned,
                'owner': owner
            }
        config['gpios'] = gpios

        return config

    def get_pins_description(self):
        """
        Return pins description

        Results:
            dict: dict of pins 
                {
                    <pin number (int)>:<gpio name|5v|3.3v|gnd|dnc(string)>
                }
        """
        rev = GPIO.RPI_INFO['P1_REVISION']

        if rev==1:
            return self.PINS_REV1
        elif rev==2:
            return self.PINS_REV2
        elif rev==3:
            return self.PINS_REV3

        return {}

    def get_assigned_gpios(self):
        """
        Return assigned gpios

        Returns:
            list: list of gpios
        """
        devices = self.get_module_devices()
        gpios = []
        for uuid in devices:
            gpios.append(devices[uuid]['gpio'])
        
        return gpios

    def get_raspi_gpios(self):
        """
        Return available GPIO pins according to board revision

        Returns:
            dict: dict of gpios 
                {
                    <gpio name>, <pin number>
                }
        """
        rev = GPIO.RPI_INFO['P1_REVISION']

        if rev==1:
            return self.GPIOS_REV1
        if rev==2:
            return self.GPIOS_REV2
        elif rev==3:
            gpios = self.GPIOS_REV2.copy()
            gpios.update(self.GPIOS_REV3)
            return gpios

        return {}

    def get_pins_number(self):
        """
        Return pins number according to board revision
        
        Returns:
            int: pins number
        """
        rev = GPIO.RPI_INFO['P1_REVISION']

        if rev==1 or rev==2:
            return 26
        elif rev==3:
            return 40

        return 0

    def reserve_gpio(self, name, gpio, usage, command_sender):
        """
        Reserve a gpio used to configure raspberry pi (ie onewire, lirc...)
        This action only flag this gpio as reserved to avoid using it again

        Params:
            name: name of gpio
            gpio: gpio value
            usage: gpio usage (must be a known value 'onewire', ?)
            command_sender: command request sender (used to set gpio in readonly mode)

        Returns:
            dict: Created gpio device

        Raises:
            CommandError, MissingParameter, InvalidParameter
        """
        #fix command_sender: rpcserver is the default gpio entry point
        if command_sender=='rpcserver':
            command_sender = 'gpios'

        #search for gpio device
        found_gpio = self._search_device('gpio', gpio)

        #check values
        if not gpio:
            raise MissingParameter('Gpio parameter is missing')
        elif found_gpio is not None and found_gpio['mode']!=usage:
            raise InvalidParameter('Gpio is already reserved for %s usage' % found_gpio['mode'])
        elif found_gpio is not None and found_gpio['mode']==usage:
            return found_gpio
        elif not name:
            raise MissingParameter('Name parameter is missing')
        elif self._search_device('name', name) is not None:
            raise InvalidParameter('Name "%s" already used' % name)
        elif gpio not in self.get_raspi_gpios().keys():
            raise InvalidParameter('Gpio does not exist for this raspberry pi')
        elif usage not in [self.USAGE_ONEWIRE]:
            raise InvalidParameter('Usage is invalid')
        else:
            #gpio is valid, prepare new entry
            data = {
                'name': name,
                'mode': usage,
                'pin': self.get_raspi_gpios()[gpio],
                'gpio': gpio,
                'keep': False,
                'on': False,
                'reverted': False,
                'owner': command_sender,
                'type': 'gpio',
                'subtype': self.MODE_RESERVED
            }

            #add device
            self.logger.debug("data=%s" % data)
            device = self._add_device(data)
            if device is None:
                raise CommandError('Unable to add device')
    
            return device

    def is_reserved_gpio(self, uuid):
        """
        Return True if gpio is reserved

        Params:
            uuid (string): device uuid

        Returns:
            bool: True if gpio is reserved, False otherwise
        """
        device = self._get_device(uuid)
        if device is None:
            raise CommandError('Device %s not found' % uuid)

        self.logger.debug('is_reserved_gpio: %s' % device)
        if device['subtype']==self.MODE_RESERVED:
            return True

        return False

    def add_gpio(self, name, gpio, mode, keep, reverted, command_sender):
        """
        Add new gpio

        Params:
            name: name of gpio
            gpio: gpio value
            mode: mode (input or output)
            keep: keep state when restarting
            reverted: if true on callback will be triggered on gpio low level instead of high level
            command_sender: command request sender (used to set gpio in readonly mode)

        Returns:
            dict: created gpio device

        Raises:
            CommandError, MissingParameter, InvalidParameter
        """
        #fix command_sender: rpcserver is the default gpio entry point
        if command_sender=='rpcserver':
            command_sender = 'gpios'

        #check values
        if not gpio:
            raise MissingParameter('Gpio parameter is missing')
        elif not name:
            raise MissingParameter('Name parameter is missing')
        elif not mode:
            raise MissingParameter('Mode parameter is missing')
        elif keep is None:
            raise MissingParameter('Keep parameter is missing')
        elif self._search_device('name', name) is not None:
            raise InvalidParameter('Name "%s" already used' % name)
        elif gpio not in self.get_raspi_gpios().keys():
            raise InvalidParameter('Gpio does not exist for this raspberry pi')
        elif mode not in (self.MODE_INPUT, self.MODE_OUTPUT):
            raise InvalidParameter('Mode "%s" is invalid' % mode)
        elif self._search_device('gpio', gpio) is not None:
            raise InvalidParameter('Gpio "%s" is already configured' % gpio)
        else:
            #gpio is valid, prepare new entry
            data = {
                'name': name,
                'mode': mode,
                'pin': self.get_raspi_gpios()[gpio],
                'gpio': gpio,
                'keep': keep,
                'on': False,
                'reverted': reverted,
                'owner': command_sender,
                'type': 'gpio',
                'subtype': mode
            }

            #add device
            self.logger.debug("data=%s" % data)
            device = self._add_device(data)
            if device is None:
                raise CommandError('Unable to add device')
    
            #configure it
            self.__configure_gpio(device)

            return device

    def delete_gpio(self, uuid, command_sender):
        """
        Delete gpio

        Params:
            uuid: device identifier
            command_sender (string): command sender

        Returns:
            bool: True if device was deleted, False otherwise

        Raises:
            CommandError, MissingParameter, Unauthorized, InvalidParameter
        """
        #fix command_sender: rpcserver is the default gpio entry point
        if command_sender=='rpcserver':
            command_sender = 'gpios'

        #check values
        device = self._get_device(uuid)
        if not uuid:
            raise MissingParameter('Uuid parameter is missing')
        elif device is None:
            raise InvalidParameter('Device does not exist')
        elif device['owner']!=command_sender:
            raise Unauthorized('Device can only be deleted by module that created it')
        else:
            #device is valid, remove entry
            if not self._delete_device(uuid):
                raise CommandError('Failed to delete device')

            return True

        return False

    def update_gpio(self, uuid, name, keep, reverted, command_sender):
        """
        Update gpio

        Params:
            uuid (string): device identifier
            name (string): gpio name
            keep (bool): keep status flag
            reverted (bool): reverted flag
            command_sender (string): command sender

        Returns:
            bool: True if update was successfull, False otherwise

        Raises:
            CommandError, MissingParameter, Unauthorized, InvalidParameter
        """
        #fix command_sender: rpcserver is the default gpio entry point
        if command_sender=='rpcserver':
            command_sender = 'gpios'

        #check values
        device = self._get_device(uuid)
        if not uuid:
            raise MissingParameter('Uuid parameter is missing')
        elif device is None:
            raise InvalidParameter('Device does not exist')
        elif device['owner']!=command_sender:
            raise Unauthorized('Device can only be deleted by module that created it')
        else:
            #device is valid, update entry
            device['name'] = name
            device['keep'] = keep
            device['reverted'] = reverted
            if self._update_device(uuid, device)==None:
                raise CommandError('Unable to update device')

            return True

        return False

    def turn_on(self, uuid):
        """
        Turn on specified device

        Params:
            uuid (string): device identifier

        Returns:
            bool: True if command executed successfully
        """
        #check values
        device = self._get_device(uuid)
        if device is None:
            raise CommandError('Device not found')
        if device['mode']!=self.MODE_OUTPUT:
            raise CommandError('Gpio %s configured as %s cannot be turned on' % (device['uuid'], device['mode']))

        #turn on relay
        self.logger.debug('Turn on GPIO %s' % device['gpio'])
        GPIO.output(device['pin'], GPIO.LOW)

        #save current state
        device['on'] = True
        if device['keep']:
            self._update_device(uuid, device)

        #broadcast event
        self.send_event('gpios.gpio.on', {'gpio':device['gpio'], 'init':False}, uuid)

        return True

    def turn_off(self, uuid):
        """
        Turn off specified device

        Params:
            uuid (string): device identifier

        Returns:
            bool: True if command executed successfully

        Raises:
            CommandError
        """
        device = self._get_device(uuid)
        if device is None:
            raise CommandError('Device not found')
        if device['mode']!=self.MODE_OUTPUT:
            raise CommandError('Gpio %s configured as %s cannot be turned off' % (device['uuid'], device['mode']))
                
        #turn off relay
        self.logger.debug('Turn off GPIO %s' % device['gpio'])
        GPIO.output(device['pin'], GPIO.HIGH)

        #save current state
        device['on'] = False
        if device['keep']:
            self._update_device(uuid, device)

        #broadcast event
        self.send_event('gpios.gpio.off', {'gpio':device['gpio'], 'init':False}, uuid)

        return True

    def is_on(self, uuid):
        """
        Return gpio status (on or off)

        Params:
            uuid (string): device identifier

        Returns:
            bool: True if device is on, False if device is off

        Raises:
            CommandError
        """
        #check values
        device = self._get_device(uuid)
        if device is None:
            raise CommandError('Device not found')
        if device['mode']==self.MODE_RESERVED:
            raise CommandError('Gpio %s configured as %s cannot be checked' % (device['uuid'], device['mode']))

        return device['on']

    def reset_gpios(self):
        """
        Reset all gpios turning them off
        """
        devices = self.get_module_devices()
        for uuid in devices:
            if devices[uuid]['mode']==Gpios.MODE_OUTPUT:
                self.turn_off(uuid)


if __name__ == '__main__':
    #testu
    o = Gpios()
    print o.get_raspi_gpios()
