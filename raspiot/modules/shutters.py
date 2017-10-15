#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.utils import MissingParameter, InvalidParameter, CommandError, CommandInfo
from raspiot.raspiot import RaspIotModule
from threading import Timer
import time

__all__ = [u'Shutters']


class Shutters(RaspIotModule):
    """
    Shutters module helps user configures GPIOS to control roller shutters. It allows:
     - open and close shutters in software (using dashboard widget)
     - configure relays control
     - configure switches
     - close shutters at specific level (in percentage)
    """

    MODULE_CONFIG_FILE = u'shutters.conf'
    MODULE_DEPS = [u'gpios']
    MODULE_DESCRIPTION = u'Controls your roller shutters'
    MODULE_LOCKED = False
    MODULE_URL = None
    MODULE_TAGS = []
    MODULE_COUNTRY = 'any'

    STATUS_OPENED = u'opened'
    STATUS_CLOSED = u'closed'
    STATUS_PARTIAL = u'partial'
    STATUS_OPENING = u'opening'
    STATUS_CLOSING = u'closing'

    def __init__(self, bus, debug_enabled, join_event):
        """
        Constructor

        Args:
            bus (MessageBus): MessageBus instance
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotModule.__init__(self, bus, debug_enabled, join_event)

        #internal timers
        self.__timers = {}
        self.raspi_gpios = {}

    def _configure(self):
        """
        Configure module
        """
        #raspi gpios
        self.raspi_gpios = self.get_raspi_gpios()

        #reset gpios and shutters
        self.reset()

    def get_module_config(self):
        """
        Get full module configuration

        Returns:
            dict: module configuration
        """
        config = {}
        config[u'raspi_gpios'] = self.get_raspi_gpios()
        return config

    def event_received(self, event):
        """
        Event received from bus

        Params:
            event (MessageRequest): event data
        """
        self.logger.debug(u'Event received %s' % event)
        #drop startup events
        if event[u'startup']:
            self.logger.debug(u'Drop startup event')
            return

        #process received event
        if event[u'event']==u'gpios.gpio.off':
            #drop gpio init event
            if event[u'params'][u'init']:
                self.logger.debug(u'Drop gpio init event')
                return

            #gpio turned off, get gpio device
            gpio_uuid = event[u'uuid']
            self.logger.debug(u'gpio_uuid=%s' % event[u'uuid'])

            #search shutter and execute action
            shutters = self._get_devices()
            self.logger.debug(u'shutters=%s' % shutters)
            for uuid in shutters:

                #execute action according to triggered gpio
                self.logger.debug(u'level=%s' % unicode(shutters[uuid][u'level']))
                if shutters[uuid][u'shutter_open_uuid']==gpio_uuid and shutters[uuid][u'level'] is not None:
                    self.logger.debug(u'Shutter just opened after level_shutter action. Close it now')
                    #reset shutter level value
                    level = shutters[uuid][u'level']
                    shutters[uuid][u'level'] = None
                    self._update_device(uuid, shutters[uuid])
                    self.__execute_action(shutters[uuid], False, level)
                    break

                if shutters[uuid][u'switch_open_uuid']==gpio_uuid:
                    self.logger.debug(u'Found switch_open_uuid')
                    self.__execute_action(shutters[uuid], True)
                    break

                elif shutters[uuid][u'switch_close_uuid']==gpio_uuid:
                    self.logger.debug(u'Found switch_close_uuid')
                    self.__execute_action(shutters[uuid], False)
                    break

            self.logger.debug(u'Done')

    def reset(self):
        """
        Reset all that need to be resetted:
        - gpios are resetted
        - shutters that are opening/closing are set to opened/closed
        """
        #reset gpios
        resp = self.send_command(u'reset_gpios', u'gpios')
        if resp[u'error']:
            self.logger.error(resp[u'message'])
            return

        #and reset shutter
        devices = self.get_module_devices()
        for uuid in devices:
            if devices[uuid][u'status']==Shutters.STATUS_OPENING:
                self.change_status(uuid, Shutters.STATUS_OPENED)
            elif devices[uuid][u'status']==Shutters.STATUS_CLOSING:
                self.change_status(uuid, Shutters.STATUS_CLOSED)

    def get_raspi_gpios(self):
        """
        Get raspi gpios

        Returns:
            dict: raspi gpios
        """
        resp = self.send_command(u'get_raspi_gpios', u'gpios')
        if resp['error']:
            self.logger.error(resp[u'message'])
            return {}
        else:
            return resp[u'data']

    def get_assigned_gpios(self):
        """
        Return assigned gpios

        Returns:
            dict: assigned gpios
        """
        resp = self.send_command(u'get_assigned_gpios', u'gpios')
        if resp[u'error']:
            self.logger.error(resp[u'message'])
            return {}
        else:
            return resp[u'data']

    def __stop_action(self, shutter):
        """
        Stop specified shutter

        Params:
            shutter (dict): shutter data
        """
        #first of all cancel timer if necessary
        if self.__timers.has_key(shutter[u'uuid']):
            self.logger.debug(u'Cancel timer of shutter "%s"' % shutter[u'uuid'])
            self.__timers[shutter[u'uuid']].cancel()
            del self.__timers[shutter[u'uuid']]

        #then reset level if necessary
        if shutter[u'level'] is not None:
            shutter[u'level'] = None
            self._update_device(shutter[u'uuid'], shutter)

        #then get gpio
        if shutter[u'status']==Shutters.STATUS_OPENING:
            gpio_uuid = shutter[u'shutter_open_uuid']
        elif shutter[u'status']==Shutters.STATUS_CLOSING:
            gpio_uuid = shutter[u'shutter_close_uuid']
        else:
            #shutter is already stopped, nothing to do
            self.logger.info(u'Shutter already stopped. Stop action dropped')
            return
        self.logger.debug(u'stop shutter: gpio=%s' % unicode(gpio_uuid))

        #and turn off gpio
        resp = self.send_command(u'turn_off', u'gpios', {u'uuid':gpio_uuid})
        if resp[u'error']:
            raise CommandError(resp[u'message'])
        
        #change status
        self.change_status(shutter[u'uuid'], Shutters.STATUS_PARTIAL)

    def __open_action(self, shutter):
        """
        Open specified shutter

        Params:
            shutter (dict): shutter data
        """
        #turn on gpio
        gpio_uuid = shutter[u'shutter_open_uuid']
        resp = self.send_command(u'turn_on', u'gpios', {u'uuid':gpio_uuid})
        if resp[u'error']:
            raise CommandError(resp[u'message'])

        #change status
        self.change_status(shutter[u'uuid'], Shutters.STATUS_OPENING)

        #launch turn off timer
        self.logger.debug(u'Launch timer with duration=%s' % (unicode(shutter[u'delay'])))
        self.__timers[shutter[u'uuid']] = Timer(float(shutter[u'delay']), self.__end_of_timer, [shutter[u'uuid'], gpio_uuid, Shutters.STATUS_OPENED])
        self.__timers[shutter[u'uuid']].start()

    def __close_action(self, shutter, level):
        """
        Close specified shutter

        Params:
            shutter (dict): shutter data
            level (int): level to close shutter (percentage)
        """
        #turn on gpio
        gpio_uuid = shutter[u'shutter_close_uuid']
        resp = self.send_command(u'turn_on', u'gpios', {u'uuid':gpio_uuid})
        if resp[u'error']:
            raise Exception(resp[u'message'])

        #change status
        self.change_status(shutter[u'uuid'], Shutters.STATUS_CLOSING)

        if level is not None:
            #compute timer duration according to specified level
            duration = float(shutter[u'delay']) * float(level) / 100.0
            self.logger.debug(u'Level duration=%s' % unicode(duration))

            #launch close timer
            self.logger.debug(u'Launch timer with level duration=%s' % (unicode(duration)))
            self.__timers[shutter[u'uuid']] = Timer(duration, self.__end_of_timer, [shutter[u'uuid'], gpio_uuid, Shutters.STATUS_PARTIAL])
            self.__timers[shutter[u'uuid']].start()
        
        else:
            #launch close timer
            self.logger.debug(u'Launch timer with duration=%s' % (unicode(shutter[u'delay'])))
            self.__timers[shutter[u'uuid']] = Timer(float(shutter[u'delay']), self.__end_of_timer, [shutter[u'uuid'], gpio_uuid, Shutters.STATUS_CLOSED])
            self.__timers[shutter[u'uuid']].start()

    def __execute_action(self, shutter, open_action, close_level=None):
        """
        Execute action according to parameters
        Centralize here all process to avoid turning off and on at the same time

        Params:
            shutter (dict): concerned shutter data
            open_shutter (bool): True if action is to open shutter. False if is close action
            close_level (int): open or close shutter at specified level value (percentage)
        """
        if not shutter:
            self.logger.error(u'__execute_action: shutter is not defined')
            return

        if close_level is not None:
            #level requested
            if shutter[u'status'] in [Shutters.STATUS_OPENING, Shutters.STATUS_CLOSING]:
                #shutter is in opening or closing state, stop it
                self.logger.debug(u'Shutter is in action, stop it')
                self.__stop_action(shutter)

            elif shutter[u'status'] in [Shutters.STATUS_CLOSED, Shutters.STATUS_PARTIAL]:
                #shutter is closed or partially closed, open it completely first
                self.logger.debug(u'Shutter is partially or completely closed, open it')
                #keep in mind level to open it after it will be opened completely
                shutter[u'level'] = close_level
                if not self._update_device(shutter[u'uuid'], shutter):
                    raise CommandError(u'Unable to update device %s' % shutter['uuid'])
                self.__open_action(shutter)

            else:
                #shutter is already opened, close it at specified level
                self.logger.debug(u'Shutter already opened, close it at %s level' % close_level)
                self.__close_action(shutter, close_level)

        elif open_action:
            #open action triggered
            if shutter[u'status'] in [Shutters.STATUS_OPENING, Shutters.STATUS_CLOSING]:
                #shutter is in opening or closing state, stop it
                self.__stop_action(shutter)

            elif shutter[u'status'] in [Shutters.STATUS_CLOSED, Shutters.STATUS_PARTIAL]:
                #shutter is not completely opened or closed, open it
                self.__open_action(shutter)
            else:
                #shutter is already opened, do nothing
                self.logger.debug(u'Shutter %s is already opened' % shutter[u'uuid'])
                raise CommandInfo(u'Shutter is already opened');

        else:
            #close action triggered
            if shutter[u'status'] in [Shutters.STATUS_OPENING, Shutters.STATUS_CLOSING]:
                #shutter is in opening or closing state, stop it
                self.__stop_action(shutter)

            elif shutter[u'status'] in [Shutters.STATUS_OPENED, Shutters.STATUS_PARTIAL]:
                #close shutter action
                self.__close_action(shutter, close_level)

            else:
                #shutter is already closed
                self.logger.debug(u'Shutter %s is already closed' % shutter['uuid'])
                raise CommandInfo(u'Shutter is already closed');
        

    def add_shutter(self, name, shutter_open, shutter_close, delay, switch_open, switch_close):
        """
        Add shutter

        Paarams:
            name (string): shutter name
            shutter_open (string): shutter_open gpio
            shutter_close (string): shutter_close gpio
            delay (int): shutter delay (seconds)
            switch_open (string): switch_open gpio
            switch_close (string): switch_close gpio

        Returns:
            bool: True if shutter added
        """
        #get used gpios
        assigned_gpios = self.get_assigned_gpios()

        #check values
        if not name:
            raise MissingParameter(u'Name parameter is missing')
        elif not shutter_open:
            raise MissingParameter(u'Open shutter parameter is missing')
        elif not shutter_close:
            raise MissingParameter(u'Close shutter parameter is missing')
        elif not switch_open:
            raise MissingParameter(u'Open switch parameter is missing')
        elif not switch_close:
            raise MissingParameter(u'Close switch parameter is missing')
        elif not delay:
            raise MissingParameter(u'Delay parameter is missing')
        elif delay<=0:
            raise InvalidParameter(u'Delay must be greater than 0')
        elif shutter_open==shutter_close or shutter_open==switch_open or shutter_open==switch_close or shutter_close==switch_open or shutter_close==switch_close or switch_open==switch_close:
            raise InvalidParameter(u'Gpios must all be differents')
        elif shutter_open in assigned_gpios:
            raise InvalidParameter(u'Open shutter is already assigned')
        elif shutter_close in assigned_gpios:
            raise InvalidParameter(u'Close shutter is already assigned')
        elif switch_open in assigned_gpios:
            raise InvalidParameter(u'Open switch is already assigned')
        elif switch_close in assigned_gpios:
            raise InvalidParameter(u'Close switch is already assigned')
        elif self._search_device(u'name', name):
            raise InvalidParameter(u'Shutter name is already assigned')
        elif shutter_open not in self.raspi_gpios:
            raise InvalidParameter(u'Open shutter does not exist for this raspberry pi')
        elif shutter_close not in self.raspi_gpios:
            raise InvalidParameter(u'Close shutter does not exist for this raspberry pi')
        elif switch_open not in self.raspi_gpios:
            raise InvalidParameter(u'Open switch does not exist for this raspberry pi')
        elif switch_close not in self.raspi_gpios:
            raise InvalidParameter(u'Close switch does not exist for this raspberry pi')
        else:
            #configure open shutter
            resp_shutter_open = self.send_command(u'add_gpio', u'gpios', {u'name':name+u'_shutteropen', u'gpio':shutter_open, u'mode':u'out', u'keep':False, u'reverted':False})
            if resp_shutter_open[u'error']:
                raise CommandError(resp_shutter_open[u'message'])
            resp_shutter_open = resp_shutter_open[u'data']
                
            #configure close shutter
            resp_shutter_close = self.send_command(u'add_gpio', u'gpios', {u'name':name+u'_shutterclose', u'gpio':shutter_close, u'mode':u'out', u'keep':False, u'reverted':False})
            if resp_shutter_close[u'error']:
                raise CommandError(resp_shutter_close[u'message'])
            resp_shutter_close = resp_shutter_close[u'data']

            #configure open switch
            resp_switch_open = self.send_command(u'add_gpio', u'gpios', {u'name':name+u'_switchopen', u'gpio':switch_open, u'mode':u'in', u'keep':False, u'reverted':False})
            if resp_switch_open[u'error']:
                raise CommandError(resp_switch_open[u'message'])
            resp_switch_open = resp_switch_open[u'data']

            #configure close switch
            resp_switch_close = self.send_command(u'add_gpio', u'gpios', {u'name':name+u'_switchclose', u'gpio':switch_close, u'mode':u'in', u'keep':False, u'reverted':False})
            if resp_switch_close[u'error']:
                raise CommandError(resp_switch_close[u'message'])
            resp_switch_close = resp_switch_close[u'data']

            #shutter is valid, prepare new entry
            self.logger.debug(u'name=%s delay=%s shutter_open=%s shutter_close=%s switch_open=%s switch_close=%s' % (unicode(name), unicode(delay), unicode(shutter_open), unicode(shutter_close), unicode(switch_open), unicode(switch_close)))
            data = {
                u'name': name,
                u'delay': delay,
                u'shutter_open': shutter_open,
                u'shutter_open_uuid': resp_shutter_open[u'uuid'],
                u'shutter_close': shutter_close,
                u'shutter_close_uuid': resp_shutter_close[u'uuid'],
                u'switch_open': switch_open,
                u'switch_open_uuid': resp_switch_open[u'uuid'],
                u'switch_close': switch_close,
                u'switch_close_uuid': resp_switch_close[u'uuid'],
                u'status': Shutters.STATUS_OPENED,
                u'lastupdate': int(time.time()),
                u'type': u'shutter',
                u'level': None
            }
    
            #add device
            device = self._add_device(data)
            if device is None:
                raise CommandError(u'Unable to add device')

        return True

    def delete_shutter(self, uuid):
        """
        Delete specified shutter

        Params:
            uuid (string): device identifier

        Raises:
            CommandError, InvalidParameter, MissingParameter
        """
        device = self._get_device(uuid)
        if not uuid:
            raise MissingParameter(u'Uuid parameter is missing')
        elif device is None:
            raise InvalidParameter(u'Shutter doesn\'t exist')
        else:
            #unconfigure open shutter
            resp = self.send_command(u'delete_gpio',u'gpios', {u'uuid':device[u'shutter_open_uuid']})
            if resp[u'error']:
                raise CommandError(resp[u'message'])

            #unconfigure close shutter
            resp = self.send_command(u'delete_gpio', u'gpios', {u'uuid':device[u'shutter_close_uuid']})
            if resp[u'error']:
                raise CommandError(resp[u'message'])

            #unconfigure open switch
            resp = self.send_command(u'delete_gpio', u'gpios', {u'uuid':device[u'switch_open_uuid']})
            if resp[u'error']:
                raise CommandError(resp[u'message'])

            #unconfigure close switch
            resp = self.send_command(u'delete_gpio', u'gpios', {u'uuid':device[u'switch_close_uuid']})
            if resp[u'error']:
                raise CommandError(resp[u'message'])

            #shutter is valid, remove it
            if not self._delete_device(uuid):
                raise CommandError(u'Unable to delete device')

        return True

    def update_shutter(self, uuid, name, delay):
        """

        Update specified shutter
        Params:
            uuid (string): device identifier
            name (string): shutter name
            delay (int): shutter delay (seconds)

        Raises:
            CommandError, InvalidParameter, MissingParameter
        """
        shutter = self._get_device(uuid)
        if not uuid:
            raise MissingParameter(u'Uuid parameter is missing')
        elif shutter is None:
            raise InvalidParameter(u'Shutter doesn\'t exist')
        if not name:
            raise MissingParameter(u'Name parameter is missing')
        elif not delay:
            raise MissingParameter(u'Delay parameter is missing')
        elif delay<=0:
            raise InvalidParameter(u'Delay must be greater than 0')
        else:
            #shutter is valid, update it
            shutter[u'name'] = name
            shutter[u'delay'] = delay

            if not self._update_device(uuid, shutter):
                raise CommandError(u'Unable to update device')

        return True

    def change_status(self, uuid, status):
        """
        Change shutter status

        Params:
            uuid (string): device identifier
            status (string): shutter status
        """
        self.logger.debug(u'Change_status for shutter "%s" to "%s"' % (unicode(uuid), unicode(status)))
        device = self._get_device(uuid)
        if not status in [Shutters.STATUS_OPENED, Shutters.STATUS_CLOSED, Shutters.STATUS_PARTIAL, Shutters.STATUS_OPENING, Shutters.STATUS_CLOSING]:
            raise InvalidParameter(u'Status value is invalid')
        elif device is None:
            raise InvalidParameter(u'Shutter doesn\'t exist')
        else:
            #get current time
            now = int(time.time())

            #save new status
            device[u'status'] = status
            device[u'lastupdate'] = now
            if not self._update_device(uuid, device):
                raise CommandError(u'Unable to change shutter status')

            #and broadcast new shutter status
            self.send_event(u'shutters.shutter.%s' % status, {u'shutter': device[u'name'], u'lastupdate':now}, uuid)

    def __end_of_timer(self, uuid, gpio_uuid, new_status):
        """
        Triggered when timer is over

        Params:
            uuid (string): device identifier
            gpio_uuid (string): gpio device identifier
            new_status (string): new shutter status

        Raises:
            CommandError
        """
        #turn off specified gpio
        self.logger.debug(u'end_of_timer for gpio "%s"' % gpio_uuid)
        resp = self.send_command(u'turn_off', u'gpios', {u'uuid':gpio_uuid})
        if resp[u'error']:
            raise CommandError(resp[u'message'])

        #and update status to specified one
        self.change_status(uuid, new_status)

    def open_shutter(self, uuid):
        """
        Open specified shutter

        Params:
            uuid (string): device identifier

        Raises:
            InvalidParameter
        """
        self.logger.debug(u'Open shutter %s' % (uuid))
        device = self._get_device(uuid)
        if device is None:
            raise InvalidParameter(u'Shutter %s doesn\'t exist' % uuid)
        self.__execute_action(device, True)

    def close_shutter(self, uuid):
        """
        Close specified shutter

        Params:
            uuid (string): device identifier

        Raises:
            InvalidParameter
        """
        self.logger.debug('uClose shutter %s' % (uuid))
        device = self._get_device(uuid)
        if device is None:
            raise InvalidParameter(u'Shutter %s doesn\'t exist' % uuid)
        self.__execute_action(device, False)

    def stop_shutter(self, uuid):
        """
        Stop specified shutter

        Params:
            uuid (string): device identifier

        Raises:
            InvalidParameter
        """
        self.logger.debug(u'stop_shutter %s' % uuid)
        device = self._get_device(uuid)
        if device is None:
            raise InvalidParameter(u'Shutter %s doesn\'t exist' % uuid)
        self.__stop_action(device)

    def level_shutter(self, uuid, level):
        """
        Close shutter at specified level.
        If shutter is not opened, it is opened first then close at level.

        Params:
            uuid (string): device uuid
            level (int): open shutter at specified level value (percentage)

        Raises:
            InvalidParameter
        """
        self.logger.debug(u'level_shutter %s' % uuid)
        device = self._get_device(uuid)
        if device is None:
            raise InvalidParameter(u'Shutter %s doesn\'t exist' % uuid)
        if not isinstance(level, int):
            raise InvalidParameter(u'Level must be an integer')
        if level<0 or level>100:
            raise InvalidParameter(u'Level value must be between 0 and 100')
        self.__execute_action(device, True, level)

