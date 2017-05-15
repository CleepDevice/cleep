#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot import RaspIotModule
from utils import CommandError, MissingParameter, InvalidParameter
import importlib

__all__ = ['Inventory']

class Inventory(RaspIotModule):
    """
    Inventory handles inventory of:
     - existing devices: knows all devices uuid and module that handles it
     - loaded modules and their commands
     - existing providers (sms, email, sound...)
    """  

    def __init__(self, bus, debug_enabled, installed_modules):
        """
        Constructor

        Args:
            bus (MessageBus): bus instance
            debug_enabled (bool): debug status
            modules (array): available modules
        """
        #init
        RaspIotModule.__init__(self, bus, debug_enabled)

        #members
        #list devices: uuid => module name
        self.devices = {}
        #list of modules: dict(<module name>:dict(<module config>), ...)
        self.modules = {}
        #list of installed modules
        self.installed_modules = []
        #list of providers
        self.providers = {}

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
            #update installed flag
            self.modules[module]['installed'] = True

            #fill installed modules
            self.logger.debug('Request commands of module "%s"' % module)
            resp = self.send_command('get_module_commands', module, None, 15)
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

        Args:
            uuid (string): device identifier

        Returns:
            string: module name or None if device was not found
        """
        if self.devices.has_key(uuid):
            return self.devices[uuid]

        return None

    def get_device_infos(self, uuid):
        """
        Return device infos (module name and device name) according to specified uuid

        Args:
            uuid (string): device identifier
        
        Returns:
            dict: device infos or None if device not found
                {
                    'name': '',
                    'module': ''
                }
        """
        if self.devices.has_key(uuid):
            return self.devices[uuid]

        return None

    def get_module_devices(self, module):
        """
        Return module devices
        
        Args:
            module (strng): module name
        
        Returns:
            array: list of devices 
                [{'uuid':'', 'name':''}, ...]

        Raises:
            CommandError: if module doesn't exists
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
        
        Returns:
            list: list of modules
                ['module name':{'module info':'', ...}, ...]
        """
        return self.modules

    def get_modules_names(self):
        """
        Return list of modules names

        Returns:
            list: list of module names
                ['name1', 'name2', ...]
        """
        return self.modules.keys()

    def get_module_commands(self, module):
        """
        Return list of module commands

        Args:
            module (string): module name

        Returns:
            list: list of commands or None if module not found
                ['command1', 'command2', ...]
        """
        if self.modules.has_key(module):
            return self.modules[module]

        return None

    def is_module_loaded(self, module):
        """
        Simply returns True if specified module is loaded
        
        Args:
            module (string): module name

        Returns:
            bool: True if module loaded, False otherwise
        """
        return self.modules.has_key(module)

    def register_provider(self, type, subtype, profile, command_sender):
        """
        Register new provider

        Args:
            type (string): provider type (ie: alert for sms/push/email provider)
            subtype (string): provider subtype (ie: sms for sms provider)
            profiles (list of dict): used to describe provider capabilities (ie: screen can have 1 or 2 lines, provider user must adapts posted data according to this capabilities)
            command_sender (string): command sender (automatically added by bus)

        Returns:
            bool: True

        Raises:
            MissingParameter: if parameter is missing
        """
        self.logger.debug('Register new %s:%s provider %s' % (type, subtype, command_sender))
        #check values
        if type is None or len(type)==0:
            raise MissingParameter('Type parameter is missing')
        if subtype is None or len(subtype)==0:
            raise MissingParameter('Subtype parameter is missing')

        #add provider type
        if not self.providers.has_key(type):
            self.providers[type] = {}

        #add provider subtype
        if not self.providers[type].has_key(subtype):
            self.providers[type][subtype] = {}

        #register new provider
        self.providers[type][subtype][command_sender] = {
            'profile': profile
        }
        
        return True

    def unregister_provider(self, type, command_sender):
        """
        Unregister provider

        Args:
            command_sender (string): command sender (automatically added by bus)

        Returns:
            bool: True if unregistration succeed, False otherwise
        """
        if not self.providers.has_key(type) or not self.providers[type].has_key(command_sender):
            return False

        #remove provider
        del self.providers[type][command_sender]

        return True

    def has_provider(self, type):
        """
        Return True if at least one provider is registered for specified type

        Args:
            type (string): provider type
        
        Returns:
            bool: True if provider exists or False otherwise
        """
        if self.providers.has_key(type) and len(self.providers[type])>0:
            return True

        return False

    def get_providers(self, type):
        """
        Return list of available providers for specified type

        Args:
            type (string): provider type

        Returns:
            dict: empty dict if not provider available for requested type or available providers
        """
        if self.providers.has_key(type):
            return self.providers[type]

        return {}

