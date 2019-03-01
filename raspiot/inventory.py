#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import importlib
import inspect
import copy
from threading import Event
from raspiot import RaspIot, RaspIotRenderer, RaspIotRpcWrapper
from .libs.configs.modulesjson import ModulesJson
from utils import CommandError, MissingParameter, InvalidParameter
from .libs.configs.raspiotconf import RaspiotConf
from .libs.internals.install import Install
import libs.internals.tools as Tools

__all__ = [u'Inventory']

class Inventory(RaspIot):
    """
    Inventory handles inventory of:
     - existing devices: knows all devices and module that handles it
     - loaded modules and their commands
     - existing renderers (sms, email, sound...)
    """

    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'0.0.0'
    MODULE_CORE = True

    def __init__(self, bootstrap, rpcserver, debug_enabled, configured_modules, debug_config):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            rpcserver (Object): rpcserver instance (used to set debug)
            debug_enabled (bool): debug inventory or not
            configured_modules (dict): list of configured modules to start
            debug_config (dict): debug computed from config and command line
        """
        #init
        RaspIot.__init__(self, bootstrap, debug_enabled)
        #self.logger.setLevel(logging.DEBUG)

        #members
        self.__modules_loaded = False
        self.__rpcserver = rpcserver
        self.configured_modules = configured_modules
        self.debug_config = debug_config
        self.bootstrap = bootstrap
        self.events_factory = bootstrap[u'events_factory']
        self.formatters_factory = bootstrap[u'formatters_factory']
        #dict to store event to synchronize module startups
        self.__join_events = []
        #used to store modules status (library or not) during modules loading
        self.__modules_loaded_as_dependency = {}
        #list of modules: dict(<module name>:dict(<module config>), ...)
        self.modules = {}
        #list of mandatory modules that must be loaded at startup
        self.mandatory_modules = [
            u'system',
            u'audio',
            u'network',
            u'cleepbus',
            u'parameters'
        ]
        #direct access to modules instances
        self.__modules_instances = {}
        #modules that failed to starts
        self.__modules_in_errors = []
        #module names that are RaspIotRpcWrapper instances
        self.__rpc_wrappers = []

    def _configure(self):
        """
        Configure module
        """
        self.load_modules()

    def event_received(self, event):
        """
        Handle event

        Args:
            event (MessageRequest): event data
        """
        #handle module installation/uninstallation/update
        if event[u'event'] in (u'system.module.install', u'system.module.uninstall', u'system.module.update'):
            if event[u'params'][u'module'] in self.modules:
                if event[u'params'][u'status']==Install.STATUS_PROCESSING:
                    self.logger.debug(u'Set module "%s" processing status to True' % event[u'params'][u'module'])
                    if event[u'event']==u'system.module.install':
                        self.modules[event[u'params'][u'module']][u'processing'] = u'install'
                    elif event[u'event']==u'system.module.uninstall':
                        self.modules[event[u'params'][u'module']][u'processing'] = u'uninstall'
                    elif event[u'event']==u'system.module.update':
                        self.modules[event[u'params'][u'module']][u'processing'] = u'update'
                else:
                    self.logger.debug(u'Set module "%s" processing status to False' % event[u'params'][u'module'])
                    self.modules[event[u'params'][u'module']][u'processing'] = None

    def __get_bootstrap(self):
        """
        Get bootstrap object to pass to module to load
        This function instanciate a new Event for module synchronization and pass all other attributes
        """
        bootstrap = copy.copy(self.bootstrap)
        bootstrap[u'join_event'] = Event()

        return bootstrap

    def __fix_country(self, country):
        if not country:
            return u''
        else:
            return country.lower()

    def __fix_urls(self, site_url, bugs_url, info_url, help_url):
        return {
            u'site': site_url,
            u'bugs': bugs_url,
            u'info': info_url,
            u'help': help_url
        }

    def __load_module(self, module_name, local_modules, is_dependency=False):
        """
        Load specified module

        Args:
            module_name (string): module name
            local_modules (list): list of locally installed modules
            is_dependency (bool): True if module to load is a dependency
        """
        if is_dependency:
            self.logger.debug(u'Loading dependency "%s"' % module_name)
        else:
            self.logger.debug(u'Loading module "%s"' % module_name)

        #set module is installed
        self.modules[module_name][u'installed'] = True

        #import module file and get module class
        module_ = importlib.import_module(u'raspiot.modules.%s.%s' % (module_name, module_name))
        module_class_ = getattr(module_, module_name.capitalize())
                    
        #enable or not debug
        debug = False
        if self.debug_config[u'trace_enabled'] or self.debug_config[u'debug_modules'].count(module_name)==1:
            self.logger.debug(u'Debug enabled for module "%s"' % module_name)
            debug = True

        #instanciate module class
        self.logger.debug(u'Starting module "%s"' % module_name)

        #load module dependencies
        if module_class_.MODULE_DEPS:
            for dependency in module_class_.MODULE_DEPS:
                if dependency not in self.__modules_loaded_as_dependency:
                    #load dependency
                    self.__load_module(dependency, local_modules, True)

                    #flag module is loaded as dependency and not module
                    self.__modules_loaded_as_dependency[dependency] = True
            
                else:
                    #module is already loaded, nothing else to do
                    pass

        #instanciate and start module
        bootstrap = self.__get_bootstrap()
        self.__modules_instances[module_name] = module_class_(bootstrap, debug)
        self.__modules_instances[module_name].start()

        #append join event after module starts to make sure it can unlock it
        self.__join_events.append(bootstrap[u'join_event'])

        #fix some metadata
        fixed_urls = self.__fix_urls(
            getattr(module_class_, u'MODULE_URLSITE', None),
            getattr(module_class_, u'MODULE_URLBUGS', None),
            getattr(module_class_, u'MODULE_URLINFO', None),
            getattr(module_class_, u'MODULE_URLHELP', None)
        )
        fixed_country = self.__fix_country(getattr(module_class_, u'MODULE_COUNTRY', None))

        #update metadata with local values
        if module_name not in self.modules.keys():
            self.modules[module_name] = {}
        self.modules[module_name][u'description'] = module_class_.MODULE_DESCRIPTION
        self.modules[module_name][u'author'] = getattr(module_class_, u'MODULE_AUTHOR', u'')
        self.modules[module_name][u'core'] = getattr(module_class_, u'MODULE_CORE', False)
        self.modules[module_name][u'tags'] = getattr(module_class_, u'MODULE_TAGS', [])
        self.modules[module_name][u'country'] = fixed_country
        self.modules[module_name][u'urls'] = fixed_urls
        self.modules[module_name][u'category'] = getattr(module_class_, u'MODULE_CATEGORY', u'')
        self.modules[module_name][u'screenshots'] = getattr(module_class_, u'MODULE_SCREENSHOTS', [])

        #handle properly version and updatable flag
        if u'version' in self.modules[module_name] and Tools.compare_versions(module_class_.MODULE_VERSION, self.modules[module_name][u'version']):
            self.modules[module_name][u'updatable'] = self.modules[module_name][u'version']
        self.modules[module_name][u'version'] = module_class_.MODULE_VERSION

        #flag module is loaded as module and not dependency
        self.__modules_loaded_as_dependency[module_name] = False

    def __get_modules_json(self):
        """
        Get content of modules.json file

        Returns:
            dict: modules.json content
        """
        modules_json = ModulesJson(self.cleep_filesystem)

        if not modules_json.exists():
            #modules.json doesn't exists, download it
            self.logger.info(u'No modules.json still loaded from CleepOS website. Download it now')
            if modules_json.update():
                self.logger.info(u'File modules.json downloaded successfully')

            else:
                self.logger.error(u'Failed to update modules.json. No module (except installed ones) will be available')
                return modules_json.get_empty()

        return modules_json.get_json()

    def reload_modules(self):
        """
        Reload modules refreshing only not installed modules
        """
        self.logger.debug(u'Reloading modules')
        #get list of all available modules (from remote list)
        modules_json_content = self.__get_modules_json()
        modules_json = modules_json_content[u'list']

        #iterates over modules.json
        for module_name in modules_json:
            if module_name not in self.modules:
                self.logger.debug(u'Append module "%s" to list of modules' % module_name)
                #new module, add new entry in existing modules list
                self.modules[module_name] = {}
                
                #add data from modules.json
                for key in modules_json[module_name]:
                    self.modules[module_name][key] = copy.deepcopy(modules_json[module_name][key])

                #add internal data
                self.modules[module_name][u'name'] = module_name
                self.modules[module_name][u'installed'] = False
                self.modules[module_name][u'library'] = False
                self.modules[module_name][u'local'] = False
                self.modules[module_name][u'pending'] = False
                self.modules[module_name][u'processing'] = None
                self.modules[module_name][u'updatable'] = u''
                self.modules[module_name][u'core'] = False

    def load_modules(self):
        """
        Load all modules
        """
        #init
        if self.__modules_loaded:
            raise Exception(u'Modules loading must be performed only once. If you want to refresh modules list, use reload_modules instead')
        local_modules = []
                
        #get list of all available modules (from remote list)
        modules_json_content = self.__get_modules_json()
        self.modules = modules_json_content[u'list']

        #append manually installed modules (surely module in development)
        path = os.path.join(os.path.dirname(__file__), u'modules')
        if not os.path.exists(path):
            raise CommandError(u'Invalid modules path')
        for f in os.listdir(path):
            fpath = os.path.join(path, f)
            module_name = os.path.split(fpath)[-1]
            module_py = os.path.join(fpath, u'%s.py' % module_name)
            if os.path.isdir(fpath) and os.path.exists(module_py) and module_name not in self.modules:
                self.logger.debug(u'Found module "%s" installed manually' % module_name)
                local_modules.append(module_name)
                self.modules[module_name] = {}

        #add default metadata
        for module_name in self.modules:
            self.modules[module_name][u'name'] = module_name
            self.modules[module_name][u'installed'] = False
            self.modules[module_name][u'library'] = False
            self.modules[module_name][u'local'] = module_name in local_modules
            self.modules[module_name][u'pending'] = False
            self.modules[module_name][u'processing'] = None
            self.modules[module_name][u'updatable'] = u''
            self.modules[module_name][u'core'] = False
            self.modules[module_name][u'screenshots'] = []

        #load mandatory modules
        for module_name in self.mandatory_modules:
            try:
                #load module
                self.__load_module(module_name, local_modules)

            except:
                #failed to load mandatory module
                self.logger.fatal(u'Unable to load main module "%s". System will be instable' % module_name)
                self.logger.exception(u'Module "%s" exception:' % module_name)
                self.crash_report.report_exception({
                    u'message': u'Unable to load main module "%s". System will be instable' % module_name,
                    u'module_name': module_name
                })

        #load installed modules
        for module_name in self.configured_modules:
            try:
                #load module
                self.__load_module(module_name, local_modules)

                #fill renderers
                if issubclass(self.__modules_instances[module_name].__class__, RaspIotRenderer):
                    renderers = self.__modules_instances[module_name].get_module_renderers()
                    self.formatters_factory.register_renderer(module_name, renderers[u'type'], renderers[u'profiles'])

            except:
                #flag modules has in error
                self.__modules_in_errors.append(module_name)

                #failed to load module
                self.logger.exception(u'Unable to load module "%s" or one of its dependencies:' % module_name)

        #finalize loading process
        for module_name in self.modules:
            #fix final library status
            if module_name in self.__modules_loaded_as_dependency:
                self.modules[module_name][u'library'] = self.__modules_loaded_as_dependency[module_name]

            #store rpc wrappers
            if module_name in self.__modules_instances and isinstance(self.__modules_instances[module_name], RaspIotRpcWrapper):
                self.logger.debug(u'Store RpcWrapper instance "%s"' % module_name)
                self.__rpc_wrappers.append(module_name)

        #wait for all modules are completely loaded
        self.logger.debug('Waiting for end of modules loading...')
        for join_event in self.__join_events:
            join_event.wait()

        self.__modules_loaded = True
        self.logger.debug('All modules are loaded')

    def unload_modules(self):
        """
        Unload all modules stopping them
        """
        #stpo all running modules
        for module_name in self.__modules_instances:
            self.__modules_instances[module_name].stop()

        #clear collection
        self.__modules_instances.clear()

    def get_device_module(self, uuid):
        """
        Return module that owns specified device

        Args:
            uuid (string): device identifier

        Returns:
            string: module name or None if device was not found
        """
        devices = self.get_devices()
        for module_name in devices:
            if uuid in devices[module_name]:
                return module_name

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
        if module in self.modules:
            raise CommandError(u'Module %s doesn\'t exist' % module)

        #search module devices
        devices = self.get_devices()
        for module_name in devices:
            if module_name==module:
                return devices[module_name]

        return []

    def get_devices(self):
        """
        Return list of modules devices

        Returns:
            dict: dictionnary of devices by module::
                {
                    module1: 
                        device uuid: {
                            device properties,
                            ...
                        },
                        ...
                    },
                    module2: ...
                }
        """
        #init
        devices = {}

        #get all devices
        for module_name in self.__modules_instances:
            try:
                module_devices = self.__modules_instances[module_name].get_module_devices()
                devices[module_name] = module_devices
            
            except:
                self.logger.exception(u'Unable to get devices of module "%s"' % module_name)

        return devices

    def get_module(self, module):
        """
        Returns infos of specified module

        Returns:
            list: module infos::
            {
                name: str
                version: str
                ...
            }
        """
        if module not in self.modules:
            return None

        else:
            return copy.deepcopy(self.modules[module])

    def get_modules(self):
        """
        Returns list of modules
        
        Returns:
            list: list of modules::
                {
                    module name: {
                        name: '',
                        version: '',
                        ...
                    },
                    ...
                }
        """
        #init
        modules = copy.deepcopy(self.modules)
        events = self.events_factory.get_modules_events()
        conf = RaspiotConf(self.cleep_filesystem)
        raspiot_config = conf.as_dict()
        
        #inject volatile infos
        for module_name in modules:
            try:
                #current module config
                if module_name in self.__modules_instances:
                    modules[module_name][u'config'] = self.__modules_instances[module_name].get_module_config()
            
                #module events
                if module_name in events:
                    modules[module_name][u'events'] = events[module_name]

                #pending status
                modules[module_name][u'pending'] = False
                if module_name in self.mandatory_modules:
                    #mandatory modules
                    modules[module_name][u'pending'] = False
                elif module_name in self.__modules_in_errors:
                    #module failed to start, force eventual pending state to false
                    modules[module_name][u'pending'] = False
                elif module_name in raspiot_config[u'general'][u'modules'] and not modules[module_name][u'installed']:
                    #install pending
                    modules[module_name][u'pending'] = True
                elif module_name not in raspiot_config[u'general'][u'modules'] and modules[module_name][u'installed']:
                    #uninstall pending
                    modules[module_name][u'pending'] = True
                elif module_name in raspiot_config[u'general'][u'updated'] and modules[module_name][u'installed']:
                    #module updated, need to restart raspiot
                    modules[module_name][u'pending'] = True

                #started flag
                if module_name in self.__modules_in_errors:
                    modules[module_name][u'started'] = False
                else:
                    modules[module_name][u'started'] = True

            except:
                self.logger.exception(u'Unable to get config of module "%s"' % module_name)

        return modules
            
    def get_module_commands(self, module):
        """
        Returns list of module commands

        Args:
            module (string): module name

        Returns:
            list: list of commands or None if module not found::
                ['command1', 'command2', ...]
        """
        if module in self.__modules_instances:
            return self.__modules_instances[module].get_module_commands()

        return None

    def is_module_loaded(self, module):
        """
        Simply returns True if specified module is loaded
        
        Args:
            module (string): module name

        Returns:
            bool: True if module loaded, False otherwise
        """
        return module in self.__modules_instances

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
        for module in self.modules:
            #installed module ?
            if not self.modules[module][u'installed']:
                continue

            #get debug status
            try:
                debugs[module] = {
                    u'debug': self.__modules_instances[module].is_debug_enabled()
                }

            except:
                self.logger.exception('Unable to get module %s debug status:' % module)
                debugs[module] = {
                    u'debug': False
                }

        #append system modules
        debugs[u'inventory'] = {
            u'debug': self.is_debug_enabled()
        }
        debugs[u'rpc'] = {
            u'debug': self.__rpcserver.get_debug()
        }
    
        return debugs

    def set_rpc_debug(self, debug):
        """
        Set debug on rpcserver

        Args:
            debug (bool): debug enabled or not
        """
        self.__rpcserver.set_debug(debug)

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

    def rpc_wrapper(self, route, request):
        """
        Rpc wrapper is called by rpc server when default / POST route is called.
        Inventory get all loaded RaspIotRpcWrapperModule modules and push the bottle request object.
        See bottle documentation for request object description https://bottlepy.org/docs/dev/tutorial.html#request-data
        """
        for module_name in self.__rpc_wrappers:
            try:
                self.__modules_instances[module_name].wrap_request(route, request)
            except:
                self.logger.exception(u'RpcWrapper wrap_request function failed:')

