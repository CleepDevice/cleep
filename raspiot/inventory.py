#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import importlib
import inspect
import copy
from threading import Event
from raspiot.core import RaspIot, RaspIotModule, RaspIotRenderer, RaspIotRpcWrapper
from raspiot.libs.configs.modulesjson import ModulesJson
from raspiot.exception import CommandError, MissingParameter, InvalidParameter
from raspiot.libs.configs.raspiotconf import RaspiotConf
from raspiot.libs.internals.install import Install
import raspiot.libs.internals.tools as Tools
from raspiot.common import CORE_MODULES, ExecutionStep

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

    PYTHON_RASPIOT_IMPORT_PATH = u'raspiot.modules.'
    PYTHON_RASPIOT_MODULES_PATH = u'modules'

    def __init__(self, bootstrap, rpcserver, debug_enabled, configured_modules, debug_config):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            rpcserver (Bottle): rpcserver instance (used to set debug)
            debug_enabled (bool): debug inventory or not
            configured_modules (list): list of configured modules to start::

                ['module1', 'module2', ...]

            debug_config (dict): debug computed from config and command line::

                {
                    trace_enabled (bool): trace enabled flag
                    debug_modules (list): list of modules to enable debug
                }

        """
        # init
        RaspIot.__init__(self, bootstrap, debug_enabled)
        # self.logger.setLevel(logging.DEBUG)

        # members
        self.__modules_loaded = False
        self.__rpcserver = rpcserver
        self.configured_modules = configured_modules
        self.debug_config = debug_config
        self.bootstrap = bootstrap
        self.events_broker = bootstrap[u'events_broker']
        self.formatters_broker = bootstrap[u'formatters_broker']
        # dict to store event to synchronize module startups
        self.__join_events = []
        # used to store modules status (library or not) during modules loading
        self.__modules_loaded_as_dependency = {}
        # list of modules: dict(<module name>:dict(<module config>), ...)
        self.modules = {}
        # direct access to modules instances
        self.__modules_instances = {}
        # modules that failed to starts
        self.__modules_in_errors = []
        # module names that are RaspIotRpcWrapper instances
        self.__rpc_wrappers = []
        # modules dependencies
        self.__dependencies = {}
        # current module loading tree
        self.__module_loading_tree = []

    def _configure(self):
        """
        Configure module
        """
        self._load_modules()

    def event_received(self, event):
        """
        Handle event

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
        # handle module installation/uninstallation/update
        if event[u'event'] in (u'system.module.install', u'system.module.uninstall', u'system.module.update'):
            if event[u'params'][u'module'] in self.modules:
                if event[u'params'][u'status']==Install.STATUS_PROCESSING:
                    self.logger.debug(u'Update module "%s" processing status' % event[u'params'][u'module'])
                    if event[u'event']==u'system.module.install':
                        self.modules[event[u'params'][u'module']][u'processing'] = u'install'
                    elif event[u'event']==u'system.module.uninstall':
                        self.modules[event[u'params'][u'module']][u'processing'] = u'uninstall'
                    elif event[u'event']==u'system.module.update':
                        self.modules[event[u'params'][u'module']][u'processing'] = u'update'
                else:
                    self.logger.debug(u'Set module "%s" processing status to None' % event[u'params'][u'module'])
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
        return u'' if not country else country.lower()

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

        # handle circular dependency
        if module_name in self.__module_loading_tree:
            self.logger.trace(u'Circular dependency detected')
            return
        self.__module_loading_tree.append(module_name)
        self.logger.trace(u'Module loading tree: %s' % self.__module_loading_tree)

        # handle already loaded dependency
        if module_name in self.__modules_loaded_as_dependency:
            self.logger.trace(u'Trying to loaded dependency module "%s" as a module, it is now considered as module' % module_name)
            self.__modules_loaded_as_dependency[module_name] = False
            return

        # set module is installed
        if module_name not in self.modules and module_name not in local_modules:
            raise Exception('Module "%s" doesn\'t exist. Parent module and module dependencies won\'t be loaded.' % module_name)
        self.modules[module_name][u'installed'] = True

        # import module file and get module class
        module_path = u'%s%s.%s' % (self.PYTHON_RASPIOT_IMPORT_PATH, module_name, module_name)
        self.logger.trace(u'Importing module "%s"' % module_path)
        module_ = importlib.import_module(module_path)
        module_class_ = getattr(module_, module_name.capitalize())
                    
        # enable or not debug
        debug = False
        if self.debug_config[u'trace_enabled'] or module_name in self.debug_config[u'debug_modules']:
            self.logger.debug(u'Debug enabled for module "%s"' % module_name)
            debug = True

        # load module dependencies
        self.logger.trace('Module "%s" dependencies: %s' % (module_name, module_class_.MODULE_DEPS))
        if module_class_.MODULE_DEPS:
            for dependency in module_class_.MODULE_DEPS:
                # self.logger.trace('Processing "%s" module dependency "%s"' % (module_name, dependency))
                # update dependencies list
                if dependency not in self.__dependencies:
                    self.__dependencies[dependency] = []
                self.__dependencies[dependency].append(module_name)
                
                #if dependency not in self.__modules_loaded_as_dependency:
                if dependency not in self.__modules_instances:
                    # load dependency
                    self.__load_module(dependency, local_modules, True)
                    self.__module_loading_tree.pop()

                    # flag module is loaded as dependency and not module
                    self.__modules_loaded_as_dependency[dependency] = True
            
                else:
                    # dependency is already loaded, nothing else to do
                    self.logger.trace(u'Dependency "%s" already loaded' % dependency)

        # instanciate module
        self.logger.trace(u'Instanciating module "%s"' % module_name)
        bootstrap = self.__get_bootstrap()
        self.__modules_instances[module_name] = module_class_(bootstrap, debug)

        # append module join event to make sure all modules are loaded
        self.__join_events.append(bootstrap[u'join_event'])

        # fix some metadata
        fixed_urls = self.__fix_urls(
            getattr(module_class_, u'MODULE_URLSITE', None),
            getattr(module_class_, u'MODULE_URLBUGS', None),
            getattr(module_class_, u'MODULE_URLINFO', None),
            getattr(module_class_, u'MODULE_URLHELP', None)
        )
        fixed_country = self.__fix_country(getattr(module_class_, u'MODULE_COUNTRY', None))

        # update metadata with module values
        self.modules[module_name].update({
            u'description': module_class_.MODULE_DESCRIPTION,
            u'author': getattr(module_class_, u'MODULE_AUTHOR', u''),
            u'core': getattr(module_class_, u'MODULE_CORE', False),
            u'tags': getattr(module_class_, u'MODULE_TAGS', []),
            u'country': fixed_country,
            u'urls': fixed_urls,
            u'category': getattr(module_class_, u'MODULE_CATEGORY', u''),
            u'screenshots': getattr(module_class_, u'MODULE_SCREENSHOTS', []),
            u'deps': getattr(module_class_, u'MODULE_DEPS', []),
        })

        # handle properly version and updatable flag
        # self.logger.trace('Check module "%s" version: %s<->%s' % (module_name, module_class_.MODULE_VERSION, self.modules[module_name][u'version']))
        if u'version' in self.modules[module_name] and Tools.compare_versions(module_class_.MODULE_VERSION, self.modules[module_name][u'version']):
            self.modules[module_name][u'updatable'] = self.modules[module_name][u'version']
        self.modules[module_name][u'version'] = module_class_.MODULE_VERSION

        # flag module is loaded as module and not dependency
        self.__modules_loaded_as_dependency[module_name] = False

    def _get_modules_json(self):
        """
        Get content of modules.json file

        Returns:
            dict: modules.json content
        """
        modules_json = ModulesJson(self.cleep_filesystem)

        if not modules_json.exists():
            # modules.json doesn't exists, download it
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
        self.logger.info(u'Reloading modules')
        # get list of all available modules (from remote list)
        modules_json_content = self._get_modules_json()
        modules_json = modules_json_content[u'list']
        self.logger.trace(u'modules.json: %s' % modules_json)

        # iterates over new modules.json
        for module_name, module_data in modules_json.items():
            if module_name not in self.modules:
                # new module, add new entry in existing modules list
                self.logger.debug(u'Add new module "%s" to list of available modules' % module_name)
                self.modules[module_name] = module_data
                
                # add data from modules.json
                #for key in modules_json[module_name]:
                #    self.modules[module_name][key] = copy.deepcopy(modules_json[module_name][key])

                # add/force some metadata
                self.modules[module_name].update({
                    u'name': module_name,
                    u'installed': False,
                    u'library': False,
                    u'local': False,
                    u'pending': False,
                    u'processing': None,
                    u'updatable': u'',
                    u'core': False,
                    u'screenshots': [],
                    u'deps': [],
                    u'loadedby': [],
                })

            else:
                # update existing module, but only updatable flag
                # current module must keep its local data
                self.modules[module_name].update({
                    u'updatable': module_data[u'version'] if Tools.compare_versions(self.modules[module_name][u'version'], module_data[u'version']) else u'',
                })

    def _load_modules(self):
        """
        Load all modules
        """
        # init
        if self.__modules_loaded:
            raise Exception(u'Modules loading must be performed only once. If you want to refresh modules list, use reload_modules instead')
        local_modules = []
                
        # get list of all available modules (from remote list)
        modules_json_content = self._get_modules_json()
        self.modules = modules_json_content[u'list']
        self.logger.trace('Modules.json: %s' % self.modules)

        # append manually installed modules (surely module in development)
        local_modules_path = os.path.abspath(os.path.join(os.path.dirname(__file__), self.PYTHON_RASPIOT_MODULES_PATH))
        self.logger.trace('Local modules path: %s' % local_modules_path)
        if not os.path.exists(local_modules_path): # pragma: no cover
            raise CommandError(u'Invalid modules path')
        for f in os.listdir(local_modules_path):
            fpath = os.path.join(local_modules_path, f)
            module_name = os.path.split(fpath)[-1]
            module_py = os.path.join(fpath, u'%s.py' % module_name)
            if os.path.isdir(fpath) and os.path.exists(module_py) and module_name not in self.modules:
                self.logger.debug(u'Found module "%s" installed manually' % module_name)
                local_modules.append(module_name)
                self.modules[module_name] = {}
        self.logger.trace('Local modules: %s' % local_modules)

        # add default metadata
        for module_name in self.modules:
            self.modules[module_name].update({
                u'name': module_name,
                u'installed': False,
                u'library': False,
                u'local': module_name in local_modules,
                u'pending': False,
                u'processing': None,
                u'updatable': u'',
                u'core': False,
                u'screenshots': [],
                u'deps': [],
                u'loadedby': [],
            })

        # execution step: BOOT->INIT
        self.bootstrap[u'execution_step'].step = ExecutionStep.INIT

        # load core modules
        self.logger.trace('CORE_MODULES: %s' % CORE_MODULES)
        for module_name in CORE_MODULES:
            try:
                # load module
                self.__load_module(module_name, local_modules)

            except:
                # failed to load mandatory module
                self.logger.error(u'Unable to load core module "%s". System will be instable' % module_name)
                self.logger.exception(u'Core module "%s" exception:' % module_name)
                self.crash_report.report_exception({
                    u'message': u'Unable to load core module "%s". System will be instable' % module_name,
                    u'module_name': module_name
                })

            finally:
                # clear module loading tree (replace it with clear() available in python3)
                del self.__module_loading_tree[:]

        # load installed modules
        for module_name in self.configured_modules:
            try:
                # load module
                self.__load_module(module_name, local_modules)

                # register renderers
                # if issubclass(self.__modules_instances[module_name].__class__, RaspIotRenderer):
                if module_name in self.__modules_instances and isinstance(self.__modules_instances[module_name], RaspIotRenderer):
                    config = self.__modules_instances[module_name]._get_renderer_config()
                    self.formatters_broker.register_renderer(module_name, config[u'profiles'])

                # store rpc wrappers
                if module_name in self.__modules_instances and isinstance(self.__modules_instances[module_name], RaspIotRpcWrapper):
                    self.logger.debug(u'Store RpcWrapper instance "%s"' % module_name)
                    self.__rpc_wrappers.append(module_name)

            except:
                # flag modules has in error
                self.__modules_in_errors.append(module_name)

                # failed to load module
                self.logger.exception(u'Unable to load module "%s" or one of its dependencies:' % module_name)

            finally:
                # clear module loading tree (replace it with clear() available in python3)
                del self.__module_loading_tree[:]

        # execution step: INIT->CONFIG
        self.bootstrap[u'execution_step'].step = ExecutionStep.CONFIG

        # finalize loading process
        for module_name in self.modules:
            # fix final library status
            if module_name in self.__modules_loaded_as_dependency:
                self.modules[module_name][u'library'] = self.__modules_loaded_as_dependency[module_name]

        # start installed modules
        for module_name, module_ in self.__modules_instances.items():
            module_.start()

        # wait for all modules to be completely loaded
        self.logger.info(u'Waiting for end of modules configuration...')
        for join_event in self.__join_events:
            join_event.wait()
        self.logger.info(u'All modules are configured.')

        # execution step: CONFIG->RUN
        self.bootstrap[u'execution_step'].step = ExecutionStep.RUN

        self.__modules_loaded = True
        self.logger.debug('All modules are loaded')

    def unload_modules(self):
        """
        Unload all modules stopping them
        """
        # stop all running modules
        for module_name in self.__modules_instances:
            self.__modules_instances[module_name].stop()

        # clear collection
        self.__modules_instances.clear()

    def get_module_device(self, uuid):
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

    def get_module_devices(self, module_name):
        """
        Return module devices
        
        Args:
            module_name (string): module name
        
        Returns:
            list: list of devices::

                [
                    {'uuid':'', 'name':''},
                    ...
                ]

        Raises:
            CommandError: if module doesn't exists
        """
        # check values
        if module_name not in self.modules:
            raise InvalidParameter(u'Module "%s" doesn\'t exist' % module_name)

        # search module devices
        devices = self.get_devices()
        return devices[module_name] if module_name in devices else []

    def get_devices(self):
        """
        Return dict of modules devices

        Returns:
            dict: dict of devices by module::

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
        # init
        devices = {}

        # get all devices
        for module_name in self.__modules_instances:
            try:
                if isinstance(self.__modules_instances[module_name], RaspIotModule):
                    devices[module_name] = self.__modules_instances[module_name].get_module_devices()
            
            except:
                self.logger.exception(u'Unable to get devices of module "%s"' % module_name)

        return devices

    def get_module_infos(self, module_name):
        """
        Returns infos of specified module

        Args:
            module_name (string): module name

        Returns:
            dict: module infos or empty dict if module not found::
                
                {
                    name: str
                    version: str
                    ...
                }

        """
        if module_name not in self.modules:
            return {}

        events = self.events_broker.get_modules_events()
        module = copy.deepcopy(self.modules[module_name])

        # add module config
        module[u'config'] = self.__modules_instances[module_name].get_module_config()
            
        # add module events
        module[u'events'] = events[module_name] if module_name in events else []
    
        # started flag
        module[u'started'] = False if module_name in self.__modules_in_errors else True

        # add library is loaded by
        module[u'loadedby'] = self.__dependencies[module_name] if module_name in self.__dependencies else []

        return module

    def get_installable_modules(self):
        """
        Returns dict of installable modules. It also returns modules installed as library.

        Returns:
            dict: dict of modules::

                {
                    module name: {
                        name: '',
                        version: '',
                        ...
                    },
                    ...
                }

        """
        return self._get_modules(lambda name,module,modules: name in modules and (modules[name][u'library'] or not modules[name][u'installed']))

    def get_modules(self):
        """
        Returns dict of installed modules. It also returned modules installed as library.

        Returns:
            dict: dict of modules::

                {
                    module name: {
                        name: '',
                        version: '',
                        ...
                    },
                    ...
                }

        """
        installed_modules = self._get_modules(lambda name,module,modules: name in modules and modules[name][u'installed'])
        modules = {}

        for module_name, module in installed_modules.items():
            try:
                # drop not launched modules
                if module_name not in self.__modules_instances:
                    self.logger.trace(u'Drop not started module "%s"' % module_name)
                    continue
                
                modules[module_name] = self.get_module_infos(module_name)

            except: # pragma: no cover
                self.logger.exception(u'Unable to get data from module "%s"' % module_name)

        return modules

    def _get_modules(self, module_filter=None):
        """
        Returns modules adding possibility to filter them

        Args:
            module_filter (function): filtering function. Params: module name, module data, all modules
        
        Returns:
            dict: dict of modules::

                {
                    module name: {
                        name: '',
                        version: '',
                        ...
                    },
                    ...
                }

        """
        # check params
        if module_filter is not None and not callable(module_filter):
            raise InvalidParameter(u'Parameter "module_filter" must be callable')
        # fix module_filter
        if module_filter is None:
            module_filter = lambda mod_name, mod_data, all_mods: True
        
        # init
        all_modules = copy.deepcopy(self.modules)
        conf = RaspiotConf(self.cleep_filesystem)
        raspiot_config = conf.as_dict()

        # update volatile infos
        filtered_modules = {}
        for module_name, module in {k:v for k,v in all_modules.items() if module_filter(k,v,all_modules)}.items():
            try:
                # pending status
                module[u'pending'] = False
                if module_name in self.__modules_in_errors:
                    # module failed to start, force eventual pending state to false
                    module[u'pending'] = False
                elif module_name in raspiot_config[u'general'][u'modules'] and not module[u'installed']:
                    # install pending
                    module[u'pending'] = True
                # Impossible case ?
                # elif module_name not in raspiot_config[u'general'][u'modules'] and module[u'installed'] and module[u'library']:
                #     # module is installed as library
                #     module[u'pending'] = False
                elif module_name not in raspiot_config[u'general'][u'modules'] and module[u'installed'] and not module[u'library']:
                    # uninstall pending
                    module[u'pending'] = True
                elif module_name in raspiot_config[u'general'][u'updated'] and module[u'installed']:
                    # module updated, need to restart raspiot
                    module[u'pending'] = True

                filtered_modules[module_name] = module

            except: # pragma: no cover
                self.logger.exception(u'Unable to get config of module "%s"' % module_name)

        return filtered_modules
            
    def get_module_commands(self, module):
        """
        Returns list of module commands

        Args:
            module (string): module name

        Returns:
            list: list of commands or empty list if module not found::

                ['command1', 'command2', ...]

        """
        return self.__modules_instances[module].get_module_commands() if module in self.__modules_instances else []

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
            dict: dict of modules/libraries debug flag::
            
                {
                    modulename (bool): debug flag
                    ...
                }

        """
        debugs = {}
        for module in self.modules:
            # only get debug value of installed modules
            if not self.modules[module][u'installed']:
                continue

            # get debug status
            try:
                debugs[module] = {
                    u'debug': self.__modules_instances[module].is_debug_enabled()
                }

            except:
                self.logger.exception('Unable to get module %s debug status:' % module)
                debugs[module] = {
                    u'debug': False
                }

        # append core modules
        debugs.update({
            u'inventory': {
                u'debug': self.is_debug_enabled()
            },
            u'rpc': {
                u'debug': self.__rpcserver.is_debug_enabled()
            }
        })

        return debugs

    def set_rpc_debug(self, debug):
        """
        Set debug on rpcserver

        Args:
            debug (bool): debug enabled or not
        """
        self.__rpcserver.set_debug(debug)

    def set_rpc_cache_control(self, cache_enabled):
        """
        Set RPC server cache control

        Args:
            cache_enabled (bool): True to enable cache
        """
        self.__rpcserver.set_cache_control(cache_enabled)

    def get_renderers(self):
        """
        Return renderers from events broker

        Returns:
            list: list of renderers with their handled profiles
        """
        return self.formatters_broker.get_renderers_profiles()

    def get_modules_events(self):
        """
        Return modules events

        Returns:
            dict: dict of modules events::

                {
                    module1: [event1, event2, ...],
                    module2: [event1],
                    ...
                }

        """
        return self.events_broker.get_modules_events()

    def get_used_events(self):
        """
        Return used events

        Returns:
            list: list of used events
        """
        return self.events_broker.get_used_events()

    def _rpc_wrapper(self, route, request):
        """
        Rpc wrapper is called by rpc server when default / POST route is called.
        Inventory get all loaded RaspIotRpcWrapperModule modules and push the bottle request object.
        See bottle documentation for request object description https://bottlepy.org/docs/dev/tutorial.html#request-data
        """
        for module_name in self.__rpc_wrappers:
            try:
                self.__modules_instances[module_name]._wrap_request(route, request)
            except:
                self.logger.exception(u'RpcWrapper wrap_request function failed:')

    def get_drivers(self):
        """
        Return drivers
        """
        return self.bootstrap[u'drivers'].get_all_drivers()

