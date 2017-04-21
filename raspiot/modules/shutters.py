#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.utils import MissingParameter, InvalidParameter, CommandError, CommandInfo
from raspiot.raspiot import RaspIotMod
from threading import Timer
import time

__all__ = ['Shutters']


class Shutters(RaspIotMod):

    MODULE_CONFIG_FILE = 'shutters.conf'
    MODULE_DEPS = ['gpios']
    MODULE_DESCRIPTION = 'Controls your roller shutters'
    MODULE_LOCKED = False

    STATUS_OPENED = 'opened'
    STATUS_CLOSED = 'closed'
    STATUS_PARTIAL = 'partial'
    STATUS_OPENING = 'opening'
    STATUS_CLOSING = 'closing'

    def __init__(self, bus, debug_enabled):
        """
        Constructor
        @param bus: bus instance
        @param debug_enabled: debug status
        """
        #init
        RaspIotMod.__init__(self, bus, debug_enabled)

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

    def get_module_config(self):
        """
        Get full module configuration
        """
        config = {}
        config['raspi_gpios'] = self.get_raspi_gpios()
        return config

    def event_received(self, event):
        """
        Event received from bus
        """
        self.logger.debug('Event received %s' % event)
        #drop startup events
        if event['startup']:
            self.logger.debug('Drop startup event')
            return

        #process received event
        if event['event']=='gpios.gpio.off':
            #drop gpio init event
            if event['params']['init']:
                self.logger.debug('Drop gpio init event')
                return

            #gpio turned off, get gpio device
            gpio_uuid = event['uuid']
            self.logger.debug('gpio_uuid=%s' % event['uuid'])

            #search shutter and execute action
            shutters = self._get_devices()
            self.logger.debug('shutters=%s' % shutters)
            for uuid in shutters:

                #execute action according to triggered gpio
                self.logger.debug('level=%s' % str(shutters[uuid]['level']))
                if shutters[uuid]['shutter_open_uuid']==gpio_uuid and shutters[uuid]['level'] is not None:
                    self.logger.debug('Shutter just opened after level_shutter action. Close it now')
                    #reset shutter level value
                    level = shutters[uuid]['level']
                    shutters[uuid]['level'] = None
                    self._update_device(uuid, shutters[uuid])
                    self.__execute_action(shutters[uuid], False, level)
                    break

                if shutters[uuid]['switch_open_uuid']==gpio_uuid:
                    self.logger.debug('Found switch_open_uuid')
                    self.__execute_action(shutters[uuid], True)
                    break

                elif shutters[uuid]['switch_close_uuid']==gpio_uuid:
                    self.logger.debug('Found switch_close_uuid')
                    self.__execute_action(shutters[uuid], False)
                    break

            self.logger.debug('Done')

    def reset(self):
        """
        Reset all that need to be resetted:
        - gpios are resetted
        - shutters that are opening/closing are set to opened/closed
        """
        #reset gpios
        resp = self.send_command('reset_gpios', 'gpios')
        if resp['error']:
            self.logger.error(resp['message'])
            return

        #and reset shutter
        devices = self.get_module_devices()
        for uuid in devices:
            if devices[uuid]['status']==Shutters.STATUS_OPENING:
                self.change_status(uuid, Shutters.STATUS_OPENED)
            elif devices[uuid]['status']==Shutters.STATUS_CLOSING:
                self.change_status(uuid, Shutters.STATUS_CLOSED)

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

    def __stop_action(self, shutter):
        """
        Stop specified shutter
        @param shutter: shutter object
        """
        #first of all cancel timer if necessary
        if self.__timers.has_key(shutter['uuid']):
            self.logger.debug('Cancel timer of shutter "%s"' % shutter['uuid'])
            self.__timers[shutter['uuid']].cancel()
            del self.__timers[shutter['uuid']]

        #then reset level if necessary
        if shutter['level'] is not None:
            shutter['level'] = None
            self._update_device(shutter['uuid'], shutter)

        #then get gpio
        if shutter['status']==Shutters.STATUS_OPENING:
            gpio_uuid = shutter['shutter_open_uuid']
        elif shutter['status']==Shutters.STATUS_CLOSING:
            gpio_uuid = shutter['shutter_close_uuid']
        else:
            #shutter is already stopped, nothing to do
            self.logger.info('Shutter already stopped. Stop action dropped')
            return
        self.logger.debug('stop shutter: gpio=%s' % str(gpio_uuid))

        #and turn off gpio
        resp = self.send_command('turn_off', 'gpios', {'uuid':gpio_uuid})
        if resp['error']:
            raise CommandError(resp['message'])
        
        #change status
        self.change_status(shutter['uuid'], Shutters.STATUS_PARTIAL)

    def __open_action(self, shutter):
        """
        Open specified shutter
        @param shutter: shutter object
        """
        #turn on gpio
        gpio_uuid = shutter['shutter_open_uuid']
        resp = self.send_command('turn_on', 'gpios', {'uuid':gpio_uuid})
        if resp['error']:
            raise CommandError(resp['message'])

        #change status
        self.change_status(shutter['uuid'], Shutters.STATUS_OPENING)

        #launch turn off timer
        self.logger.debug('Launch timer with duration=%s' % (str(shutter['delay'])))
        self.__timers[shutter['uuid']] = Timer(float(shutter['delay']), self.__end_of_timer, [shutter['uuid'], gpio_uuid, Shutters.STATUS_OPENED])
        self.__timers[shutter['uuid']].start()

    def __close_action(self, shutter, level):
        """
        Close specified shutter
        @param shutter: shutter object
        @param level: level to close shutter
        """
        #turn on gpio
        gpio_uuid = shutter['shutter_close_uuid']
        resp = self.send_command('turn_on', 'gpios', {'uuid':gpio_uuid})
        if resp['error']:
            raise Exception(resp['message'])

        #change status
        self.change_status(shutter['uuid'], Shutters.STATUS_CLOSING)

        if level is not None:
            #compute timer duration according to specified level
            duration = float(shutter['delay']) * float(level) / 100.0
            self.logger.debug('Level duration=%s' % str(duration))

            #launch close timer
            self.logger.debug('Launch timer with level duration=%s' % (str(duration)))
            self.__timers[shutter['uuid']] = Timer(duration, self.__end_of_timer, [shutter['uuid'], gpio_uuid, Shutters.STATUS_PARTIAL])
            self.__timers[shutter['uuid']].start()
        
        else:
            #launch close timer
            self.logger.debug('Launch timer with duration=%s' % (str(shutter['delay'])))
            self.__timers[shutter['uuid']] = Timer(float(shutter['delay']), self.__end_of_timer, [shutter['uuid'], gpio_uuid, Shutters.STATUS_CLOSED])
            self.__timers[shutter['uuid']].start()

    def __execute_action(self, shutter, open_action, close_level=None):
        """
        Execute action according to parameters
        Centralize here all process to avoid turning off and on at the same time
        @param shutter: concerned shutter
        @param open_shutter: True if action is to open shutter. False if is close action
        @param close_level: open or close shutter at specified level value (percentage)
        """
        if not shutter:
            self.logger.error('__execute_action: shutter is not defined')
            return

        if close_level is not None:
            #level requested
            if shutter['status'] in [Shutters.STATUS_OPENING, Shutters.STATUS_CLOSING]:
                #shutter is in opening or closing state, stop it
                self.logger.debug('Shutter is in action, stop it')
                self.__stop_action(shutter)

            elif shutter['status'] in [Shutters.STATUS_CLOSED, Shutters.STATUS_PARTIAL]:
                #shutter is closed or partially closed, open it completely first
                self.logger.debug('Shutter is partially or completely closed, open it')
                #keep in mind level to open it after it will be opened completely
                shutter['level'] = close_level
                if not self._update_device(shutter['uuid'], shutter):
                    raise CommandError('Unable to update device %s' % shutter['uuid'])
                self.__open_action(shutter)

            else:
                #shutter is already opened, close it at specified level
                self.logger.debug('Shutter already opened, close it at %s level' % close_level)
                self.__close_action(shutter, close_level)

        elif open_action:
            #open action triggered
            if shutter['status'] in [Shutters.STATUS_OPENING, Shutters.STATUS_CLOSING]:
                #shutter is in opening or closing state, stop it
                self.__stop_action(shutter)

            elif shutter['status'] in [Shutters.STATUS_CLOSED, Shutters.STATUS_PARTIAL]:
                #shutter is not completely opened or closed, open it
                self.__open_action(shutter)
            else:
                #shutter is already opened, do nothing
                self.logger.debug('Shutter %s is already opened' % shutter['uuid'])
                raise CommandInfo('Shutter is already opened');

        else:
            #close action triggered
            if shutter['status'] in [Shutters.STATUS_OPENING, Shutters.STATUS_CLOSING]:
                #shutter is in opening or closing state, stop it
                self.__stop_action(shutter)

            elif shutter['status'] in [Shutters.STATUS_OPENED, Shutters.STATUS_PARTIAL]:
                #close shutter action
                self.__close_action(shutter, close_level)

            else:
                #shutter is already closed
                self.logger.debug('Shutter %s is already closed' % shutter['uuid'])
                raise CommandInfo('Shutter is already closed');
        

    def add_shutter(self, name, shutter_open, shutter_close, delay, switch_open, switch_close):
        """
        Add shutter
        @param name: shutter name
        @param shutter_open: shutter_open gpio
        @param shutter_close: shutter_close gpio
        @param delay: shutter delay
        @param switch_open: switch_open gpio
        @param switch_close: switch_close gpio
        @return True if shutter added
        """
        #get used gpios
        assigned_gpios = self.get_assigned_gpios()

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
        elif delay<=0:
            raise InvalidParameter('Delay must be greater than 0')
        elif shutter_open==shutter_close or shutter_open==switch_open or shutter_open==switch_close or shutter_close==switch_open or shutter_close==switch_close or switch_open==switch_close:
            raise InvalidParameter('Gpios must all be differents')
        elif shutter_open in assigned_gpios:
            raise InvalidParameter('Open shutter is already assigned')
        elif shutter_close in assigned_gpios:
            raise InvalidParameter('Close shutter is already assigned')
        elif switch_open in assigned_gpios:
            raise InvalidParameter('Open switch is already assigned')
        elif switch_close in assigned_gpios:
            raise InvalidParameter('Close switch is already assigned')
        elif self._search_device('name', name):
            raise InvalidParameter('Shutter name is already assigned')
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
            resp_shutter_open = self.send_command('add_gpio', 'gpios', {'name':name+'_shutteropen', 'gpio':shutter_open, 'mode':'out', 'keep':False, 'reverted':False})
            if resp_shutter_open['error']:
                raise CommandError(resp_shutter_open['message'])
            resp_shutter_open = resp_shutter_open['data']
                
            #configure close shutter
            resp_shutter_close = self.send_command('add_gpio', 'gpios', {'name':name+'_shutterclose', 'gpio':shutter_close, 'mode':'out', 'keep':False, 'reverted':False})
            if resp_shutter_close['error']:
                raise CommandError(resp_shutter_close['message'])
            resp_shutter_close = resp_shutter_close['data']

            #configure open switch
            resp_switch_open = self.send_command('add_gpio', 'gpios', {'name':name+'_switchopen', 'gpio':switch_open, 'mode':'in', 'keep':False, 'reverted':False})
            if resp_switch_open['error']:
                raise CommandError(resp_switch_open['message'])
            resp_switch_open = resp_switch_open['data']

            #configure close switch
            resp_switch_close = self.send_command('add_gpio', 'gpios', {'name':name+'_switchclose', 'gpio':switch_close, 'mode':'in', 'keep':False, 'reverted':False})
            if resp_switch_close['error']:
                raise CommandError(resp_switch_close['message'])
            resp_switch_close = resp_switch_close['data']

            #shutter is valid, prepare new entry
            self.logger.debug('name=%s delay=%s shutter_open=%s shutter_close=%s switch_open=%s switch_close=%s' % (str(name), str(delay), str(shutter_open), str(shutter_close), str(switch_open), str(switch_close)))
            data = {
                'name': name,
                'delay': delay,
                'shutter_open': shutter_open,
                'shutter_open_uuid': resp_shutter_open['uuid'],
                'shutter_close': shutter_close,
                'shutter_close_uuid': resp_shutter_close['uuid'],
                'switch_open': switch_open,
                'switch_open_uuid': resp_switch_open['uuid'],
                'switch_close': switch_close,
                'switch_close_uuid': resp_switch_close['uuid'],
                'status': Shutters.STATUS_OPENED,
                'lastupdate': int(time.time()),
                'type': 'shutter',
                'level': None
            }
    
            #add device
            device = self._add_device(data)
            if device is None:
                raise CommandError('Unale to add device')

        return True

    def delete_shutter(self, uuid):
        """
        Delete specified shutter
        @param uuid: device identifier
        """
        device = self._get_device(uuid)
        if not uuid:
            raise MissingParameter('"uuid" parameter is missing')
        elif device is None:
            raise InvalidParameter('Shutter doesn\'t exist')
        else:
            #unconfigure open shutter
            resp = self.send_command('delete_gpio', 'gpios', {'uuid':device['shutter_open_uuid']})
            if resp['error']:
                raise CommandError(resp['message'])

            #unconfigure close shutter
            resp = self.send_command('delete_gpio', 'gpios', {'uuid':device['shutter_close_uuid']})
            if resp['error']:
                raise CommandError(resp['message'])

            #unconfigure open switch
            resp = self.send_command('delete_gpio', 'gpios', {'uuid':device['switch_open_uuid']})
            if resp['error']:
                raise CommandError(resp['message'])

            #unconfigure close switch
            resp = self.send_command('delete_gpio', 'gpios', {'uuid':device['switch_close_uuid']})
            if resp['error']:
                raise CommandError(resp['message'])

            #shutter is valid, remove it
            if not self._delete_device(uuid):
                raise CommandError('Unable to delete device')

        return True

    def update_shutter(self, uuid, name, delay):
        """
        Update specified shutter
        @param uuid: device identifier
        @param name: shutter name
        @param delay: shutter delay
        """
        shutter = self._get_device(uuid)
        if not uuid:
            raise MissingParameter('"uuid" parameter is missing')
        elif shutter is None:
            raise InvalidParameter('Shutter doesn\'t exist')
        if not name:
            raise MissingParameter('Name parameter is missing')
        elif not delay:
            raise MissingParameter('Delay parameter is missing')
        elif delay<=0:
            raise InvalidParameter('Delay must be greater than 0')
        else:
            #shutter is valid, update it
            shutter['name'] = name
            shutter['delay'] = delay

            if not self._update_device(uuid, shutter):
                raise CommandError('Unable to update device')

        return True

    def change_status(self, uuid, status):
        """
        Change shutter status
        @param uuid: device identifier
        @param status: shutter status
        """
        self.logger.debug('change_status for shutter "%s" to "%s"' % (str(uuid), str(status)))
        device = self._get_device(uuid)
        if not status in [Shutters.STATUS_OPENED, Shutters.STATUS_CLOSED, Shutters.STATUS_PARTIAL, Shutters.STATUS_OPENING, Shutters.STATUS_CLOSING]:
            raise InvalidParameter('Status value is invalid')
        elif device is None:
            raise InvalidParameter('Shutter doesn\'t exist')
        else:
            #get current time
            now = int(time.time())

            #save new status
            device['status'] = status
            device['lastupdate'] = now
            if not self._update_device(uuid, device):
                raise CommandError('Unable to change shutter status')

            #and broadcast new shutter status
            self.send_event('shutters.shutter.%s' % status, {'shutter': device['name'], 'lastupdate':now}, uuid)

    def __end_of_timer(self, uuid, gpio_uuid, new_status):
        """
        Triggered when timer is over
        """
        #turn off specified gpio
        self.logger.debug('end_of_timer for gpio "%s"' % gpio_uuid)
        resp = self.send_command('turn_off', 'gpios', {'uuid':gpio_uuid})
        if resp['error']:
            raise CommandError(resp['message'])

        #and update status to specified one
        self.change_status(uuid, new_status)

    def open_shutter(self, uuid):
        """
        Open specified shutter
        @param uuid: device identifier
        """
        self.logger.debug('Open shutter %s' % (uuid))
        device = self._get_device(uuid)
        if device is None:
            raise InvalidParameter('Shutter %s doesn\'t exist' % uuid)
        self.__execute_action(device, True)

    def close_shutter(self, uuid):
        """
        Close specified shutter
        @param uuid: device identifier
        """
        self.logger.debug('Close shutter %s' % (uuid))
        device = self._get_device(uuid)
        if device is None:
            raise InvalidParameter('Shutter %s doesn\'t exist' % uuid)
        self.__execute_action(device, False)

    def stop_shutter(self, uuid):
        """
        Stop specified shutter
        @param uuid: device identifier
        """
        self.logger.debug('stop_shutter %s' % uuid)
        device = self._get_device(uuid)
        if device is None:
            raise InvalidParameter('Shutter %s doesn\'t exist' % uuid)
        self.__stop_action(device)

    def level_shutter(self, uuid, level):
        """
        Close shutter at specified level.
        If shutter is not opened, it is opened first then close at level.
        @param uuid: device uuid
        @param level: open shutter at specified level value (percentage)
        """
        self.logger.debug('level_shutter %s' % uuid)
        device = self._get_device(uuid)
        if device is None:
            raise InvalidParameter('Shutter %s doesn\'t exist' % uuid)
        if not isinstance(level, int):
            raise InvalidParameter('Level must be an integer')
        if level<0 or level>100:
            raise InvalidParameter('Level value must be between 0 and 100')
        self.__execute_action(device, True, level)

if __name__ == '__main__':
    #testu
    o = Shutters()
    print o.get_raspi_gpios()
