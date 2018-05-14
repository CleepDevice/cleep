#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import json
from bus import BusClient
from threading import Lock, Thread, Timer
from utils import CommandError, MissingParameter, InvalidParameter, ResourceNotAvailable
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

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor.

        Args:
            bootstrap (dict): bootstrap objects.
            debug_enabled (bool): flag to set debug level to logger.
        """
        #init bus
        BusClient.__init__(self, bootstrap)

        #init logger
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)
        self.debug_enabled = debug_enabled

        #members
        self.events_factory = bootstrap[u'events_factory']
        self.cleep_filesystem = bootstrap[u'cleep_filesystem']

        #load and check configuration
        self.__configLock = Lock()
        self._config = self._load_config()
        if getattr(self, u'DEFAULT_CONFIG', None) is not None:
            self._check_config(self.DEFAULT_CONFIG)

    def __del__(self):
        """
        Destructor
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
                #TODO f = self.cleep_filesystem.open(path, u'r')
                f = open(path, u'r')
                raw = f.read()
                #self.cleep_filesystem.close(f)
                f.close()
            else:
                #no conf file yet. Create default one
                #f = self.cleep_filesystem.open(path, u'w')
                f = open(path, u'w')
                default = {}
                raw = json.dumps(default)
                f.write(raw)
                #self.cleep_filesystem.close(f)
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
            self.logger.debug(u'Module %s has no configuration file configured' % self.__class__.__name__)
            return None

        self.__configLock.acquire(True)
        try:
            path = os.path.join(RaspIot.CONFIG_DIR, self.MODULE_CONFIG_FILE)
            #f = self.cleep_filesystem.open(path, u'w')
            f = open(path, u'w')
            f.write(json.dumps(config))
            #self.cleep_filesystem.close(f)
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
            self.logger.debug(u'Module %s has no configuration file configured' % self.__class__.__name__)
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

    def _get_event(self, event_name):
        """
        Get event name

        Args:
            event_name (string): event name

        Return:
            Event instance
        """
        return self.events_factory.get_event_instance(event_name)

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
        #start thread (non blocking)
        BusClient.start(self)

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
        try:
            resp = self.send_command(u'is_module_loaded', u'inventory', {u'module': module})
            if resp[u'error']:
                self.logger.error(u'Unable to request inventory')
                return False

            return resp[u'data']

        except:
            self.logger.exception(u'Unable to know if module is loaded or not:')
            return False

    def _event_received(self, event):
        """
        Event is received on bus

        Args:
            event (dict): event infos (event, params)
        """
        if hasattr(self, u'event_received'):
            #function implemented in instance, execute it
            event_received = getattr(self, u'event_received')
            if event_received is not None:
                event_received(event)





class RaspIotModule(RaspIot):
    """
    Base raspiot class for module
    It implements:
     - device helpers
    """
    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor.

        Args:
            bootstrap (dict): bootstrap objects.
            debug_enabled (bool): flag to set debug level to logger.
        """
        #init raspiot
        RaspIot.__init__(self, bootstrap, debug_enabled)

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





class RaspIotResource(RaspIotModule):
    """
    Base raspiot class for specific resource (for example audio)
    It implements:
     - resource lock/release
     - resource demand request
    """

    RESOURCE_TIMEOUT = 5.0

    def __init__(self, resources, bootstrap, debug_enabled):
        """
        Constructor.

        Args:
            resources (dict): dict of handled resources {'resource name': <delay to reacquire>, ...}
            bootstrap (dict): bootstrap objects.
            debug_enabled (bool): flag to set debug level to logger.
        """
        #init raspiot
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #members
        if not isinstance(resources, dict):
            raise InvalidParameter('Parameter resources is invalid: must be a list not a %s' % str(type(resources)))
        self.delays = resources
        self.resources = {}
        for resource in resources.keys():
            self.resources[resource] = {
                u'in_use': None,
                u'waiting': False,
                u'was_in_use': False
            }
        self.__module = self.__class__.__name__.lower()
        self.resource_released_event = self._get_event('system.resource.released')
        self.resource_acquired_event = self._get_event('system.resource.acquired')

    def acquire_resource(self, resource, extra=None):
        """
        Acquire specified resource

        Args:
            resource (string): resource name
            extra (any): extra parameters

        Return:
            bool: True if resource acquired
        """
        #check resource
        if resource not in self.resources.keys():
            #unsupported resource specified
            raise Exception(u'Specified resource %s is not supported by this module' % resource)

        #supported resource, check if request not already running
        if self.resources[resource][u'waiting']:
            #acquisition already requested
            self.logger.debug(u'Module %s is already acquiring resource %s' % (self.__module, resource))
            return False

        #no acquisition in progress, check if resource already acquired
        if self.resources[resource][u'in_use'] and self.resources[resource][u'in_use']==self.__module:
            #resource already acquired by this module, do nothing
            self.logger.debug(u'Resource %s already acquired by %s, do nothing' % (resource, self.__module))
            return False

        elif self.resources[resource][u'in_use'] and self.resources[resource][u'in_use']!=self.__module:
            #resource is in use, request for the need of it
            self.logger.debug(u'Send command need_resource for resource %s to resource owner %s' % (resource, self.resources[resource][u'in_use']))
            resp = self.send_command(u'need_resource', self.resources[resource][u'in_use'], {u'resource':resource})
            #self.logger.debug('need_resource resp: %s' % resp)

            #check resp
            if resp[u'error'] or not resp[u'data']:
                self.logger.warning('Unable to claim resource %s to module %s' % (resource, self.resources[resource][u'in_use']))
                raise ResourceNotAvailable(resource)

            #resource released, acquire it now
            if self._acquire_resource(resource, extra):
                #resource acquired, set resource stuff
                self.logger.debug(u'Resource %s acquired successfully' % resource)
                self.resources[resource][u'in_use'] = self.__module
                self.resources[resource][u'waiting'] = False

                #and send event
                self.resource_acquired_event.send({u'resource': resource, u'module':self.__module})

            else:
                #resource not acquired
                self.logger.warning(u'Resource %s not acquired' % resource)
                return False

        else:
            #acquire resource
            self.logger.debug(u'Resource %s is free, acquire it' % resource)
            if self._acquire_resource(resource, extra):
                #resource acquired, set resource stuff
                self.resources[resource][u'in_use'] = self.__module
                self.resources[resource][u'waiting'] = False

                #and send event
                self.resource_acquired_event.send({u'resource': resource, u'module':self.__module})

            else:
                #resource not acquired
                self.logger.warning(u'Resource %s not acquired' % resource)
                return False

        return True

    def _acquire_resource(self, resource, extra=None):
        """
        Acquire resource

        Args:
            resource (string): resource name
            extra (any): extra parameters

        Return:
            bool: True if resource really acquired
        """
        raise NotImplemented(u'Method release_resource must be implemented')

    def release_resource(self, resource, extra=None):
        """
        Release resource

        Args:
            resource (string): resource name
            extra (any): extra parameters

        Return:
            bool: True if resource released
        """
        self.logger.debug('release_resource')
        #release resource in module
        if not self._release_resource(resource, extra):
            #unable to release resource
            self.logger.Debug(u'Unable to release resource %s' % resource)
            return False

        #module explicitely release resource, reset reacquisition flag
        self.resources[resource][u'was_in_use'] = False
        self.resources[resource][u'in_use'] = None

        #and send released resource event
        self.resource_released_event.send({u'resource': resource, u'module':self.__module})

        return True

    def _release_resource(self, resource, extra=None):
        """
        Release resource

        Args:
            resource (string): resource name
            extra (any): extra parameters

        Return:
            bool: True if resource released
        """
        raise NotImplemented(u'Method release_resource must be implemented')

    def need_resource(self, resource):
        """
        Request for the need of a resource (internal use only)

        Args:
            resource (string): resource name
        """
        #self.logger.debug('need_resource: self.resources=%s' % self.resources)
        if self.resources[resource][u'in_use']==self.__module:
            #release resource owned by this module
            if not self.release_resource(resource):
                #unable to release resource
                self.logger.warning('Unable to release resource %s while another module needs it' % resource)
                return False

            #flag used to reacquire resource automatically after other module releases it
            self.resources[resource][u'was_in_use'] = True

            return True

        else:
            #resource is not in use by this module
            #self.logger.debug(u'Resource %s is not used by this module' % resource)
            pass

            return False

    def _event_received(self, event):
        """
        Event received (overwrite default behaviour)

        Args:
            event (dict): event params
        """
        if event[u'event']==u'system.resource.acquired' and event[u'params'][u'resource'] in self.resources.keys():
            #resource is acquired
            self.resources[event[u'params'][u'resource']][u'in_use'] = event[u'params'][u'module']
            self.resources[event[u'params'][u'resource']][u'waiting'] = False
            #self.logger.debug(u'resources: %s' % self.resources)

        elif event[u'event']==u'system.resource.released' and event[u'params'][u'resource'] in self.resources.keys():
            #resource is released
            self.resources[event[u'params'][u'resource']][u'in_use'] = None

            if self.resources[event[u'params'][u'resource']][u'was_in_use']:
                #reacquire resource because it was used before
                self.logger.debug(u'Module %s will reacquire resource %s in %d seconds' % (self.__module, event[u'params'][u'resource'], self.delays[event[u'params'][u'resource']]))
                self.resources[event[u'params'][u'resource']][u'was_in_use'] = False

                #reacquire resource after delay
                tempo = Timer(self.delays[event[u'params'][u'resource']], self.acquire_resource, [event[u'params'][u'resource']])
                tempo.start()

            #self.logger.debug(u'resources: %s' % self.resources)

        #call parent method
        RaspIotModule._event_received(self, event)

 



class RaspIotRenderer(RaspIotModule):
    """
    Base raspiot class for renderer.
    It implements:
     - automatic renderer registration
     - post function to post data to renderer
    """
    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor.

        Args:
            bootstrap (dict): bootstrap objects.
            debug_enabled (bool): flag to set debug level to logger.
        """
        #init raspiot
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #members
        self.profiles_types = []

    def get_module_renderers(self):
        """
        Register internally available profiles and return it.
        This method is called by inventory at startup
        """
        if getattr(self, u'RENDERER_PROFILES', None) is None:
            raise Exception(u'RENDERER_PROFILES is not defined in %s' % self.__class__.__name__)
        if getattr(self, u'RENDERER_TYPE', None) is None:
            raise Exception(u'RENDERER_TYPE is not defined in %s' % self.__class__.__name__)

        #cache profile types as string
        for profile in self.RENDERER_PROFILES:
            self.profiles_types.append(profile.__name__)

        return {
            u'type': self.RENDERER_TYPE,
            u'profiles': self.RENDERER_PROFILES
        }

    def render(self, profile):
        """
        Render profile

        Args:
            profile (RendererProfile): profile to render

        Returns:
            bool: True if post is successful.

        Raises:
            MissingParameter, InvalidParameter
        """
        #check profile type
        if profile.__class__.__name__ not in self.profiles_types:
            raise InvalidParameter(u'Profile "%s" is not supported in this renderer' % profile.__class__.__name__)

        #call implementation
        return self._render(profile)

    def _render(self, profile):
        """
        Fake render method
        """
        pass
