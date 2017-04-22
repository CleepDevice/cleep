#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot import RaspIotMod
from utils import CommandError, MissingParameter, InvalidParameter
import importlib

__all__ = ['Inventory']

class Inventory(RaspIotMod):
    """
    Class that handles inventory of:
     - existing devices: knows all devices uuid and module that handles it
     - loaded modules and their commands
    """  

    def __init__(self, bus, debug_enabled, installed_modules):
        """
        Constructor
        @param bus: bus instance
        @param debug_enabled: debug status
        @param modules: array of available modules
        """
        #init
        RaspIotMod.__init__(self, bus, debug_enabled)

        #member
        #list devices: uuid => module name
        self.devices = {}
        #list of modules: dict(<module name>:dict(<module config>), ...)
        self.modules = {}
        #list of installed modules
        self.installed_modules = []

        #fill installed modules list
        for module in installed_modules:
            if module.startswith('mod.'):
                _module = module.replace('mod.', '')
                self.installed_modules.append(_module)

    def _start(self):
        """
        Start module
        """
        #list all modules
        path = os.path.join(os.path.dirname(__file__), 'modules')
        if not os.path.exists(path):
            raise CommandError('Invalid modules path')
        for f in os.listdir(path):
            fpath = os.path.join(path, f)
            (module, ext) = os.path.splitext(f)
            if os.path.isfile(fpath) and ext=='.py' and module!='__init__':
                module_ = importlib.import_module('raspiot.modules.%s' % module)
                class_ = getattr(module_, module.capitalize())
                self.modules[module] = {
                    'description': class_.MODULE_DESCRIPTION,
                    'locked': class_.MODULE_LOCKED,
                    'tags': class_.MODULE_TAGS,
                    'url': class_.MODULE_URL,
                    'installed': False
                }

        self.logger.info('installed modules: %s' % self.installed_modules)
        for module in self.installed_modules:
            self.logger.info(' ==> %s' % module)
            #update installed flag
            self.modules[module]['installed'] = True

            #fill installed modules
            self.logger.debug('Request commands of module "%s"' % module)
            resp = self.send_command('get_module_commands', module)
            if not resp['error']:
                self.modules[module]['commands'] = resp['data']
            else:
                self.logger.error('Unable to get commands of module "%s"' % module)

            #fill devices
            self.logger.debug('Request devices of module "%s"' % module)
            resp = self.send_command('get_module_devices', module)
            if not resp['error']:
                for uuid in resp['data']:
                    #save new device entry (module name and device name)
                    self.devices[uuid] = {
                        'module': module,
                        'name': resp['data'][uuid]['name']
                    }
            else:
                self.logger.error('Unable to get devices of module "%s"' % module)

        self.logger.debug('devices=%s' % self.devices)
        self.logger.debug('modules=%s' % self.modules)

    def get_device_module(self, uuid):
        """
        Return module that owns specified device
        @param uuid: device identifier
        @return module name (string) or None if device was not found
        """
        if self.devices.has_key(uuid):
            return self.devices[uuid]

        return None

    def get_device_infos(self, uuid):
        """
        Return device infos (module name and device name) according to specified uuid
        @param uuid: device identifier
        @return device infos (dict(<device name>, <device module>)) or None if device not found
        """
        if self.devices.has_key(uuid):
            return self.devices[uuid]

        return None

    def get_module_devices(self, module):
        """
        Return module devices
        @param module: module name
        @return list of devices (array of dict(<device uuid>, <device name>))
        """
        #check values
        if self.modules.has_key(module):
            raise CommandError('Module %s doesn\'t exist' % module)

        #search module devices
        devices = []
        for uuid in self.devices:
            if self.devices[uuid]['module']==module:
                devices.append({
                    'uuid': uuid,
                    'name': self.devices[uuid]['name']
                })

        return devices

    def get_modules(self):
        """
        Return list of modules
        @return dict of modules
        """
        return self.modules

    def get_modules_names(self):
        """
        Return list of modules names
        @return array of module names (string)
        """
        return self.modules.keys()

    def get_module_commands(self, module):
        """
        Return list of module commands
        @param module: module name (string)
        @return list of commands (array(<command name>)) or None if module not found
        """
        if self.modules.has_key(module):
            return self.modules[module]

        return None

    def is_module_loaded(self, module):
        """
        Simply returns True if specified module is loaded
        @param module: module name
        @return True if module loaded, False otherwise
        """
        return self.modules.has_key(module)

