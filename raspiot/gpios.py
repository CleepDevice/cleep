#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import glob
import uuid as moduuid
import json
from threading import Lock, Thread
import RPi.GPIO as GPIO
import bus
from raspiot import RaspIot
import time

__all__ = ['Gpios']

#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO);

class GpioInputWatcher(Thread):
    """
    Object that watches for changes on specified input pin
    We don't use GPIO lib implemented threaded callback due to a bug when executing a timer within 
    callback function
    This object doesn't configure pin!
    """
    def __init__(self, pin, on_callback, off_callback=None, level=GPIO.LOW, debounce=200):
        Thread.__init__(self)
        self.continu = True
        self.pin = pin
        self.level = level
        self.debounce = debounce
        self.on_callback = on_callback
        self.off_callback = off_callback

    def stop(self):
        """
        Stop process
        """
        self.continu = False

    def run(self):
        last_level = None
        time_on = 0
        try:
            while self.continu:
                level = GPIO.input(self.pin)
                if last_level is None:
                    #first run, nothing to do except init values
                    pass
                elif level!=last_level and level==self.level:
                    logger.debug('input %s on' % str(self.pin))
                    time_on = time.time()
                    self.on_callback(self.pin)
                    time.sleep(self.debounce/1000.0)

                elif level!=last_level:
                    logger.debug('input %s off' % str(self.pin))
                    if self.off_callback:
                        self.off_callback(self.pin, time.time()-time_on)
                    time.sleep(.1)

                else:
                    time.sleep(.1)
                last_level = level
        except:
            logger.debug('Exception in GpioInputWatcher')



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
class Gpios(RaspIot):
    CONFIG_FILE = 'gpios.conf'
    DEPS = []

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
    } #first items are dedicated GPIO ports. Then possible GPIO ports
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

    MODE_IN = 'in'
    MODE_OUT = 'out'

    def __init__(self, bus):
        RaspIot.__init__(self, bus)
        self.__input_watchers = []

        #configure RasPi
        GPIO.setmode(GPIO.BOARD)
        #GPIO.setwarnings(False)
        for gpio in self._config:
            self.__configure_gpio(gpio, self._config[gpio])

    def stop(self):
        RaspIot.stop(self)

        #stop input watchers
        for w in self.__input_watchers:
            w.stop()
        #cleanup gpios
        GPIO.cleanup()

    def __configure_gpio(self, gpio, conf):
        """
        Configure GPIO
        """
        logger.debug('configuregpio: gpio=%s, conf=%s' % (gpio,conf))
        try:
            #get gpio pin
            gpios = self.get_raspi_gpios()
            pin = gpios[gpio]
            if conf['mode']==self.MODE_OUT:
                logger.debug('Configure gpio %s (pin %d) as OUTPUT' % (gpio, pin))
                #configure it
                if conf['on']:
                    initial = GPIO.LOW
                    #GPIO.output(pin, GPIO.LOW)
                    event = 'event.gpio.on'
                else:
                    initial = GPIO.HIGH
                    #GPIO.output(pin, GPIO.HIGH)
                    event = 'event.gpio.off'
                logger.debug('event=%s initial=%s' % (str(event), str(initial)))
                GPIO.setup(pin, GPIO.OUT, initial=initial)

                #and broadcast gpio status at startup
                logger.debug('broadcast event %s for gpio %s' % (event, gpio))
                req = bus.MessageRequest()
                req.event = event
                req.params = {'gpio':gpio, 'init':True}
                self.push(req)

            elif conf['mode']==self.MODE_IN:
                logger.debug('Configure gpio %s (pin %s) as INPUT' % (gpio, pin))
                #configure it
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

                #and launch input watcher
                w = GpioInputWatcher(pin, self.__input_on_callback, self.__input_off_callback)
                self.__input_watchers.append(w)
                w.start()
            return True

        except:
            logger.exception('Exception during GPIO configuration:')
            return False

    def __input_on_callback(self, pin):
        """
        Callback when input is turned on
        """
        logger.debug('on_callback for pin %s triggered' % pin)
        #get triggered gpio
        gpios = self.get_raspi_gpios()
        gpio = None
        for key in gpios:
            if gpios[key]==pin:
                gpio = key
                break

        if gpio==None:
            logger.error('Triggered gpio for pin #%s was not found' % str(pin))
        else:
            #broadcast event
            req = bus.MessageRequest()
            req.event = 'event.gpio.on'
            req.params = {'gpio':gpio, 'init':False}
            logger.debug('broadcast %s' % str(req))
            self.push(req)

    def __input_off_callback(self, pin, duration):
        """
        Callback when input is turned off
        """
        logger.debug('off_callback for pin %s triggered' % pin)
        #get triggered gpio
        gpios = self.get_raspi_gpios()
        gpio = None
        for key in gpios:
            if gpios[key]==pin:
                gpio = key
                break

        if gpio==None:
            logger.error('Triggered gpio for pin #%s was not found' % str(pin))
        else:
            #broadcast event
            req = bus.MessageRequest()
            req.event = 'event.gpio.off'
            req.params = {'gpio':gpio, 'init':False, 'duration':duration}
            logger.debug('broadcast %s' % str(req))
            self.push(req)

    def get_raspi_gpios(self):
        """
        Return available GPIO pins according to board revision
        """
        rev = GPIO.RPI_INFO['P1_REVISION']
        if rev==2:
            #A/B
            return self.GPIOS_REV2
        elif rev==3:
            #A+/B+/B2
            return self.GPIOS_REV3
        return {}

    def get_gpio(self, gpio):
        """
        Return specified configured gpio
        """
        if self._config.has_key(gpio):
            return self._config[gpio]
        else:
            return None

    def get_gpios(self):
        """
        Return configured gpios
        """
        return self._config

    def add_gpio(self, name, gpio, mode, keep):
        """
        Add new gpio
        @param name: name of gpio
        @param gpio: gpio value
        @param mode: mode (input or output)
        @param keep: keep state when restarting
        """
        config = self.get_gpios()

        #check values
        if not gpio:
            raise bus.MissingParameter('"gpio" parameter is missing')
        elif not name:
            raise bus.MissingParameter('"name" parameter is missing')
        elif not mode:
            raise bus.MissingParameter('"mode" parameter is missing')
        elif keep is None:
            raise bus.MissingParameter('"keep" parameter is missing')
        elif name in config:
            raise bus.InvalidParameter('Name "%s" already used' % name)
        elif gpio not in self.get_raspi_gpios().keys():
            raise bus.InvalidParameter('"gpio" does not exist for this raspberry pi')
        elif mode not in (self.MODE_IN, self.MODE_OUT):
            raise bus.InvalidParameter('Mode "%s" is invalid' % mode)
        elif self.get_gpio(gpio) is not None:
            raise bus.InvalidParameter('Gpio "%s" is already configured' % gpio)
        else:
            #gpio is valid, prepare new entry
            config[gpio] = {'name':name, 'mode':mode, 'pin':self.get_raspi_gpios()[gpio], 'keep': keep, 'on': False}

            #save config
            self._save_config(config)
    
            #configure it
            self.__configure_gpio(gpio, config[gpio])
        
    def del_gpio(self, gpio):
        """
        Delete gpio
        """
        #check values
        if not gpio:
            raise bus.MissingParameter('"gpio" parameter is missing')
        elif gpio not in self.get_raspi_gpios().keys():
            raise bus.InvalidParameter('"gpio" doesn\'t exists for this raspberry pi')
        elif self.get_gpio(gpio) is None:
            raise bus.InvalidParameter('Gpio "%s" is not configured yet' % gpio)
        else:
            #gpio is valid, remove entry
            config = self._get_config()
            del config[gpio]
            #save config
            self._save_config(config)

    def turn_on(self, gpio):
        """
        Turn on specified gpio
        """
        logger.debug('turn_on')
        try:
            #check values
            gpios = self.get_raspi_gpios()
            if not gpios.has_key(gpio):
                return 'Specified gpio "%s" not found' % gpio, None
            
            #turn on relay
            logger.debug('turn on GPIO %s' % gpio)
            GPIO.output(gpios[gpio], GPIO.LOW)

            #save current state
            if self._config[gpio]['keep']:
                self._config[gpio]['on'] = True
                self._save_config(self._config)

            #broadcast event
            req = bus.MessageRequest()
            req.event = 'event.gpio.on'
            req.params = {'gpio':gpio, 'init':False}
            self.push(req)

            return True
        except:
            logger.exception('Exception in turn_on:')
            return False

    def turn_off(self, gpio):
        """
        Turn off specified gpio
        """
        logger.debug('turn_off')
        try:
            #check values
            gpios = self.get_raspi_gpios()
            if not gpios.has_key(gpio):
                return 'Specified gpio "%s" not found' % gpio, None
                
            #turn off relay
            logger.debug('turn off GPIO %s' % gpio)
            GPIO.output(gpios[gpio], GPIO.HIGH)

            #save config
            if self._config[gpio]['keep']:
                self._config[gpio]['on'] = False
                self._save_config(self._config)

            #broadcast event
            req = bus.MessageRequest()
            req.event = 'event.gpio.off'
            req.params = {'gpio':gpio, 'init':False}
            self.push(req)

            return True
        except:
            logger.exception('Exception in turn_off:')
            return False

    def is_on(self, gpio):
        """
        Return gpio status (on or off)
        """
        try:
            #check values
            gpios = self.get_raspi_gpios()
            if not gpios.has_key(gpio):
                return 'Specified gpio "%s" not found' % gpio, None

            #return gpio status
            return self._config[gpio]['on']
        except:
            logger.exception('Exception in is_on:')
            return False

    def reset_gpios(self):
        """
        Reset all gpios setting turning them off
        """
        config = self.get_gpios()
        for gpio in config:
            if config[gpio]['mode']==Gpios.MODE_OUT:
                self.turn_off(gpio)


if __name__ == '__main__':
    #testu
    o = Gpios()
    print o.get_raspi_gpios()
