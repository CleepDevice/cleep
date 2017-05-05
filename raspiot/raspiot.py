#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import json
from bus import BusClient
from threading import Lock, Thread
import time
import copy
import uuid


__all__ = ['RaspIot', 'RaspIotProvider', 'RaspIotModule']


class RaspIot(BusClient):
    """
    Base raspiot class
    It implements :
     - configuration helpers
     - message bus access
     - logger with log level configured
    """
    CONFIG_DIR = '/etc/raspiot/'
    MODULE_DEPS = []

    def __init__(self, bus, debug_enabled):
        """
        Constructor
        @param bus: MessageBus instance
        @param debug_enabled: flag to set debug level to logger (bool)
        """
        #init bus
        BusClient.__init__(self, bus, self._start, self._stop)

        #init logger
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)

        #load and check configuration
        self.__configLock = Lock()
        self._config = self._load_config()
        if getattr(self, 'DEFAULT_CONFIG', None) is not None:
            self._check_config(self.DEFAULT_CONFIG)

    def __del__(self):
        """
        Destructor
        """
        self.stop()

    def __file_is_empty(self, path):
        """
        Return True if file is empty
        @param path: path to check
        @return True if file is empty
        """
        return os.path.isfile(path) and not os.path.getsize(path)>0

    def __has_config_file(self):
        """
        Check if module has configuration file
        """
        if getattr(self, 'MODULE_CONFIG_FILE', None) is None:
            return False

        return True

    def _load_config(self):
        """
        Load config file
        @return configuration file content or None if error occured
        """
        #check if module have config file
        if not self.__has_config_file():
            self.logger.info('Module %s has no configuration file configured' % self.__class__.__name__)
            return None

        self.__configLock.acquire(True)
        out = None
        try:
            path = os.path.join(RaspIot.CONFIG_DIR, self.MODULE_CONFIG_FILE)
            self.logger.debug('Loading conf file %s' % path)
            if os.path.exists(path) and not self.__file_is_empty(path):
                f = open(path, 'r')
                raw = f.read()
                f.close()
            else:
                #no conf file yet. Create default one
                f = open(path, 'w')
                default = {}
                raw = json.dumps(default)
                f.write(raw)
                f.close()
                time.sleep(.25) #make sure file is written
            self._config = json.loads(raw)
            out = self._config
        except:
            self.logger.exception('Unable to load config file %s:' % path)
        self.__configLock.release()

        return out
 
    def _save_config(self, config):
        """
        Save config file
        @param config: config to save
        @return configuration file content or None if error occured
        """
        out = None
        force_reload = False

        #check if module have config file
        if not self.__has_config_file():
            self.logger.warning('Module %s has no configuration file configured' % self.__class__.__name__)
            return None

        self.__configLock.acquire(True)
        try:
            path = os.path.join(RaspIot.CONFIG_DIR, self.MODULE_CONFIG_FILE)
            f = open(path, 'w')
            f.write(json.dumps(config))
            f.close()
            force_reload = True
        except:
            self.logger.exception('Unable to write config file %s:' % path)
        self.__configLock.release()

        if force_reload:
            #reload config
            out = self._load_config()

        return out

    def _reload_config(self):
        """
        Reload configuration
        Just an alias to _load_configuration
        """
        self._load_config()

    def _get_config(self):
        """
        Return copy of config dict
        """
        #check if module have config file
        if not self.__has_config_file():
            self.logger.warning('Module %s has no configuration file configured' % self.__class__.__name__)
            return {}

        self.__configLock.acquire(True)
        copy_ = copy.deepcopy(self._config)
        self.__configLock.release()
        return copy_

    def _check_config(self, keys):
        """
        Check config files looking for specified keys.
        If key not found, key is added with specified default value
        @param keys: dict {'key1':'default value1', ...}
        @return nothing, only check configuration file consistency
        """
        config = self._get_config()
        fixed = False
        for key in keys:
            if not config.has_key(key):
                #fix missing key
                config[key] = keys[key]
                fixed = True
        if fixed:
            self.logger.debug('Config file fixed')
            self._save_config(config)

    def _get_unique_id(self):
        """
        Return unique id. Useful to get unique device identifier
        """
        return str(uuid.uuid4())

    def get_module_config(self):
        """
        Return module configuration.
        This function returns all config content except 'devices' entry
        """
        config = self._get_config()

        #remove devices from config
        if config.has_key('devices'):
            del config['devices']

        return config

    def get_module_devices(self):
        """
        Return module devices
        This function returns all devices registered in 'devices' config section
        """
        if self._config is not None and self._config.has_key('devices'):
            return self._config['devices']
        else:
            return {}

    def get_module_commands(self):
        """
        Return available module commands
        @return array of command names
        """
        ms = dir(self)
        for m in ms[:]:
            if not callable(getattr(self, m)):
                #filter module members
                ms.remove(m)
            elif m.startswith('_'):
                #filter protected or private commands
                ms.remove(m)
            elif m in ('send_command', 'send_event', 'start', 'stop', 'push'):
                #filter bus commands
                ms.remove(m)
            elif m in ('event_received'):
                #filter raspiot commands
                ms.remove(m)
            elif m in ('getName', 'isAlive', 'isDaemon', 'is_alive', 'join', 'run', 'setDaemon', 'setName'):
                #filter system commands
                ms.remove(m)

        return ms

    def start(self):
        """
        Start module
        """
        BusClient.start(self)

    def _start(self):
        """
        Post start: called just after module is started
        This function is used to launch processes that requests cpu time and cannot be launched during init
        At this time, all modules are loaded and the system is completely operational
        """
        pass

    def stop(self):
        """
        Stop process
        """
        BusClient.stop(self)
        self._stop()

    def _stop(self):
        """
        Pre stop: called just before module is stopped
        This function is used to stop specific processes like threads
        """
        pass

    def is_module_loaded(self, module):
        """
        Request inventory to check if specified module is loaded or not
        @param module: module name
        @return True if module is loaded, False otherwise
        """
        resp = self.send_command('is_module_loaded', 'inventory', {'module': module})
        if resp['error']:
            self.logger.error('Unable to request inventory')

        return resp['data']




class RaspIotModule(RaspIot):
    """
    Base raspiot class for module
    It implements:
     - device helpers
    """

    def __init__(self, bus, debug_enabled):
        """
        Constructor
        @param bus: MessageBus instance
        @param debug_enabled: flag to set debug level to logger (bool)
        """
        #init raspiot
        RaspIot.__init__(self, bus, debug_enabled)

    def _add_device(self, data):
        """
        Helper function to add device in module configuration file.
        This function auto inject new entry "devices" in configuration file.
        This function appends new device in devices section and add unique id in uuid property
        It also appends 'name' property if not provided
        @param data: device data
        @return device data if process was successful, None otherwise
        """
        config = self._get_config()

        #prepare config file
        if not config.has_key('devices'):
            config['devices'] = {}

        #prepare data
        uuid = self._get_unique_id()
        data['uuid'] = uuid
        if not data.has_key('name'):
            data['name'] = ''
        config['devices'][uuid] = data
        self.logger.debug('config=%s' % config)

        #save data
        if self._save_config(config) is None:
            #error occured
            return None

        return data

    def _delete_device(self, uuid):
        """
        Helper function to remove device from module configuration file
        @param uuid: device identifier
        @return True if device was deleted, False otherwise
        """
        config = self._get_config()

        #check values
        if not config.has_key('devices'):
            self.logger.error('"devices" config file entry doesn\'t exist')
            raise Exception('"devices" config file entry doesn\'t exist')
        if not config['devices'].has_key(uuid):
            self.logger.error('Trying to delete unknown device')
            return False

        #delete device entry
        del config['devices'][uuid]

        #save config
        if self._save_config(config) is None:
            #error occured
            return False

        return True

    def _update_device(self, uuid, data):
        """
        Helper function to update device
        @param uuid: device identifier
        @param data: device data to update
        @return True if device updated, False otherwise
        """
        config = self._get_config()

        #check values
        if not config.has_key('devices'):
            self.logger.error('"devices" config file entry doesn\'t exist')
            raise Exception('"devices" config file entry doesn\'t exist')
        if not config['devices'].has_key(uuid):
            self.logger.error('Trying to update unknown device')

        #check uuid key existence
        if not data.has_key('uuid'):
            data['uuid'] = uuid

        #update data
        config['devices'][uuid] = data

        #save data
        if self._save_config(config) is None:
            #error occured
            return False

        return True

    def _search_device(self, key, value):
        """
        Helper function to search a device based on the property value
        Useful to search a device of course, but can be used to check if a name is not already assigned to a device
        @param key: device property to search on
        @param value: property value
        @return None if key-value wasn't found or the device data if key-value found
        """
        config = self._get_config()

        #check values
        if not config.has_key('devices'):
            self.logger.warning('"devices" config file entry doesn\'t exist')
            #raise Exception('"devices" config file entry doesn\'t exist')
            return None
        if len(config['devices'])==0:
            #no device in dict, return no match
            return None

        #search
        for uuid in config['devices']:
            if config['devices'][uuid].has_key(key) and config['devices'][uuid][key]==value:
                #device found
                return config['devices'][uuid]

        return None

    def _get_device(self, uuid):
        """
        Get device according to specified identifier
        @param uuid: device identifier
        @return None if device not found, device data otherwise
        """
        config = self._get_config()

        #check values
        if not config.has_key('devices'):
            self.logger.error('"devices" config file entry doesn\'t exist')
            #raise Exception('"devices" config file entry doesn\'t exist')
            return None

        if config['devices'].has_key(uuid):
            return config['devices'][uuid]

        return None

    def _get_devices(self):
        """
        Return module devices (alias to get_module_devices function)
        """
        return self.get_module_devices()

    def _get_device_count(self):
        """
        Return number of devices in configuration file"
        @return number of saved devices (int)
        """
        if self._config.has_key('devices'):
            return len(self._config['devices'])
        else:
            return 0




class RaspIotProvider(RaspIotModule):
    """
    Base raspiot class for provider
    It implements:
     - automatic provider registration
     - post function to post data to provider
     - get function to get data from provider
     - get capabilities to get provider capabilities
    """

    def __init__(self, bus, debug_enabled):
        """
        Constructor
        @param bus: MessageBus instance
        @param debug_enabled: flag to set debug level to logger (bool)
        """
        #init raspiot
        RaspIot.__init__(self, bus, debug_enabled)

    def __get_capabilities(self):
        if getattr(self, 'PROVIDER_CAPABILITIES'):
            return self.PROVIDER_CAPABILITIES
        else:
            raise NotImplementedError('PROVIDER_CAPABILITIES must be implemented in provider')

    def post(self, data):
        """
        Post data to provider
        @param data: data to post
        @return True if post is successful
        """
        return True

    def get(self, data):
        """
        Get data from provider
        @param data: data to post
        @return dict of infos
        """
        return {}
