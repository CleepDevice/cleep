#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import json
from bus import BusClient
from threading import Lock, Thread
from utils import CommandError, MissingParameter, InvalidParameter
import time
import copy
import uuid


__all__ = [u'RaspIot', u'RaspIotRenderer', u'RaspIotModule']


class RaspIot(BusClient):
    """
    Base raspiot class
    It implements :
     - configuration helpers
     - message bus access
     - logger with log level configured
    """
    CONFIG_DIR = u'/etc/raspiot/'
    MODULE_DEPS = []

    def __init__(self, bus, debug_enabled):
        """
        Constructor.

        Args:
            bus (MessageBus): MessageBus instance.
            debug_enabled (bool): flag to set debug level to logger.
        """
        #init bus
        BusClient.__init__(self, bus)

        #init logger
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)
        self.debug_enabled = debug_enabled

        #load and check configuration
        self.__configLock = Lock()
        self._config = self._load_config()
        if getattr(self, u'DEFAULT_CONFIG', None) is not None:
            self._check_config(self.DEFAULT_CONFIG)

    def __del__(self):
        """
        Destructor.
        """
        self.stop()

    def __file_is_empty(self, path):
        """
        Return True if file is empty.

        Args:
            path (string): path to check.
        
        Returns:
            bool: True if file is empty.
        """
        return os.path.isfile(path) and not os.path.getsize(path)>0

    def __has_config_file(self):
        """
        Check if module has configuration file.

        Returns:
            bool: True if module has config file, False otherwise.
        """
        if getattr(self, u'MODULE_CONFIG_FILE', None) is None:
            return False

        return True

    def _load_config(self):
        """
        Load config file.

        Returns:
            dict: configuration file content or None if error occured.
        """
        #check if module have config file
        if not self.__has_config_file():
            self.logger.info(u'Module %s has no configuration file configured' % self.__class__.__name__)
            return None

        self.__configLock.acquire(True)
        out = None
        try:
            path = os.path.join(RaspIot.CONFIG_DIR, self.MODULE_CONFIG_FILE)
            self.logger.debug(u'Loading conf file %s' % path)
            if os.path.exists(path) and not self.__file_is_empty(path):
                f = open(path, u'r')
                raw = f.read()
                f.close()
            else:
                #no conf file yet. Create default one
                f = open(path, u'w')
                default = {}
                raw = json.dumps(default)
                f.write(raw)
                f.close()
                time.sleep(.25) #make sure file is written
            self._config = json.loads(raw)
            out = self._config
        except:
            self.logger.exception(u'Unable to load config file %s:' % path)
        self.__configLock.release()

        return out
 
    def _save_config(self, config):
        """
        Save config file.

        Args:
            config (dict): config to save.
        
        Returns:
            dict: configuration file content or None if error occured.
        """
        out = None
        force_reload = False

        #check if module have config file
        if not self.__has_config_file():
            self.logger.warning(u'Module %s has no configuration file configured' % self.__class__.__name__)
            return None

        self.__configLock.acquire(True)
        try:
            path = os.path.join(RaspIot.CONFIG_DIR, self.MODULE_CONFIG_FILE)
            f = open(path, u'w')
            f.write(json.dumps(config))
            f.close()
            force_reload = True
        except:
            self.logger.exception(u'Unable to write config file %s:' % path)
        self.__configLock.release()

        if force_reload:
            #reload config
            out = self._load_config()

        return out

    def _reload_config(self):
        """
        Reload configuration.
        Just an alias to _load_config without config content.
        """
        self._load_config()

    def _get_config(self):
        """
        Return copy of config dict.

        Returns:
            dict: config file content (copy).
        """
        #check if module have config file
        if not self.__has_config_file():
            self.logger.warning(u'Module %s has no configuration file configured' % self.__class__.__name__)
            return {}

        self.__configLock.acquire(True)
        copy_ = copy.deepcopy(self._config)
        self.__configLock.release()

        return copy_

    def _check_config(self, keys):
        """
        Check config files looking for specified keys.
        If key not found, key is added with specified default value.
        Save new configuration file if necessary.

        Args:
            keys (dict): dict of keys-default values {'key1':'default value1', ...}.

        Returns:
            None: nothing, only check configuration file consistency.
        """
        config = self._get_config()
        fixed = False
        for key in keys:
            if not config.has_key(key):
                #fix missing key
                config[key] = keys[key]
                fixed = True
        if fixed:
            self.logger.debug(u'Config file fixed')
            self._save_config(config)

    def _get_unique_id(self):
        """
        Return unique id. Useful to get unique device identifier.

        Returns:
            string: new unique id (uuid4 format).
        """
        return unicode(uuid.uuid4())

    def is_debug_enabled(self):
        """
        Return True if debug is enabled

        Returns:
            bool: True if debug enabled
        """
        return self.debug_enabled

    def set_debug(self, debug):
        """
        Enable or disable debug level. It changes logger level on the fly.

        Args:
            debug (bool): debug enabled if True, otherwise info level
        """
        #change current logger debug level
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        #update debug flag
        self.debug_enabled = debug

    def get_module_config(self):
        """
        Returns module configuration.
        
        Returns:
            dict: all config content except 'devices' entry.
        """
        config = self._get_config()

        #remove devices from config
        if config.has_key(u'devices'):
            del config[u'devices']

        return config

    def get_module_devices(self):
        """
        Returns module devices.

        Returns:
            dict: all devices registered in 'devices' config section.
        """
        if self._config is not None and self._config.has_key(u'devices'):
            return self._config[u'devices']
        else:
            return {}

    def get_module_commands(self):
        """
        Return available module commands.
        
        Returns:
            list: list of command names.
        """
        ms = dir(self)
        for m in ms[:]:
            if not callable(getattr(self, m)):
                #filter module members
                ms.remove(m)
            elif m.startswith('_'):
                #filter protected or private commands
                ms.remove(m)
            elif m in (u'send_command', u'send_event', u'start', u'stop', u'push', u'render_event', u'event_received'):
                #filter bus commands
                ms.remove(m)
            elif m in (u'getName', u'isAlive', u'isDaemon', u'is_alive', u'join', u'run', u'setDaemon', u'setName'):
                #filter system commands
                ms.remove(m)

        return ms

    def start(self):
        """
        Start module.
        """
        BusClient.start(self)
        self._start()

    def _start(self):
        """
        Post start: called just after module is started.
        This function is used to launch processes that requests cpu time and cannot be launched during init.
        At this time application is starting up and bus is not operational. If you need to push message to
        bus you should implement event_received method and handle system.application.ready event.
        """
        pass

    def stop(self):
        """
        Stop process.
        """
        BusClient.stop(self)
        self._stop()

    def _stop(self):
        """
        Pre stop: called just before module is stopped.
        This function is used to stop specific processes like threads.
        """
        pass

    def is_module_loaded(self, module):
        """
        Request inventory to check if specified module is loaded or not.
        
        Args:
            module (string): module name.

        Returns:
            bool: True if module is loaded, False otherwise.
        """
        resp = self.send_command(u'is_module_loaded', u'inventory', {u'module': module})
        if resp[u'error']:
            self.logger.error(u'Unable to request inventory')

        return resp[u'data']





class RaspIotModule(RaspIot):
    """
    Base raspiot class for module
    It implements:
     - device helpers
    """

    def __init__(self, bus, debug_enabled):
        """
        Constructor.

        Args:
            bus (MessageBus): MessageBus instance.
            debug_enabled (bool): flag to set debug level to logger.
        """
        #init raspiot
        RaspIot.__init__(self, bus, debug_enabled)

    def _add_device(self, data):
        """
        Helper function to add device in module configuration file.
        This function auto inject new entry "devices" in configuration file.
        This function appends new device in devices section and add unique id in uuid property.
        It also appends 'name' property if not provided.

        Args:
            data (dict): device data.
        
        Returns:
            dict: device data if process was successful, None otherwise.
        """
        config = self._get_config()

        #prepare config file
        if not config.has_key(u'devices'):
            config[u'devices'] = {}

        #prepare data
        uuid = self._get_unique_id()
        data['uuid'] = uuid
        if not data.has_key(u'name'):
            data[u'name'] = u''
        config[u'devices'][uuid] = data
        self.logger.debug(u'config=%s' % config)

        #save data
        if self._save_config(config) is None:
            #error occured
            return None

        return data

    def _delete_device(self, uuid):
        """
        Helper function to remove device from module configuration file.

        Args:
            uuid (string): device identifier.

        Returns:
            bool: True if device was deleted, False otherwise.
        """
        config = self._get_config()

        #check values
        if not config.has_key(u'devices'):
            self.logger.error(u'"devices" config file entry doesn\'t exist')
            raise Exception(u'"devices" config file entry doesn\'t exist')
        if not config[u'devices'].has_key(uuid):
            self.logger.error(u'Trying to delete unknown device')
            return False

        #delete device entry
        del config[u'devices'][uuid]

        #save config
        if self._save_config(config) is None:
            #error occured
            return False

        return True

    def _update_device(self, uuid, data):
        """
        Helper function to update device.

        Args:
            uuid (string): device identifier.
            data (dict): device data to update.

        Returns:
            bool: True if device updated, False otherwise.
        """
        config = self._get_config()

        #check values
        if not config.has_key(u'devices'):
            self.logger.error(u'"devices" config file entry doesn\'t exist')
            raise Exception(u'"devices" config file entry doesn\'t exist')
        if not config[u'devices'].has_key(uuid):
            self.logger.error(u'Trying to update unknown device')

        #check uuid key existence
        if not data.has_key(u'uuid'):
            data[u'uuid'] = uuid

        #update data
        config[u'devices'][uuid] = data

        #save data
        if self._save_config(config) is None:
            #error occured
            return False

        return True

    def _search_device(self, key, value):
        """
        Helper function to search a device based on the property value.
        Useful to search a device of course, but can be used to check if a name is not already assigned to a device.

        Args:
            key (string): device property to search on.
            value (any): property value.

        Returns
            dict: the device data if key-value found, or None otherwise.
        """
        config = self._get_config()

        #check values
        if not config.has_key(u'devices'):
            self.logger.warning(u'"devices" config file entry doesn\'t exist')
            return None
        if len(config[u'devices'])==0:
            #no device in dict, return no match
            return None

        #search
        for uuid in config[u'devices']:
            if config[u'devices'][uuid].has_key(key) and config[u'devices'][uuid][key]==value:
                #device found
                return config[u'devices'][uuid]

        return None

    def _get_device(self, uuid):
        """
        Get device according to specified identifier.

        Args:
            uuid (string): device identifier.

        Returns:
            dict: None if device not found, device data otherwise.
        """
        config = self._get_config()

        #check values
        if not config.has_key(u'devices'):
            self.logger.error(u'"devices" config file entry doesn\'t exist')
            return None

        if config[u'devices'].has_key(uuid):
            return config[u'devices'][uuid]

        return None

    def _get_devices(self):
        """
        Return module devices (alias to get_module_devices function).

        Returns:
            list: list of devices.
        """
        return self.get_module_devices()

    def _get_device_count(self):
        """
        Return number of devices in configuration file".

        Returns:
            int: number of saved devices.
        """
        if self._config.has_key(u'devices'):
            return len(self._config[u'devices'])
        else:
            return 0

    def render_event(self, event, event_values, renderer_types):
        """ 
        Post event to specified renderers types

        Args:
            renderer_types (list): list of renderer types

        Returns:
            bool: True if post command succeed, False otherwise
        """
        resp = self.send_command(u'render_event', u'inventory', {u'event':event, u'event_values':event_values, u'types': renderer_types})
        if resp[u'error']:
            self.logger.error(u'Unable to request renderers by type')
            return False

        return True



class RaspIotRenderer(RaspIotModule):
    """
    Base raspiot class for renderer.
    It implements:
     - automatic renderer registration
     - post function to post data to renderer
    """

    def __init__(self, bus, debug_enabled):
        """
        Constructor.

        Args:
            bus (MessageBus): MessageBus instance.
            debug_enabled (bool): flag to set debug level to logger.
        """
        #init raspiot
        RaspIot.__init__(self, bus, debug_enabled)
        self.profiles_types = []

    def register_renderer(self):
        """
        Register renderer to inventory.

        Returns:
            bool: True if renderer registered successfully
        """
        if getattr(self, u'RENDERER_PROFILES', None) is None:
            raise CommandError(u'RENDERER_PROFILES is not defined in %s' % self.__class__.__name__)
        if getattr(self, u'RENDERER_TYPE', None) is None:
            raise CommandError(u'RENDERER_TYPE is not defined in %s' % self.__class__.__name__)

        #cache profile types as string
        for profile in self.RENDERER_PROFILES:
            self.profiles_types.append(profile.__class__.__name__)

        resp = self.send_command(u'register_renderer', u'inventory', {u'type':self.RENDERER_TYPE, u'profiles':self.RENDERER_PROFILES})
        if resp[u'error']:
            self.logger.error(u'Unable to register renderer to inventory: %s' % resp[u'message'])

        return True

    def render(self, data):
        """
        Post data to renderer.

        Args:
            data (dict): data to post.

        Returns:
            bool: True if post is successful.

        Raises:
            MissingParameter, InvalidParameter
        """
        #check data type
        if data.__class__.__name__ not in self.profiles_types:
            raise InvalidParameter(u'Data has invalid type "%s"' % data.__class__.__name__)

        #call implementation
        return self._render(data)

    def _render(self, data):
        """
        Fake render method
        """
        pass

    def event_received(self, event):
        """ 
        Event received from bus

        Args:
            event (MessageRequest): received event
        """
        if event[u'event']==u'system.application.ready':
            #application is ready, register renderer
            self.register_renderer()

