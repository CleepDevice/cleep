#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot import RaspIotModule
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
        #renderers
        self.renderer_profiles = {}
        self.renderers = {}
        #formatters
        self.formatters = {}

        #fill installed modules list
        for module in installed_modules:
            if module.startswith(u'mod.'):
                _module = module.replace(u'mod.', '')
                self.installed_modules.append(_module)

    def _start(self):
        """
        Start module
        """
        self.__load_modules()
        self.__load_formatters()

    def __load_modules(self):
        """
        Load all available modules and their devices
        """
        #list all modules
        path = os.path.join(os.path.dirname(__file__), u'modules')
        if not os.path.exists(path):
            raise CommandError(u'Invalid modules path')
        for f in os.listdir(path):
            fpath = os.path.join(path, f)
            (module, ext) = os.path.splitext(f)
            if os.path.isfile(fpath) and ext==u'.py' and module!=u'__init__':
                module_ = importlib.import_module(u'raspiot.modules.%s' % module)
                class_ = getattr(module_, module.capitalize())
                self.modules[module] = {
                    u'description': class_.MODULE_DESCRIPTION,
                    u'locked': class_.MODULE_LOCKED,
                    u'tags': class_.MODULE_TAGS,
                    u'url': class_.MODULE_URL,
                    u'installed': False
                }

        self.logger.info(u'Installed modules: %s' % self.installed_modules)
        for module in self.installed_modules:
            #update installed flag
            self.modules[module][u'installed'] = True

            #fill installed modules
            self.logger.debug(u'Request commands of module "%s"' % module)
            resp = self.send_command(u'get_module_commands', module, None, 15)
            if not resp[u'error']:
                self.modules[module][u'commands'] = resp[u'data']
            else:
                self.logger.error(u'Unable to get commands of module "%s"' % module)

            #fill devices
            self.logger.debug(u'Request devices of module "%s"' % module)
            resp = self.send_command(u'get_module_devices', module)
            if not resp[u'error']:
                for uuid in resp[u'data']:
                    #save new device entry (module name and device name)
                    self.devices[uuid] = {
                        u'module': module,
                        u'name': resp[u'data'][uuid][u'name']
                    }
            else:
                self.logger.error(u'Unable to get devices of module "%s"' % module)

        self.logger.debug(u'DEVICES=%s' % self.devices)
        self.logger.debug(u'MODULES=%s' % self.modules)

    def __load_formatters(self):
        """
        Load all available formatters
        """
        #list all formatters in formatters folder
        path = os.path.join(os.path.dirname(__file__), u'formatters')
        if not os.path.exists(path):
            raise CommandError(u'Invalid formatters path')

        #iterates over formatters
        for f in os.listdir(path):
            #build path
            fpath = os.path.join(path, f)
            (formatter, ext) = os.path.splitext(f)
            self.logger.debug(u'formatter=%s ext=%s' % (formatter, ext))

            #filter files
            if os.path.isfile(fpath) and ext==u'.py' and formatter!=u'__init__' and formatter!=u'formatter':

                formatters_ = importlib.import_module(u'raspiot.formatters.%s' % formatter)
                for name, class_ in inspect.getmembers(formatters_):

                    #filter imports
                    if name is None:
                        continue
                    if not unicode(class_).startswith(u'raspiot.formatters.%s.' % formatter):
                        continue
                    instance_ = class_()

                    #save formatter
                    self.logger.debug(u'Found class %s in %s' % (unicode(class_), formatter) )
                    if not self.formatters.has_key(instance_.input):
                        self.formatters[instance_.input] = {}
                    self.formatters[instance_.input][instance_.output] = instance_
                    self.logger.debug(u'  %s => %s' % (instance_.input, instance_.output))

        self.logger.debug(u'FORMATTERS: %s' % self.formatters)

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

    def get_renderers(self):
        """
        Returns list of renderers
        
        Returns:
            list: list of renderers by type::
                {
                    'type1': {
                        'subtype1':  {
                            <profile name>: <profile instance>,
                            ...
                        }
                        'subtype2': ...
                    },
                    'type2': {
                        <profile name>: <renderer instance>
                    },
                    ...
                }
        """
        return self.renderers

    def register_renderer(self, type, profiles, command_sender):
        """
        Register new renderer

        Args:
            type (string): renderer type (ie: alert for sms/push/email renderer)
            profiles (list of data): used to describe renderer capabilities (ie: screen can have 1 or 2 lines,
                renderer must adapts posted data according to this capabilities)
            command_sender (string): value automatically added by raspiot

        Returns:
            bool: True

        Raises:
            MissingParameter, InvalidParameter
        """
        self.logger.debug(u'Register new renderer %s' % (type))
        #check values
        if type is None or len(type)==0:
            raise MissingParameter(u'Type parameter is missing')
        if profiles is None:
            raise MissingParameter(u'Profiles is missing')
        if len(profiles)==0:
            raise InvalidParameter(u'Profiles must contains at least one profile')

        #update renderers list
        if not self.renderers.has_key(type):
            self.renderers[type] = []
        self.renderers[type].append(command_sender)

        #update renderer profiles list
        for profile in profiles:
            profile_name = profile.__class__.__name__
            if not self.renderer_profiles.has_key(command_sender):
                self.renderer_profiles[command_sender] = []
            self.renderer_profiles[command_sender].append(profile_name)

        self.logger.debug(u'RENDERERS: %s' % self.renderers)
        self.logger.debug(u'RENDERERS PROFILES: %s' % self.renderer_profiles)
        
        return True

    def has_renderer(self, type):
        """
        Return True if at least one renderer is registered for specified type

        Args:
            type (string): renderer type
        
        Returns:
            bool: True if renderer exists or False otherwise
        """
        if len(self.renderers)>0 and self.renderers.has_key(type) and len(self.renderers[type])>0:
            return True

        return False

    def render_event(self, event, event_values, types):
        """
        Render event to renderer types

        Args:
            types (list<string>): existing renderer type
        """
        if not isinstance(types, list):
            raise InvalidParameter(u'Types must be a list')

        #iterates over registered types
        for type in types:
            if self.has_renderer(type):
                #renderer exists for current type

                #get formatters
                self.logger.debug(u'Searching formatters...')
                formatters = {}
                for formatter in self.formatters:
                    if formatter.endswith(event):
                        formatters.update(self.formatters[formatter])
                if len(formatters)==0:
                    #no formatter found, exit
                    self.logger.debug(u'No formatter found for event %s' % event)
                    return False

                #find match with formatters and renderer profiles
                for renderer in self.renderers[type]:
                    for profile in self.renderer_profiles[renderer]:
                        if profile in formatters:
                            self.logger.debug(u'Found match, post profile data to renderer %s' % renderer)
                            #found match, format event to profile
                            data = formatters[profile].format(event_values)

                            #handle no data
                            if data is None:
                                continue

                            #and post profile data to renderer
                            resp = self.send_command(u'render', renderer, {u'data':data})
                            if resp[u'error']:
                                self.logger.error(u'Unable to post data to "%s" renderer: %s' % (renderer, resp[u'message']))

            else:
                #no renderer for current type
                self.logger.debug(u'No renderer registered for %s' % type)



