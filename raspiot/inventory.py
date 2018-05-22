#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot import RaspIotModule, RaspIotRenderer
from utils import CommandError, MissingParameter, InvalidParameter
import importlib
import inspect

__all__ = [u'Inventory']

class Inventory(RaspIotModule):
    """
    Inventory handles inventory of:
     - existing devices: knows all devices and module that handles it
     - loaded modules and their commands
     - existing renderers (sms, email, sound...)
    """ 

    MODULES_JSON = u'/etc/raspiot/modules.json'

    def __init__(self, bootstrap, debug_enabled, installed_modules):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): debug status
            modules (array): available modules
        """
        #init
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #members
        #factories
        self.events_factory = bootstrap[u'events_factory']
        self.formatters_factory = bootstrap[u'formatters_factory']
        #list devices: uuid => module name
        self.devices = {}
        #list of modules: dict(<module name>:dict(<module config>), ...)
        self.modules = {}
        #list of installed modules names with reference to real name
        self.installed_modules_names = {}
        #direct access to installed modules
        self.installed_modules = installed_modules
        #list of libraries
        self.libraries = []

        #fill installed and library modules list
        for module in installed_modules:
            if module.startswith(u'mod.'):
                _module = module.replace(u'mod.', '')
                self.installed_modules_names[_module] = module
            elif module.startswith(u'lib.'):
                _module = module.replace(u'lib.', '')
                self.installed_modules_names[_module] = module
                self.libraries.append(_module)

    def _configure(self):
        """
        Configure module
        """
        self.__load_modules()
        #self.__load_formatters()

    def __load_modules(self):
        """
        Load all available modules and their devices
        """
        #list all available modules (list should be downloaded from internet) and fill default metadata
        modules_json = self.cleep_filesystem.read_json(self.MODULES_JSON)
        if modules_json is None:
            #no modules loaded, fallback to empty list that will be filled only with local modules list
            self.logger.warning(u'No module loaded from Raspiot website')
            self.modules = {}
        else:
            self.modules = modules_json[u'list']
        for module_name in self.modules:
            #append metadata that doesn't exists in modules.json
            self.modules[module_name][u'locked'] = False
            self.modules[module_name][u'installed'] = False
            self.modules[module_name][u'library'] = False
            self.modules[module_name][u'local'] = False

        #append local modules (that doesn't exists on internet modules list)
        path = os.path.join(os.path.dirname(__file__), u'modules')
        if not os.path.exists(path):
            raise CommandError(u'Invalid modules path')
        for f in os.listdir(path):
            fpath = os.path.join(path, f)
            (module_name, ext) = os.path.splitext(f)
            if os.path.isfile(fpath) and ext==u'.py' and module_name!=u'__init__':
                #valid file
                if module_name not in self.modules:
                    self.logger.debug(u'Add modules found locally only')
                    #it is a local module
                    module_ = importlib.import_module(u'raspiot.modules.%s' % module_name)
                    class_ = getattr(module_, module_name.capitalize())

                    #fix module country
                    country = class_.MODULE_COUNTRY
                    if not country:
                        country = u''
                    else:
                        country = country.lower()

                    #build urls
                    urls = {
                        u'site': getattr(class_, u'MODULE_URLSITE', None),
                        u'bugs': getattr(class_, u'MODULE_URLBUGS', None),
                        u'info': getattr(class_, u'MODULE_URLINFO', None),
                        u'help': getattr(class_, u'MODULE_URLHELP', None)
                    }

                    #save module entry
                    self.modules[module_name] = {
                        u'description': class_.MODULE_DESCRIPTION,
                        u'locked': class_.MODULE_LOCKED,
                        u'tags': class_.MODULE_TAGS,
                        u'country': country,
                        u'urls': urls, 
                        u'installed': False,
                        u'library': False,
                        u'local': True
                    }

        #update metadata of installed modules
        self.logger.info(u'Installed modules: %s' % self.installed_modules_names.keys())
        for module in self.installed_modules_names.keys():
            #update local flag
            self.modules[module][u'local'] = True

            #update installed/library flag
            if module not in self.libraries:
                self.modules[module][u'installed'] = True
            else:
                self.modules[module][u'library'] = True

            #fill installed modules commands
            try:
                self.modules[module][u'command'] = self.installed_modules[self.installed_modules_names[module]].get_module_commands()
            except:
                self.logger.exception('Unable to get commands of module "%s":' % module)

            #fill installed modules devices
            try:
                devices = self.installed_modules[self.installed_modules_names[module]].get_module_devices()
                for uuid in devices:
                    #save new device entry (module name and device name)
                    self.devices[uuid] = {
                        u'module': module,
                        u'name': devices[uuid][u'name']
                    }
            except:
                self.logger.exception('Unable to get devices of module "%s"' % module)

            #fill renderers
            if issubclass(self.installed_modules[self.installed_modules_names[module]].__class__, RaspIotRenderer):
                try:
                    renderers = self.installed_modules[self.installed_modules_names[module]].get_module_renderers()
                    self.formatters_factory.register_renderer(module, renderers[u'type'], renderers[u'profiles'])
                except:
                    self.logger.exception('Unable to get renderers of module "%s"' % module)

        #self.logger.debug(u'DEVICES=%s' % self.devices)
        #self.logger.debug(u'MODULES=%s' % self.modules)

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
            module (string): module name
        
        Returns:
            array: list of devices 
                [{'uuid':'', 'name':''}, ...]

        Raises:
            CommandError: if module doesn't exists
        """
        #check values
        if self.modules.has_key(module):
            raise CommandError(u'Module %s doesn\'t exist' % module)

        #search module devices
        devices = []
        for uuid in self.devices:
            if self.devices[uuid][u'module']==module:
                devices.append({
                    u'uuid': uuid,
                    u'name': self.devices[uuid][u'name']
                })

        return devices

    def get_modules(self):
        """
        Returns list of modules
        
        Returns:
            list: list of modules::
                ['module name':{'module info':'', ...}, ...]
        """
        return self.modules

    def get_modules_names(self):
        """
        Returns list of modules names

        Returns:
            list: list of module names
                ['name1', 'name2', ...]
        """
        return self.modules.keys()

    def get_module_commands(self, module):
        """
        Returns list of module commands

        Args:
            module (string): module name

        Returns:
            list: list of commands or None if module not found::
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

    def get_modules_debug(self):
        """
        Return dict of installed modules or libraries debug flag

        Returns:
            dict: modules/libraries debug flag::
                {
                    modulename (bool): debug flag
                    ...
                }
        """
        debugs = {}
        for module in self.installed_modules_names.keys():
            #get debug status
            try:
                resp = self.send_command(u'is_debug_enabled', module)
                if resp[u'error']:
                    self.logger.error(u'Unable to get debug status of module %s: %s' % (module, resp[u'message']))
                    debugs[module] = {u'debug': False}
                else:
                    debugs[module] = {u'debug': resp[u'data']}
            except:
                self.logger.exception('Unable to get module %s debug status:' % module)
                debugs[module] = {u'debug': False}
    
        return debugs

    def get_renderers(self):
        """
        Return renderers from events factory

        Returns:
            list: list of renderers with their handled profiles
        """
        return self.formatters_factory.get_renderers_profiles()

    def get_modules_events(self):
        """
        Return modules events

        Return:
            dict: list of modules events::
                {
                    module1: [event1, event2, ...],
                    module2: [event1],
                    ...
                }
        """
        return self.events_factory.get_modules_events()

    def get_used_events(self):
        """
        Return used events

        Return:
            list: list of used events
        """
        return self.events_factory.get_used_events()

