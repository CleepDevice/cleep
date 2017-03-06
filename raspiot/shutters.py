#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from bus import MessageRequest, MessageResponse, MissingParameter, InvalidParameter
from raspiot import RaspIot, CommandError
from threading import Timer

__all__ = ['Shutters']

class Shutters(RaspIot):
    MODULE_CONFIG_FILE = 'shutters.conf'
    MODULE_DEPS = ['gpios']

    STATUS_OPENED = 'opened'
    STATUS_CLOSED = 'closed'
    STATUS_PARTIAL = 'partial'
    STATUS_OPENING = 'opening'
    STATUS_CLOSING = 'closing'

    def __init__(self, bus):
        #init
        RaspIot.__init__(self, bus)

        #internal timers
        self.__timers = {}
        self.raspi_gpios = {}

    def _start(self):
        """
        Start module
        """
        #raspi gpios
        self.raspi_gpios = self.get_raspi_gpios()

        #reset gpios and shutters
        self.reset()

    def event_received(self, event):
        """
        Event received from bus
        """
        #drop startup events
        if event['startup']:
            self.logger.debug('Drop startup event')
            return

        #process received event
        if event['event']=='gpios.gpio.off':
            #drop gpio init
            if event['params']['init']:
                self.logger.debug('Drop gpio init event')
                return

            #gpio turned off, get gpio
            gpio = event['params']['gpio']

            #search drape and execute action
            for shutter in self._config:
                if self._config[shutter]['switch_open']==gpio:
                    self.__execute_action(self._config[shutter], True)
                    break
                elif self._config[shutter]['switch_close']==gpio:
                    self.__execute_action(self._config[shutter], False)
                    break

    def reset(self):
        """
        Reset all that need to be resetted:
        - gpios are resetted
        - shutters that are opening/closing are set to opened/closed
        """
        #reset gpios
        req = MessageRequest()
        req.to = 'gpios'
        req.command = 'reset_gpios'
        resp = self.push(req)
        if resp['error']:
            self.logger.error(resp['message'])
            return

        #and reset shutter
        config = self.get_devices()
        for shutter in config:
            if config[shutter]['status']==Shutters.STATUS_OPENING:
                self.change_status(shutter, Shutters.STATUS_OPENED)
            if config[shutter]['status']==Shutters.STATUS_CLOSING:
                self.change_status(shutter, Shutters.STATUS_CLOSED)

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

    def get_devices(self):
        """
        Return full config
        """
        return self._config

    def __stop_action(self, shutter):
        """
        Stop specified shutter
        """
        #first of all cancel timer if necessary
        if self.__timers.has_key(shutter['name']):
            self.logger.debug('Cancel timer of shutter "%s"' % shutter['name'])
            self.__timers[shutter['name']].cancel()
            del self.__timers[shutter['name']]

        #then get gpio
        if shutter['status']==Shutters.STATUS_OPENING:
            gpio = shutter['shutter_open']
        else:
            gpio = shutter['shutter_close']
        self.logger.debug('stop shutter: gpio=%s' % str(gpio))

        #and turn off gpio
        req = MessageRequest()
        req.to = 'gpios'
        req.command = 'turn_off'
        req.params = {'gpio':gpio}
        resp = self.push(req)
        if resp['error']:
            raise CommandError(resp['message'])
        
        #change status
        self.change_status(shutter['name'], Shutters.STATUS_PARTIAL)

    def __open_action(self, shutter):
        """
        Open specified shutter
        """
        #turn on gpio
        gpio = shutter['shutter_open']
        req = MessageRequest()
        req.to = 'gpios'
        req.command = 'turn_on'
        req.params = {'gpio':gpio}
        resp = self.push(req)
        if resp['error']:
            raise CommandError(resp['message'])

        #change status
        self.change_status(shutter['name'], Shutters.STATUS_OPENING)
    
        #launch turn off timer
        self.logger.debug('Launch timer with duration=%s' % (str(shutter['delay'])))
        self.__timers[shutter['name']] = Timer(float(shutter['delay']), self.__end_of_timer, [shutter['name'], gpio, Shutters.STATUS_OPENED])
        self.__timers[shutter['name']].start()

    def __close_action(self, shutter):
        """
        Close specified shutter
        """
        #turn on gpio
        gpio = shutter['shutter_close']
        req = MessageRequest()
        req.to = 'gpios'
        req.command = 'turn_on'
        req.params = {'gpio':gpio}
        resp = self.push(req)
        if resp['error']:
            raise CommandError(resp['message'])

        #change status
        self.change_status(shutter['name'], Shutters.STATUS_CLOSING)
        
        #launch turn off timer
        self.logger.debug('Launch timer with duration=%s' % (str(shutter['delay'])))
        self.__timers[shutter['name']] = Timer(float(shutter['delay']), self.__end_of_timer, [shutter['name'], gpio, Shutters.STATUS_CLOSED])
        self.__timers[shutter['name']].start()

    def __execute_action(self, shutter, open_action):
        """
        Execute action according to parameters
        Centralize here all process to avoid turning off and on at the same time
        @param shutter: concerned shutter
        @param open_shutter: True if action is to open shutter. False if is close action
        """
        if not shutter:
            self.logger.error('__execute_action: shutter is not defined')
            return

        if open_action:
            #open action triggered
            if shutter['status'] in [Shutters.STATUS_OPENING, Shutters.STATUS_CLOSING]:
                #shutter is in opening or closing state, stop it
                self.__stop_action(shutter)

            elif shutter['status'] in [Shutters.STATUS_CLOSED, Shutters.STATUS_PARTIAL]:
                #shutter is not completely opened or closed, open it
                self.__open_action(shutter)
            else:
                #shutter is already opened, do nothing
                self.logger.debug('Shutter %s is already opened' % shutter['name'])

        else:
            #close action triggered
            if shutter['status'] in [Shutters.STATUS_OPENING, Shutters.STATUS_CLOSING]:
                #shutter is in opening or closing state, stop it
                self.__stop_action(shutter)

            elif shutter['status'] in [Shutters.STATUS_OPENED, Shutters.STATUS_PARTIAL]:
                #close shutter action
                self.__close_action(shutter)

            else:
                #shutter is already closed
                self.logger.debug('Shutter %s is already closed' % shutter['name'])
        

    def add_shutter(self, name, shutter_open, shutter_close, delay, switch_open, switch_close):
        #get used gpios
        used_gpios = self.get_used_gpios()

        #check values
        if not name:
            raise MissingParameter('Name parameter is missing')
        elif not shutter_open:
            raise MissingParameter('Open shutter parameter is missing')
        elif not shutter_close:
            raise MissingParameter('Close shutter parameter is missing')
        elif not switch_open:
            raise MissingParameter('Open switch parameter is missing')
        elif not switch_close:
            raise MissingParameter('Close switch parameter is missing')
        elif not delay:
            raise MissingParameter('Delay parameter is missing')
        elif shutter_open==shutter_close or shutter_open==switch_open or shutter_open==switch_close or shutter_close==switch_open or shutter_close==switch_close or switch_open==switch_close:
            raise InvalidParameter('Gpios must all be differents')
        elif shutter_open in used_gpios:
            raise InvalidParameter('Open shutter is already used')
        elif shutter_close in used_gpios:
            raise InvalidParameter('Close shutter is already used')
        elif switch_open in used_gpios:
            raise InvalidParameter('Open switch is already used')
        elif switch_close in used_gpios:
            raise InvalidParameter('Close switch is already used')
        elif name in self.get_devices():
            raise InvalidParameter('Shutter name is already used')
        elif shutter_open not in self.raspi_gpios:
            raise InvalidParameter('Open shutter does not exist for this raspberry pi')
        elif shutter_close not in self.raspi_gpios:
            raise InvalidParameter('Close shutter does not exist for this raspberry pi')
        elif switch_open not in self.raspi_gpios:
            raise InvalidParameter('Open switch does not exist for this raspberry pi')
        elif switch_close not in self.raspi_gpios:
            raise InvalidParameter('Close switch does not exist for this raspberry pi')
        else:
            #configure open shutter
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'add_gpio'
            req.params = {'name':name+'_shutteropen', 'gpio':shutter_open, 'mode':'out', 'keep':True}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])
                
            #configure close shutter
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'add_gpio'
            req.params = {'name':name+'_shutterclose', 'gpio':shutter_close, 'mode':'out', 'keep':True}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])

            #configure open switch
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'add_gpio'
            req.params = {'name':name+'_switchopen', 'gpio':switch_open, 'mode':'in', 'keep':False}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])

            #configure close switch
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'add_gpio'
            req.params = {'name':name+'_switchclose', 'gpio':switch_close, 'mode':'in', 'keep':False}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])

            #shutter is valid, prepare new entry
            self.logger.debug('name=%s delay=%s shutter_open=%s shutter_close=%s switch_open=%s switch_close=%s' % (str(name), str(delay), str(shutter_open), str(shutter_close), str(switch_open), str(switch_close)))
            config = self.get_devices()
            config[name] = {'name':name, 'delay':delay, 'shutter_open':shutter_open, 'shutter_close':shutter_close, 'switch_open':switch_open, 'switch_close':switch_close, 'status':Shutters.STATUS_OPENED}
            self._save_config(config)

    def delete_shutter(self, name):
        """
        Del specified shutter
        """
        config = self.get_devices()
        if not name:
            raise MissingParameter('"name" parameter is missing')
        elif name not in config:
            raise InvalidParameter('Shutter "%s" doesn\'t exist' % name)
        else:
            #unconfigure open shutter
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'delete_gpio'
            req.params = {'gpio':config[name]['shutter_open']}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])

            #unconfigure close shutter
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'delete_gpio'
            req.params = {'gpio':config[name]['shutter_close']}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])

            #unconfigure open switch
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'delete_gpio'
            req.params = {'gpio':config[name]['switch_open']}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])

            #unconfigure close switch
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'delete_gpio'
            req.params = {'gpio':config[name]['switch_close']}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])

            #shutter is valid, remove it
            del config[name]
            self._save_config(config)

    def change_status(self, shutter_name, status):
        """
        Change shutter status
        """
        self.logger.debug('change_status for shutter "%s" to "%s"' % (str(shutter_name), str(status)))
        config = self.get_devices()
        if not status in [Shutters.STATUS_OPENED, Shutters.STATUS_CLOSED, Shutters.STATUS_PARTIAL, Shutters.STATUS_OPENING, Shutters.STATUS_CLOSING]:
            raise InvalidParameter('Status value is invalid')
        elif shutter_name not in config:
            raise InvalidParameter('Shutter "%s" doesn\'t exist' % str(shutter_name))
        else:
            #save new status
            config[shutter_name]['status'] = status
            self._save_config(config)

            #and broadcast new shutter status
            req = MessageRequest()
            req.event = 'shutters.shutter.%s' % status
            req.params = {'shutter': shutter_name}
            self.push(req)

    def __end_of_timer(self, shutter_name, gpio, new_status):
        """
        Triggered when timer is over
        """
        #turn off specified gpio
        self.logger.debug('end_of_timer for gpio:%s' % gpio)
        req = MessageRequest()
        req.to = 'gpios'
        req.command = 'turn_off'
        req.params = {'gpio':gpio}
        resp = self.push(req)
        if resp['error']:
            raise CommandError(resp['message'])

        #and update status to specified one
        self.change_status(shutter_name, new_status)

    def open_shutter(self, name):
        """
        Open specified shutter
        """
        self.logger.debug('open_shutter %s' % str(name))
        if name not in self._config:
            raise InvalidParameter('Shutter "%s" doesn\'t exist' % name)
        self.__execute_action(self._config[name], True)

    def close_shutter(self, name):
        """
        Close specified shutter
        """
        self.logger.debug('close_shutter %s' % str(name))
        if name not in self._config:
            raise InvalidParameter('Shutter "%s" doesn\'t exist' % name)
        self.__execute_action(self._config[name], False)

    def stop_shutter(self, name):
        """
        Stop specified shutter
        """
        self.logger.debug('stop_shutter %s' % str(name))
        if name not in self._config:
            raise InvalidParameter('Shutter "%s" doesn\'t exist' % name)
        self.__stop_action(self._config[name])

if __name__ == '__main__':
    #testu
    o = Shutters()
    print o.get_raspi_gpios()
