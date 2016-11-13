#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from bus import MessageRequest, MessageResponse, MissingParameter, InvalidParameter
from raspiot import RaspIot, CommandError
from threading import Timer

__all__ = ['Drapes']

#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG);

#Drapes module
class Drapes(RaspIot):
    CONFIG_FILE = 'drapes.conf'

    STATUS_OPENED = 'opened'
    STATUS_CLOSED = 'closed'
    STATUS_PARTIAL = 'partial'
    STATUS_OPENING = 'opening'
    STATUS_CLOSING = 'closing'

    def __init__(self, bus):
        RaspIot.__init__(self, bus)
        #internal timers
        self.__timers = {}
        #raspi gpios
        self.raspi_gpios = self.get_raspi_gpios()

        #reset all stuff
        self.reset()

    def event_received(self, event):
        """
        Event received from bus
        """
        logger.debug(' *** event received: %s' % str(event))
        found = False

        #drop startup events
        if event['startup']:
            logger.debug('Drop startup event')
            return

        #process received event
        if event['event']=='event.gpio.off':
            #drop gpio init
            if event['params']['init']:
                logger.debug('Drop gpio init event')
                return

            #gpio turned off, get gpio
            gpio = event['params']['gpio']

            #search frape and execute action
            for drape in self._config:
                if self._config[drape]['switch_open']==gpio:
                    self.__execute_action(self._config[drape], True)
                    break
                elif self._config[drape]['switch_close']==gpio:
                    self.__execute_action(self._config[drape], False)
                    break

    def reset(self):
        """
        Reset all stuff
        """
        #reset gpios
        req = MessageRequest()
        req.to = 'gpios'
        req.command = 'reset_gpios'
        resp = self.push(req)
        if resp['error']:
            logger.error(resp['message'])
            return

        #and reset drapes
        config = self.get_devices()
        for drape in config:
            if config[drape]['status']==Drapes.STATUS_OPENING:
                self.change_status(drape, Drapes.STATUS_OPENED)
            if config[drape]['status']==Drapes.STATUS_CLOSING:
                self.change_status(drape, Drapes.STATUS_CLOSED)

    def get_raspi_gpios(self):
        """
        Get raspi gpios
        """
        req = MessageRequest()
        req.to = 'gpios'
        req.command = 'get_raspi_gpios'
        resp = self.push(req)
        if resp['error']:
            logger.error(resp['message'])
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
            logger.error(resp['message'])
            return {}
        else:
            return resp['data']

    def get_devices(self):
        """
        Return full config (drapes+switches)
        """
        return self._config

    def __stop_action(self, drape):
        """
        Stop specified drape
        """
        #first of all cancel timer if necessary
        if self.__timers.has_key(drape['name']):
            logger.debug('Cancel timer of drape "%s"' % drape['name'])
            self.__timers[drape['name']].cancel()
            del self.__timers[drape['name']]

        #then get gpio
        if drape['status']==Drapes.STATUS_OPENING:
            gpio = drape['drape_open']
        else:
            gpio = drape['drape_close']
        logger.debug('stop drape: gpio=%s' % str(gpio))

        #and turn off gpio
        req = MessageRequest()
        req.to = 'gpios'
        req.command = 'turn_off'
        req.params = {'gpio':gpio}
        resp = self.push(req)
        if resp['error']:
            raise CommandError(resp['message'])
        
        #change status
        self.change_status(drape['name'], Drapes.STATUS_PARTIAL)

    def __open_action(self, drape):
        """
        Open specified drape
        """
        #turn on gpio
        gpio = drape['drape_open']
        req = MessageRequest()
        req.to = 'gpios'
        req.command = 'turn_on'
        req.params = {'gpio':gpio}
        resp = self.push(req)
        if resp['error']:
            raise CommandError(resp['message'])

        #change status
        self.change_status(drape['name'], Drapes.STATUS_OPENING)
    
        #launch turn off timer
        logger.debug('Launch timer with duration=%s' % (str(drape['delay'])))
        self.__timers[drape['name']] = Timer(float(drape['delay']), self.__end_of_timer, [drape['name'], gpio, Drapes.STATUS_OPENED])
        self.__timers[drape['name']].start()

    def __close_action(self, drape):
        """
        Close specified drape
        """
        #turn on gpio
        gpio = drape['drape_close']
        req = MessageRequest()
        req.to = 'gpios'
        req.command = 'turn_on'
        req.params = {'gpio':gpio}
        resp = self.push(req)
        if resp['error']:
            raise CommandError(resp['message'])

        #change status
        self.change_status(drape['name'], Drapes.STATUS_CLOSING)
        
        #launch turn off timer
        logger.debug('Launch timer with duration=%s' % (str(drape['delay'])))
        self.__timers[drape['name']] = Timer(float(drape['delay']), self.__end_of_timer, [drape['name'], gpio, Drapes.STATUS_CLOSED])
        self.__timers[drape['name']].start()

    def __execute_action(self, drape, open_action):
        """
        Execute action according to parameters
        Centralize here all process to avoid turning off and on at the same time
        @param drape: concerned drape 
        @param open_drape: True if action is to open drape. False if is close action
        """
        if not drape:
            logger.error('__execute_action: Drape is not defined')
            return

        if open_action:
            #open action triggered
            if drape['status'] in [Drapes.STATUS_OPENING, Drapes.STATUS_CLOSING]:
                #drape is in opening or closing state, stop it
                #self.stop_drape(drape)
                self.__stop_action(drape)

            elif drape['status'] in [Drapes.STATUS_CLOSED, Drapes.STATUS_PARTIAL]:
                #drape is not completely opened or closed, open it
                #self.open_drape(drape)
                self.__open_action(drape)
            else:
                #drape is already opened, do nothing
                logger.debug('Drape %s is already opened' % drape['name'])

        else:
            #close action triggered
            if drape['status'] in [Drapes.STATUS_OPENING, Drapes.STATUS_CLOSING]:
                #drape is in opening or closing state, stop it
                #self.stop_drape(drape)
                self.__stop_action(drape)

            elif drape['status'] in [Drapes.STATUS_OPENED, Drapes.STATUS_PARTIAL]:
                #close drape action
                #self.close_drape(drape)
                self.__close_action(drape)

            else:
                #drape is already closed
                logger.debug('Drape %s is already closed' % drape['name'])
        

    def add_drape(self, name, drape_open, drape_close, delay, switch_open, switch_close):
        #get used gpios
        used_gpios = self.get_used_gpios()

        #check values
        if not name:
            raise MissingParameter('Name parameter is missing')
        elif not drape_open:
            raise MissingParameter('Open drape parameter is missing')
        elif not drape_close:
            raise MissingParameter('Close drape parameter is missing')
        elif not switch_open:
            raise MissingParameter('Open switch parameter is missing')
        elif not switch_close:
            raise MissingParameter('Close switch parameter is missing')
        elif not delay:
            raise MissingParameter('Delay parameter is missing')
        elif drape_open==drape_close or drape_open==switch_open or drape_open==switch_close or drape_close==switch_open or drape_close==switch_close or switch_open==switch_close:
            raise InvalidParameter('Gpios must all be differents')
        elif drape_open in used_gpios:
            raise InvalidParameter('Open drape is already used')
        elif drape_close in used_gpios:
            raise InvalidParameter('Close drape is already used')
        elif switch_open in used_gpios:
            raise InvalidParameter('Open switch is already used')
        elif switch_close in used_gpios:
            raise InvalidParameter('Close switch is already used')
        elif name in self.get_devices():
            raise InvalidParameter('Drape name is already used')
        elif drape_open not in self.raspi_gpios:
            raise InvalidParameter('Open drape does not exist for this raspberry pi')
        elif drape_close not in self.raspi_gpios:
            raise InvalidParameter('Close drape does not exist for this raspberry pi')
        elif switch_open not in self.raspi_gpios:
            raise InvalidParameter('Open switch does not exist for this raspberry pi')
        elif switch_close not in self.raspi_gpios:
            raise InvalidParameter('Close switch does not exist for this raspberry pi')
        else:
            #configure open drape
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'add_gpio'
            req.params = {'name':name+'_drapeopen', 'gpio':drape_open, 'mode':'out', 'keep':True}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])
                
            #configure close drape
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'add_gpio'
            req.params = {'name':name+'_drapeclose', 'gpio':drape_close, 'mode':'out', 'keep':True}
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

            #drapes is valid, prepare new entry
            drapes = self.get_devices()
            logger.debug('drapes = %s' % str(drapes))
            logger.debug('name=%s delay=%s drape_open=%s drape_close=%s switch_open=%s switch_close=%s' % (str(name), str(delay), str(drape_open), str(drape_close), str(switch_open), str(switch_close)))
            config = self.get_devices()
            config[name] = {'name':name, 'delay':delay, 'drape_open':drape_open, 'drape_close':drape_close, 'switch_open':switch_open, 'switch_close':switch_close, 'status':Drapes.STATUS_OPENED}
            self._save_config(config)

    def del_drape(self, name):
        """
        Del specified drape
        """
        config = self.get_devices()
        if not name:
            raise MissingParameter('"name" parameter is missing')
        elif name not in config:
            raise InvalidParameter('Drape "%s" doesn\'t exist' % name)
        else:
            #unconfigure open drape
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'del_gpio'
            req.params = {'gpio':config[name]['drape_open']}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])

            #unconfigure close drape
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'del_gpio'
            req.params = {'gpio':config[name]['drape_close']}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])

            #unconfigure open switch
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'del_gpio'
            req.params = {'gpio':config[name]['switch_open']}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])

            #unconfigure close switch
            req = MessageRequest()
            req.to = 'gpios'
            req.command = 'del_gpio'
            req.params = {'gpio':config[name]['switch_close']}
            resp = self.push(req)
            if resp['error']:
                raise CommandError(resp['message'])

            #drape is valid, remove it
            del config[name]
            self._save_config(config)

    def change_status(self, drape_name, status):
        """
        Change drape status
        """
        logger.debug('change_status for drape "%s" to "%s"' % (str(drape_name), str(status)))
        config = self.get_devices()
        if not status in [Drapes.STATUS_OPENED, Drapes.STATUS_CLOSED, Drapes.STATUS_PARTIAL, Drapes.STATUS_OPENING, Drapes.STATUS_CLOSING]:
            raise InvalidParameter('Status value is invalid')
        elif drape_name not in config:
            raise InvalidParameter('Drape "%s" doesn\'t exist' % str(drape_name))
        else:
            #save new status
            config[drape_name]['status'] = status
            self._save_config(config)

            #and broadcast new drape status
            req = MessageRequest()
            req.event = 'event.drape.%s' % status
            req.params = {'drape': drape_name}
            self.push(req)

    def __end_of_timer(self, drape_name, gpio, new_status):
        """
        Triggered when timer is over
        """
        #turn off specified gpio
        logger.debug('end_of_timer for gpio:%s' % gpio)
        req = MessageRequest()
        req.to = 'gpios'
        req.command = 'turn_off'
        req.params = {'gpio':gpio}
        resp = self.push(req)
        if resp['error']:
            raise CommandError(resp['message'])

        #and update status to specified one
        self.change_status(drape_name, new_status)

    def open_drape(self, name):
        """
        Open specified drape
        """
        logger.debug('open_drape %s' % str(name))
        if name not in self._config:
            raise InvalidParameter('Drape "%s" doesn\'t exist' % name)
        self.__execute_action(self._config[name], True)

    def close_drape(self, name):
        """
        Close specified drape
        """
        logger.debug('close_drape %s' % str(name))
        if name not in self._config:
            raise InvalidParameter('Drape "%s" doesn\'t exist' % name)
        self.__execute_action(self._config[name], False)

    def stop_drape(self, name):
        """
        Stop specified drape
        """
        logger.debug('stop_drape %s' % str(name))
        if name not in self._config:
            raise InvalidParameter('Drape "%s" doesn\'t exist' % name)
        self.__stop_action(self._config[name])

if __name__ == '__main__':
    #testu
    o = Drapes()
    print o.get_raspi_gpios()
