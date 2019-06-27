#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import json
from bus import BusClient
from threading import Lock, Thread, Timer
from utils import CommandError, MissingParameter, InvalidParameter, ResourceNotAvailable, ExecutionStep
import time
import copy
import uuid
from libs.internals.crashreport import CrashReport
from libs.drivers.driver import Driver
import re


__all__ = [u'RaspIot', u'RaspIotRenderer', u'RaspIotModule']


class RaspIot(BusClient):
    """
    Base raspiot class
    It implements :
     - configuration helpers
     - message bus access
     - logger with log level configured
     - custom crash report
     - driver registration
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
        self.__execution_step = bootstrap[u'execution_step']
        self.events_broker = bootstrap[u'events_broker']
        self.cleep_filesystem = bootstrap[u'cleep_filesystem']
        self.drivers = bootstrap[u'drivers']

        #load and check configuration
        self.__configLock = Lock()
        self.__config = self.__load_config()
        if getattr(self, u'DEFAULT_CONFIG', None) is not None:
            self.__check_config(self.DEFAULT_CONFIG)

        #crash report
        if getattr(self, u'MODULE_SENTRY_DSN', None) is not None:
            #set custom crash report instance
            self.logger.debug(u'Sentry DSN found in module, create dedicated crash report for this module.')
            libs_version = bootstrap[u'crash_report'].libs_version
            libs_version[self.__class__.__name__] = self.MODULE_VERSION
            product = bootstrap[u'crash_report'].product
            product_version = bootstrap[u'crash_report'].product_version
            bootstrap[u'crash_report'].disabled = bootstrap[u'crash_report'].is_enabled()
            self.crash_report = CrashReport(self.MODULE_SENTRY_DSN, product, product_version, libs_version, False, disabled)

        elif getattr(self, u'MODULE_CORE', None) is True:
            #set default crash report for core module
            self.logger.debug(u'Crash report enabled for core')
            self.crash_report = bootstrap[u'crash_report']

        else:
            #no crash report specified, set dummy one (no dsn provided)
            if not bootstrap[u'test_mode']:
                self.logger.warning(u'No Sentry DSN found, crash report disabled')
            self.crash_report = CrashReport(None, u'CleepDevice', u'0.0.0', {}, False, True)

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

    def _has_config_file(self):
        """
        Check if module has configuration file.

        Returns:
            bool: True if module has config file, False otherwise.
        """
        if getattr(self, u'MODULE_CONFIG_FILE', None) is None:
            return False

        return True

    def __load_config(self):
        """
        Load config file.

        Returns:
            dict: configuration file content or None if error occured.
        """
        #check if module have config file
        if not self._has_config_file():
            self.logger.debug(u'Module %s has no configuration file configured' % self.__class__.__name__)
            return None

        self.__configLock.acquire(True)
        out = None
        try:
            path = os.path.join(self.CONFIG_DIR, self.MODULE_CONFIG_FILE)
            self.logger.debug(u'Loading conf file %s' % path)
            if os.path.exists(path) and not self.__file_is_empty(path):
                out = self.cleep_filesystem.read_json(path)
                if out is None:
                    #should not happen but handle it
                    out = {}
            else:
                #no conf file yet. Create default one
                out = {}
                self.cleep_filesystem.write_json(path, out)
                time.sleep(0.25)
                
        except:
            self.logger.exception(u'Unable to load config file %s:' % path)
        self.__configLock.release()

        return out
 
    def __save_config(self, config):
        """
        Save config file.

        Args:
            config (dict): config to save

        Returns:
            bool: False if error occured, True otherwise
        """
        out = False
        force_reload = False

        #check if module have config file
        if not self._has_config_file():
            self.logger.debug(u'Module %s has no configuration file configured' % self.__class__.__name__)
            return False

        #get lock
        self.__configLock.acquire(True)

        try:
            path = os.path.join(self.CONFIG_DIR, self.MODULE_CONFIG_FILE)
            self.cleep_filesystem.write_json(path, config)
            self.__config = config
            out = True

        except:
            self.logger.exception(u'Unable to write config file %s:' % path)

        #release lock
        self.__configLock.release()

        return out

    def _update_config(self, config):
        """
        Secured config update: update specified fields, do not completely overwrite content

        Args:
            config (dict): new config to update

        Returns:
            bool: False if update failed, True otherwise

        Raises:
            InvalidParameter if input params are invalid
        """
        #check params
        if not isinstance(config, dict):
            raise InvalidParameter(u'Parameter config must be a dict')

        #get lock
        self.__configLock.acquire(True)

        #keep copy of old config
        old_config = copy.deepcopy(self.__config)

        #update config
        self.__config.update(config)

        #release lock
        self.__configLock.release()

        #save new config
        if not self.__save_config(self.__config):
            #revert changes
            self.__configLock.acquire(True)
            self.__config = old_config
            self.__configLock.release()
            
            return False

        return True

    def _get_config(self):
        """
        Return copy of config dict.

        Returns:
            dict: config file content (copy).
        """
        #check if module have config file
        if not self._has_config_file():
            self.logger.debug(u'Module %s has no configuration file configured' % self.__class__.__name__)
            return {}

        #get lock
        self.__configLock.acquire(True)

        #make deep copy of structure
        copy_ = copy.deepcopy(self.__config)

        #release lock
        self.__configLock.release()

        return copy_

    def _get_config_field(self, field):
        """
        Return specified config field value

        Args:
            field (string): field name

        Returns:
            any: returns field value

        Raises:
            Exception if field is unknown
        """
        try:
            return copy.deepcopy(self.__config[field])

        except KeyError:
            raise Exception(u'Unknown config field "%s"' % field)

    def _has_config_field(self, field):
        """
        Check if config has specified field

        Args:
            field (string): field to check

        Returns:
            bool: True if field exists
        """
        return field in self.__config if self.__config is not None else False

    def _set_config_field(self, field, value):
        """
        Convenience function to update config field value
        Unlike _update_config function, _set_config_field check parameter existance in config

        Args:
            field (string): field name
            value (any): field value to set

        Returns:
            bool: result of _update_config function
        """
        #check params
        if field not in self.__config:
            raise InvalidParameter(u'Parameter "%s" doesn\'t exist in config' % field)

        return self._update_config({field: value})

    def __check_config(self, keys):
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
            if key not in config:
                #fix missing key
                self.logger.debug('Add missing key "%s" in config file' % key)
                config[key] = keys[key]
                fixed = True
        if fixed:
            self.logger.debug(u'Config file fixed')
            self.__save_config(config)

    def _register_driver(self, driver):
        """
        Register driver

        Raises:
            InvalidParameter: if driver has invalid base class
        """
        if self.__execution_step.step!=ExecutionStep.INIT:
            self.logger.warn(u'Driver registration must be done during INIT step (in application constructor)')
        #check driver
        if not isinstance(driver, Driver):
            raise InvalidParameter(u'Driver must be instance of base Driver class')

        self.drivers.register(driver)

    def _get_drivers(self, driver_type):
        """
        Returns drivers for specified type

        Args:
            driver_type (string): see Driver.DRIVER_XXX for values

        Returns:
            dict: drivers
        """
        return self.drivers.get_drivers(driver_type)

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

        Returns:
            Event: Event instance
        """
        return self.events_broker.get_event_instance(event_name)

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
        if self.__config is not None and self.__config.has_key(u'devices'):
            return self.__config[u'devices']
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
            self.crash_report.report_exception({
                u'message': u'Unable to know if module is loaded or not:',
                u'module': module
            })
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





class RaspIotRpcWrapper(RaspIot):
    """
    Base raspiot class for RPC request wrapping
    """
    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects.
            debug_enabled (bool): flag to set debug level to logger.
        """
        #init raspiot
        RaspIot.__init__(self, bootstrap, debug_enabled)
    
    def wrap_request(self, route, request):
        """
        Function called when web request from / in POST is called
        By default this access point is not supported by Cleep but it can be wrapped here

        Args:
            request (bottle.request): web server bottle request content. See doc https://bottlepy.org/docs/dev/tutorial.html#request-data

        Returns:
            returns any data
        """
        raise NotImplementedError('wrap_request function must be implemented in "%s"' % self.__class__.__name__)





class RaspIotModule(RaspIot):
    """
    Base raspiot class for module
    It implements:
     - device helpers
    """
    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects.
            debug_enabled (bool): flag to set debug level to logger.
        """
        #init raspiot
        RaspIot.__init__(self, bootstrap, debug_enabled)

        #add devices section if missing
        if self._has_config_file() and not self._has_config_field(u'devices'):
            self._update_config({
                u'devices': {}
            })

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
        #prepare config file
        devices = {}
        if self._has_config_field(u'devices'):
            devices = self._get_config_field(u'devices')

        #prepare data
        uuid = self._get_unique_id()
        data['uuid'] = uuid
        if u'name' not in data:
            data[u'name'] = u'No name'
        devices[uuid] = data
        self.logger.debug(u'devices: %s' % devices)

        #save data
        if not self._update_config({u'devices': devices}):
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
        #check values
        if not self._has_config_field(u'devices'):
            self.logger.error(u'"devices" config file entry doesn\'t exist')
            raise Exception(u'"devices" config file entry doesn\'t exist')
        devices = self._get_config_field(u'devices')
        if uuid not in devices:
            self.logger.error(u'Trying to delete unknown device')
            return False

        #delete device entry
        del devices[uuid]

        #save config
        return self._set_config_field(u'devices', devices)

    def _update_device(self, uuid, data):
        """
        Helper function to update device.

        Args:
            uuid (string): device identifier.
            data (dict): device data to update.

        Returns:
            bool: True if device updated, False otherwise.
        """
        #check values
        if not self._has_config_field(u'devices'):
            self.logger.error(u'"devices" config file entry doesn\'t exist')
            raise Exception(u'"devices" config file entry doesn\'t exist')
        devices = self._get_config_field(u'devices')
        if uuid not in devices:
            self.logger.debug(u'Trying to update unknown device "%s"' % uuid)
            return False

        #check uuid key existence
        if not data.has_key(u'uuid'):
            data[u'uuid'] = uuid

        #update data
        devices[uuid] = data

        #save data
        return self._set_config_field(u'devices', devices)

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
        #check values
        if not self._has_config_field(u'devices'):
            self.logger.error(u'"devices" config file entry doesn\'t exist')
            return None
        devices = self._get_config_field(u'devices')
        if len(devices)==0:
            #no device in dict, return no match
            return None

        #search
        for uuid in devices:
            if key in devices[uuid] and devices[uuid][key]==value:
                #device found
                return devices[uuid]

        return None

    def _search_devices(self, key, value):
        """
        Helper function to search a device based on the property value.
        Useful to search a device of course, but can be used to check if a name is not already assigned to a device.

        Args:
            key (string): device property to search on.
            value (any): property value.

        Returns
            dict: the device data if key-value found, or None otherwise.
        """
        output = []

        #check values
        if not self._has_config_field(u'devices'):
            self.logger.warning(u'"devices" config file entry doesn\'t exist')
            return output
        devices = self._get_config_field(u'devices')
        if len(devices)==0:
            #no device in dict, return no match
            return output

        #search
        for uuid in devices:
            if key in devices[uuid] and devices[uuid][key]==value:
                #device found
                output.append(devices[uuid])

        return output

    def _get_device(self, uuid):
        """
        Get device according to specified identifier.

        Args:
            uuid (string): device identifier.

        Returns:
            dict: None if device not found, device data otherwise.
        """
        #check values
        if not self._has_config_field(u'devices'):
            self.logger.error(u'"devices" config file entry doesn\'t exist')
            return None

        devices = self._get_config_field(u'devices')
        if uuid in devices:
            return devices[uuid]

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
        if self._has_config_field(u'devices'):
            return len(self._get_config_field(u'devices'))
        else:
            return 0



class RaspIotResources(RaspIotModule):
    """
    Base raspiot class to handle critical resources such as audio capture and make sure
    loaded application using the same resource are not using it at the same time.
    """

    #module resources: list of resource identifer. The identifier is important and must be unique
    #                  The identifier can be for example the physical audio device name::
    #
    #   {
    #       resource_name (string): xxx.xxx (ie "audio.playback" for audio)
    #       [
    #           {
    #               permanent (bool): acquire permanently the resource
    #           },
    #           ...
    #       ],
    #       ...
    #   }
    #
    MODULE_RESOURCES = {}

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        #init raspiot
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #members
        self.__critical_resources = bootstrap[u'critical_resources']

        #register resources
        self.__register_resources()

    def __register_resources(self):
        """
        Register module resources
        """
        for resource_name, resource in self.MODULE_RESOURCES.items():
            self.__critical_resources.register_resource(
                self.__class__.__name__,
                resource_name,
                self._resource_acquired,
                self._resource_needs_to_be_released,
                resource[u'permanent'] if u'permanent' in resource else False
            )

    def _resource_acquired(self, resource_name):
        """
        Function called when resource is acquired.
        
        Note:
            Must be implemented!

        Args:
            resource_name (string): acquired resource name

        Raises:
            NotImplementedError: if function is not implemented
        """
        raise NotImplementedError(u'Method "_resource_acquired" must be implemented in "%s"' % self.__class__.__name__)

    def _resource_needs_to_be_released(self, resource_name):
        """
        Function called when resource is acquired by other module and needs to be released.

        Note:
            Must be implemented!

        Args:
            resource_name (string): acquired resource name

        Raises:
            NotImplementedError: if function is not implemented
        """
        raise NotImplementedError(u'Method "_resource_needs_to_be_released" must be implemented in "%s"' % self.__class__.__name__)

    def _need_resource(self, resource_name):
        """
        Need to acquire specified resource. The resource is really acquired after _resource_acquired
        function execution. A delay could occurs if resource is not available at this time.
        This function call does not guarantee to have resource access if current acquirer still needs
        to use it.

        Args:
            resource_name (string): Existing resource name (see resources core directory content)
        """
        self.__critical_resources.acquire_resource(self.__class__.__name__, resource_name)

    def _release_resource(self, resource_name):
        """
        Release specified resource

        Args:
            resource_name (string): Existing resource name (see resources core directory content)
        """
        return self.__critical_resources.release_resource(self.__class__.__name__, resource_name)

    def _get_resources(self):
        """
        Return loaded resources with extra data

        Returns:
            list: list of available resources
        """
        return self.__critical_resources.get_resources()

 



class RaspIotRenderer(RaspIotModule):
    """
    Base raspiot class for renderer.
    Don't forget to also inherit from other base class (RaspIotModule, RaspIotResources)

    Note:
        It implements:
            - automatic renderer registration
            - render function to render received profile
    """
    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger.
        """
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #init logger
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)
        self.debug_enabled = debug_enabled

        #members
        self.profiles_types = []

    def get_renderer_config(self):
        """
        Register internally available profiles and return it.
        This method is called by inventory at startup

        Raises:
            Exception: if RENDERER_PROFILES member is not defined
        """
        if getattr(self, u'RENDERER_PROFILES', None) is None:
            raise Exception(u'RENDERER_PROFILES is not defined in %s' % self.__class__.__name__)

        #cache profile types as string
        for profile in self.RENDERER_PROFILES:
            self.profiles_types.append(profile.__name__)

        return {
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
        try:
            self._render(profile)
            return True
        except:
            self.logger.exception('Rendering profile "%s" failed:' % profile.__class__.__name__ if profile else None)
            return False

    def _render(self, profile):
        """
        Fake render method

        Raises:
            NotImplementedError: if not implemented
        """
        raise NotImplementedError(u'_render function must be implemented in "%s"' % self.__class__.__name__)
        

