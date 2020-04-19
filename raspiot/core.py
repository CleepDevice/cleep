#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import json
from raspiot.bus import BusClient
from threading import Lock, Thread, Timer
from raspiot.exception import CommandError, MissingParameter, InvalidParameter, ResourceNotAvailable
from raspiot.common import ExecutionStep, CORE_MODULES
import time
import copy
import uuid
from raspiot.libs.internals.crashreport import CrashReport
from raspiot.libs.drivers.driver import Driver
from mock import Mock


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
        # init bus
        BusClient.__init__(self, bootstrap)

        # init logger
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)
        self.debug_enabled = debug_enabled

        # members
        self.__execution_step = bootstrap[u'execution_step']
        self.events_broker = bootstrap[u'events_broker']
        self.cleep_filesystem = bootstrap[u'cleep_filesystem']
        self.drivers = bootstrap[u'drivers']

        # load and check configuration
        self.__configLock = Lock()
        self.__config = self.__load_config()
        if getattr(self, u'DEFAULT_CONFIG', None) is not None:
            self.__check_config(self.DEFAULT_CONFIG)

        # crash report
        if getattr(self, u'MODULE_SENTRY_DSN', None) is not None and self.MODULE_SENTRY_DSN:
            # create custom crash report instance for this module with specified DSN
            self.logger.debug(u'Sentry DSN found in module, create dedicated crash report for this module.')

            # get libs from main crash report instance and append current module version
            infos = bootstrap[u'crash_report'].get_infos()
            infos[u'libsversion'][self.__class__.__name__.lower()] = self.MODULE_VERSION if hasattr(self, u'MODULE_VERSION') else '0.0.0'
            
            self.crash_report = CrashReport(
                self.MODULE_SENTRY_DSN,
                infos['product'],
                infos['productversion'],
                infos['libsversion'],
                disabled_by_system=bootstrap[u'crash_report'].is_enabled()
            )

        elif self._get_module_name() in CORE_MODULES or self._get_module_name()==u'inventory':
            # set default crash report for core module
            self.logger.debug(u'Crash report enabled for core module')
            self.crash_report = bootstrap[u'crash_report']

            # add core module version to libs version
            self.crash_report.add_module_version(self.__class__.__name__, getattr(self, u'MODULE_VERSION', '0.0.0'))

        elif bootstrap[u'test_mode']: # pragma: no cover
            self.logger.debug('Test mode: do not set crash report to module')

        else:
            # no crash report specified, set dummy one (no dsn provided)
            self.logger.debug(u'Initialize empty crashreport')
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
            dict: configuration file content
        """
        # check if module have config file
        if not self._has_config_file():
            self.logger.debug(u'Module %s has no configuration file configured' % self.__class__.__name__)
            return None

        out = {}
        self.__configLock.acquire(True)
        try:
            path = os.path.join(self.CONFIG_DIR, self.MODULE_CONFIG_FILE)
            self.logger.debug(u'Loading conf file from path "%s"' % os.path.abspath(path))
            if os.path.exists(path) and not self.__file_is_empty(path):
                out = self.cleep_filesystem.read_json(path)
                if out is None: # pragma: no cover
                    # should not happen but handle it
                    out = {}
            else:
                # no conf file yet. Create default one
                self.logger.debug(u'No config file found, create default one')
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

        # get lock
        self.__configLock.acquire(True)

        try:
            path = os.path.join(self.CONFIG_DIR, self.MODULE_CONFIG_FILE)
            self.cleep_filesystem.write_json(path, config)
            self.__config = config
            out = True

        except:
            self.logger.exception(u'Unable to write config file %s:' % path)

        # release lock
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
        # check params
        if not isinstance(config, dict):
            raise InvalidParameter(u'Parameter "config" must be a dict')
        if not self._has_config_file():
            raise Exception(u'Module %s has no configuration file configured' % self.__class__.__name__)

        # get lock
        self.__configLock.acquire(True)

        # keep copy of old config
        old_config = copy.deepcopy(self.__config)

        # update config
        self.__config.update(config)

        # release lock
        self.__configLock.release()

        # save new config
        if not self.__save_config(self.__config):
            # revert changes
            self.__configLock.acquire(True)
            self.__config = old_config
            self.__configLock.release()
            
            return False

        return True

    def _get_config(self):
        """
        Return deep copy of config dict.

        Returns:
            dict: config file content
        """
        # check if module have config file
        if not self._has_config_file():
            self.logger.debug(u'Module %s has no configuration file configured' % self.__class__.__name__)
            return {}

        # get lock
        self.__configLock.acquire(True)

        # make deep copy of structure
        copy_ = copy.deepcopy(self.__config)

        # release lock
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
        # check params
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
    
        # check config is a dict, only supported format for config file
        if not isinstance(config, dict):
            self.logger.warning(u'Invalid configuration file content, only dict content are supported. Reset its content.')
            config = {}

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
        # check driver
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
        # change current logger debug level
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        # update debug flag
        self.debug_enabled = debug

    def _get_module_name(self):
        """
        Return module name

        Returns:
            string: module name
        """
        return self.__class__.__name__.lower()

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
        return self._get_config()

    def get_module_commands(self):
        """
        Return available module commands.
        
        Returns:
            list: list of command names.
        """
        ms = dir(self)
        for m in ms[:]:
            if not callable(getattr(self, m)):
                # filter module members
                ms.remove(m)
            elif m.startswith('_'):
                # filter protected or private commands
                ms.remove(m)
            elif m in ( u'send_command', u'send_event', u'send_external_event',
                        u'get_module_commands', u'get_module_commands', u'get_module_config',
                        u'is_debug_enabled', u'set_debug', u'is_module_loaded',
                        u'start', u'stop', u'push', u'event_received', ):
                # filter bus commands
                ms.remove(m)
            elif m in (u'getName', u'isAlive', u'isDaemon', u'is_alive', u'join', u'run', u'setDaemon', u'setName'):
                # filter Thread functions
                ms.remove(m)
            elif isinstance(getattr(self, m, None), Mock):
                # only for unittest
                ms.remove(m)

        return ms

    def start(self):
        """
        Start module.
        """
        # start thread (non blocking)
        BusClient.start(self)

    def stop(self):
        """
        Stop process.
        """
        BusClient.stop(self)
        self._stop()

    def _stop(self): # pragma: no cover
        """
        Pre stop: called just before module is stopped.

        Note:
            Implement this function to stop specific processes like threads during stop process
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
            event (dict): MessageRequest as dict with event values::

                {
                    event (string): event name
                    params (dict): event parameters
                    device_id (string): device that emits event or None
                    sender (string): event sender
                    startup (bool): startup event flag
                }

        """
        self.event_received(event)

    def event_received(self, event): # pragma: no cover
        """
        Event message received

        Note:
            Implement this function to handle event on your module

        Args:
            event (dict): MessageRequest as dict with event values::

                {
                    event (string): event name
                    params (dict): event parameters
                    device_id (string): device that emits event or None
                    sender (string): event sender
                    startup (bool): startup event flag
                }

        """
        pass





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

    def _wrap_request(self, route, request): # pragma: no cover
        """
        Function called when web request from / in POST is called
        By default this access point is not supported by Cleep but it can be wrapped here

        Note:
            Must be implemented!

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
        # init raspiot
        RaspIot.__init__(self, bootstrap, debug_enabled)

        # add devices section if missing
        if self._has_config_file() and not self._has_config_field(u'devices'):
            self._update_config({
                u'devices': {}
            })

        # events
        self.delete_device_event = None
        try:
            self.delete_device_event = self.events_broker.get_event_instance(u'system.device.delete')
        except:
            pass

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
        # check parameters
        if not isinstance(data, dict):
            raise InvalidParameter(u'Parameter "data" must be a dict')

        # prepare config file
        devices = {}
        if self._has_config_field(u'devices'):
            devices = self._get_config_field(u'devices')

        # prepare data
        uuid = self._get_unique_id()
        data['uuid'] = uuid
        if u'name' not in data:
            data[u'name'] = u'noname'
        devices[uuid] = data
        self.logger.trace(u'devices: %s' % devices)

        # save data
        if not self._update_config({u'devices': devices}):
            # error occured
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
        # check values
        devices = self._get_config_field(u'devices')
        if uuid not in devices:
            self.logger.error(u'Trying to delete unknown device')
            return False

        # delete device entry
        del devices[uuid]

        # save config
        conf_result = self._set_config_field(u'devices', devices)

        # send device deleted event
        if conf_result and self.delete_device_event:
            self.delete_device_event.send(device_id=uuid)

        return conf_result

    def _update_device(self, uuid, data):
        """
        Helper function to update device.
        This function only update fields that already exists in device data. Other new fields are dropped.

        Args:
            uuid (string): device identifier.
            data (dict): device data to update.

        Returns:
            bool: True if device updated, False otherwise.
        """
        # check parameters
        if not isinstance(data, dict):
            raise InvalidParameter(u'Parameter "data" must be a dict')

        data_ = copy.deepcopy(data)

        # check values
        devices = self._get_config_field(u'devices')
        if uuid not in devices:
            self.logger.warn(u'Trying to update unknown device "%s"' % uuid)
            return False

        # always force uuid to make sure data is always valid
        data_[u'uuid'] = uuid

        # update data
        devices[uuid].update({k:v for k,v in data_.iteritems() if k in devices[uuid].keys()})

        # save data
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
        devices = self._get_config_field(u'devices')
        if len(devices)==0:
            # no device in dict, return no match
            return None

        # search
        for uuid in devices:
            if key in devices[uuid] and devices[uuid][key]==value:
                # device found
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
            list: list of devices which key-value matches, empty list if nothing found
        """
        output = []

        # check values
        devices = self._get_config_field(u'devices')
        if len(devices)==0:
            # no device in dict, return no match
            return output

        # search
        for uuid in devices:
            if key in devices[uuid] and devices[uuid][key]==value:
                # device found
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
        if not self._has_config_file():
            return None

        devices = self._get_config_field(u'devices')
        return devices[uuid] if uuid in devices else None

    def get_module_devices(self):
        """
        Returns module devices.

        Returns:
            dict: all devices registered in 'devices' config section::

                {
                    device uuid (string): device data (dict),
                    ...
                }

        """
        return self._get_config()[u'devices'] if self._has_config_file() else {}

    def _get_devices(self):
        """
        Return module devices (get_module_devices alias).

        Returns:
            dict: all devices registered in 'devices' config section::

                {
                    device uuid (string): device data (dict),
                    ...
                }

        """
        return self.get_module_devices()

    def _get_device_count(self):
        """
        Return number of devices registered in module.

        Returns:
            int: number of saved devices.
        """
        return len(self._get_config_field(u'devices')) if self._has_config_file() else 0

    def get_module_config(self):
        """
        Returns module configuration.
        
        Returns:
            dict: all config content except 'devices' entry.
        """
        config = self._get_config()

        # remove devices from config
        if config.has_key(u'devices'):
            del config[u'devices']

        return config

    def get_module_commands(self):
        """
        Return available module commands.
        
        Returns:
            list: list of command names.
        """
        ms = RaspIot.get_module_commands(self)

        ms.remove('get_module_devices')

        return ms





class RaspIotResources(RaspIotModule):
    """
    Base raspiot class to handle critical resources such as audio capture and make sure
    loaded application using the same resource are not using it at the same time.
    It implements a mechanism of acquire/release and an auto acquisition (or permanent).
    """

    # module resources:
    # list of resource identifer. The identifier is important and must be unique
    # The identifier can be for example the physical audio device name::
    #
    #   {
    #       resource_name (string): xxx.xxx (eg "audio.playback" for audio)
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
        # init raspiot
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        # members
        self.__critical_resources = bootstrap[u'critical_resources']

        # register resources
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
    Don't forget to also implements methods from other base class (RaspIotModule)

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

        # init logger
        self.logger = logging.getLogger(self.__class__.__name__)

        # members
        self.profiles_types = []

    def _get_renderer_config(self):
        """
        Register internally available profiles and return it.
        This method is called once by inventory at startup

        Returns:
            dict: handled profiles by instance::

                {
                    profiles: list (RendererProfile)
                }

        Raises:
            Exception: if RENDERER_PROFILES member is not defined
        """
        if getattr(self, u'RENDERER_PROFILES', None) is None:
            raise Exception(u'RENDERER_PROFILES is not defined in "%s"' % self.__class__.__name__)

        # cache profile types as string
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
        # check profile type
        if profile.__class__.__name__ not in self.profiles_types:
            raise InvalidParameter(u'Profile "%s" is not supported in this renderer' % profile.__class__.__name__)

        # call implementation
        try:
            self._render(profile)
            return True
        except:
            self.logger.exception('Rendering profile "%s" failed:' % profile.__class__.__name__ if profile else None)
            return False

    def _render(self, profile):
        """
        Use specified profile values to render them

        Note:
            Must be implemented!

        Raises:
            NotImplementedError: if not implemented
        """
        raise NotImplementedError(u'Method "_render" must be implemented in "%s"' % self.__class__.__name__)
        
    def get_module_commands(self):
        """
        Return available module commands.
        
        Returns:
            list: list of command names.
        """
        ms = RaspIotModule.get_module_commands(self)

        ms.remove('render')

        return ms

