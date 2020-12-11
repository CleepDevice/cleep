#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import importlib
import inspect
import copy
from threading import Event
from cleep.core import Cleep, CleepModule, CleepRenderer, CleepRpcWrapper
from cleep.libs.configs.modulesjson import ModulesJson
from cleep.exception import CommandError, MissingParameter, InvalidParameter
from cleep.libs.configs.cleepconf import CleepConf
from cleep.libs.internals.install import Install
import cleep.libs.internals.tools as Tools
from cleep.common import CORE_MODULES, ExecutionStep

__all__ = ['Inventory']

class Inventory(Cleep):
    """
    Inventory handles inventory of:
     - existing devices: knows all devices and module that handles it
     - loaded modules and their commands
     - existing renderers (sms, email, sound...)
    """

    MODULE_AUTHOR = 'Cleep'
    MODULE_VERSION = '0.0.0'
    MODULE_CORE = True

    MODULES_SYNC_TIMEOUT = 60.0
    PYTHON_CLEEP_IMPORT_PATH = 'cleep.modules.'
    PYTHON_CLEEP_MODULES_PATH = 'modules'

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
        Cleep.__init__(self, bootstrap, debug_enabled)
        # self.logger.setLevel(logging.DEBUG)

        # members
        self.__modules_loaded = False
        self.__rpcserver = rpcserver
        self.configured_modules = configured_modules
        self.debug_config = debug_config
        self.bootstrap = bootstrap
        self.events_broker = bootstrap['events_broker']
        self.formatters_broker = bootstrap['formatters_broker']
        # dict to store event to synchronize module startups
        self.__module_join_events = []
        # used to store modules status (library or not) during modules loading
        self.__modules_loaded_as_dependency = {}
        # list of modules: dict(<module name>:dict(<module config>), ...)
        self.modules = {}
        # direct access to modules instances
        self.__modules_instances = {}
        # modules that failed to starts
        # format::
        #   {
        #       module name (string): error (string),
        #       ...
        #   }
        self.__modules_in_error = {}
        # module names that are CleepRpcWrapper instances
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

    def __get_bootstrap(self):
        """
        Get a copy of bootstrap object to pass to module to load
        This function instanciate a new Event for module synchronization and pass all other attributes
        """
        bootstrap = copy.copy(self.bootstrap)
        bootstrap['module_join_event'] = Event()

        return bootstrap

    def __fix_country(self, country):
        return '' if not country else country.lower()

    def __fix_urls(self, site_url, bugs_url, info_url, help_url):
        return {
            'site': site_url,
            'bugs': bugs_url,
            'info': info_url,
            'help': help_url
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
            self.logger.debug('Loading dependency "%s"' % module_name)
        else:
            self.logger.debug('Loading module "%s"' % module_name)

        # handle circular dependency
        if module_name in self.__module_loading_tree:
            self.logger.trace('Circular dependency detected')
            return
        self.__module_loading_tree.append(module_name)
        self.logger.trace('Module loading tree: %s' % self.__module_loading_tree)

        # handle already loaded dependency
        if module_name in self.__modules_loaded_as_dependency:
            self.logger.trace('Trying to loaded dependency module "%s" as a module, it is now considered as module' % module_name)
            self.__modules_loaded_as_dependency[module_name] = False
            return

        # set module is installed
        if module_name not in self.modules and module_name not in local_modules:
            raise Exception('Module "%s" doesn\'t exist. Parent module and module dependencies won\'t be loaded.' % module_name)
        self.modules[module_name]['installed'] = True

        # import module file and get module class
        module_path = '%s%s.%s' % (self.PYTHON_CLEEP_IMPORT_PATH, module_name, module_name)
        self.logger.trace('Importing module "%s"' % module_path)
        module_ = importlib.import_module(module_path)
        module_class_ = getattr(module_, module_name.capitalize())
                    
        # enable or not debug
        debug = False
        if self.debug_config['trace_enabled'] or module_name in self.debug_config['debug_modules']:
            self.logger.debug('Debug enabled for module "%s"' % module_name)
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
                    self.logger.trace('Dependency "%s" already loaded' % dependency)

        # is module external bus implementation
        if 'CleepExternalBus' in [c.__name__ for c in module_class_.__bases__]:
            self.bootstrap['external_bus'] = module_name

        # instanciate module
        self.logger.trace('Instanciating module "%s"' % module_name)
        bootstrap = self.__get_bootstrap()
        self.__modules_instances[module_name] = module_class_(bootstrap, debug)

        # append module join event to make sure all modules are loaded
        self.__module_join_events.append(bootstrap['module_join_event'])

        # fix some metadata
        fixed_urls = self.__fix_urls(
            getattr(module_class_, 'MODULE_URLSITE', None),
            getattr(module_class_, 'MODULE_URLBUGS', None),
            getattr(module_class_, 'MODULE_URLINFO', None),
            getattr(module_class_, 'MODULE_URLHELP', None)
        )
        fixed_country = self.__fix_country(getattr(module_class_, 'MODULE_COUNTRY', None))

        # update metadata with module values
        self.modules[module_name].update({
            'label': getattr(module_class_, 'MODULE_LABEL', module_name.capitalize()),
            'description': module_class_.MODULE_DESCRIPTION,
            'author': getattr(module_class_, 'MODULE_AUTHOR', ''),
            'core': module_name in CORE_MODULES,
            'tags': getattr(module_class_, 'MODULE_TAGS', []),
            'country': fixed_country,
            'urls': fixed_urls,
            'category': getattr(module_class_, 'MODULE_CATEGORY', ''),
            'screenshots': getattr(module_class_, 'MODULE_SCREENSHOTS', []),
            'deps': getattr(module_class_, 'MODULE_DEPS', []),
            'version': getattr(module_class_, 'MODULE_VERSION', '0.0.0'),
        })

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
            self.logger.info('No modules.json still loaded from CleepOS website. Download it now')
            if modules_json.update():
                self.logger.info('File modules.json downloaded successfully')

            else:
                self.logger.error('Failed to update modules.json. No module (except installed ones) will be available')
                return modules_json.get_empty()

        return modules_json.get_json()

    def reload_modules(self):
        """
        Reload modules refreshing only not installed modules
        """
        self.logger.info('Reloading modules')
        # get list of all available modules (from remote list)
        modules_json_content = self._get_modules_json()
        modules_json = modules_json_content['list']
        self.logger.trace('modules.json: %s' % modules_json)

        # iterates over new modules.json
        for module_name, module_data in modules_json.items():
            if module_name not in self.modules:
                # new module, add new entry in existing modules list
                self.logger.debug('Add new module "%s" to list of available modules' % module_name)
                self.modules[module_name] = module_data
                
                # add/force some metadata
                self.modules[module_name].update({
                    'name': module_name,
                    'installed': False,
                    'library': False,
                    'local': False,
                    'core': False,
                    'screenshots': [],
                    'deps': [],
                    'loadedby': [],
                })

    def _load_modules(self):
        """
        Load all modules
        """
        # init
        if self.__modules_loaded:
            raise Exception('Modules loading must be performed only once. If you want to refresh modules list, use reload_modules instead')
        local_modules = []
                
        # get list of all available modules (from remote list)
        modules_json_content = self._get_modules_json()
        self.modules = modules_json_content['list']
        self.logger.trace('Modules.json: %s' % self.modules)

        # append manually installed modules (surely module in development)
        local_modules_path = os.path.abspath(os.path.join(os.path.dirname(__file__), self.PYTHON_CLEEP_MODULES_PATH))
        self.logger.trace('Local modules path: %s' % local_modules_path)
        if not os.path.exists(local_modules_path): # pragma: no cover
            raise CommandError('Invalid modules path')
        for f in os.listdir(local_modules_path):
            fpath = os.path.join(local_modules_path, f)
            module_name = os.path.split(fpath)[-1]
            module_py = os.path.join(fpath, '%s.py' % module_name)
            if os.path.isdir(fpath) and os.path.exists(module_py) and module_name not in self.modules:
                self.logger.debug('Found module "%s" installed manually' % module_name)
                local_modules.append(module_name)
                self.modules[module_name] = {}
        self.logger.trace('Local modules: %s' % local_modules)

        # add default metadata
        for module_name in self.modules:
            self.modules[module_name].update({
                'name': module_name,
                'installed': False,
                'library': False,
                'local': module_name in local_modules,
                'core': False,
                'screenshots': [],
                'deps': [],
                'loadedby': [],
            })

        # execution step: BOOT->INIT
        self.bootstrap['execution_step'].step = ExecutionStep.INIT

        # load core modules
        self.logger.trace('CORE_MODULES: %s' % CORE_MODULES)
        for module_name in CORE_MODULES:
            try:
                # load module
                self.__load_module(module_name, local_modules)

            except:
                # failed to load mandatory module
                self.logger.error('Unable to load core module "%s". System will be instable' % module_name)
                self.logger.exception('Core module "%s" exception:' % module_name)
                self.crash_report.report_exception({
                    'message': 'Unable to load core module "%s". System will be instable' % module_name,
                    'module_name': module_name
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
                if module_name in self.__modules_instances and isinstance(self.__modules_instances[module_name], CleepRenderer):
                    config = self.__modules_instances[module_name]._get_renderer_config()
                    self.formatters_broker.register_renderer(module_name, config['profiles'])

                # store rpc wrappers
                if module_name in self.__modules_instances and isinstance(self.__modules_instances[module_name], CleepRpcWrapper):
                    self.logger.debug('Store RpcWrapper instance "%s"' % module_name)
                    self.__rpc_wrappers.append(module_name)

            except Exception as e:
                # flag modules has in error
                self.__modules_in_error[module_name] = str(e)

                # failed to load module
                self.logger.exception('Unable to load module "%s" or one of its dependencies:' % module_name)

            finally:
                # clear module loading tree (replace it with clear() available in python3)
                del self.__module_loading_tree[:]

        # execution step: INIT->CONFIG
        self.bootstrap['execution_step'].step = ExecutionStep.CONFIG

        # finalize loading process
        for module_name in self.modules:
            # fix final library status
            if module_name in self.__modules_loaded_as_dependency:
                self.modules[module_name]['library'] = self.__modules_loaded_as_dependency[module_name]

        # start installed modules
        for module_name, module_ in self.__modules_instances.items():
            module_.start()

        # wait for all modules to be completely loaded
        self.logger.info('Waiting for end of modules configuration...')
        for module_join_event in self.__module_join_events:
            module_join_event.wait()
        self.logger.info('All modules are configured.')
        self.bootstrap['core_join_event'].set()

        # execution step: CONFIG->RUN
        self.bootstrap['execution_step'].step = ExecutionStep.RUN

        self.__modules_loaded = True
        self.logger.debug('All modules are loaded')

    def all_started(self):
        """
        Returns when Cleep is completely loaded and started

        Note:
            This method is blocking !
        """
        if not self.bootstrap['core_join_event'].wait(self.MODULES_SYNC_TIMEOUT):
            self.logger.fatal('Startup takes too much time. A module may be blocked. Cleep may not run properly')
            return False

        return True

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
            raise InvalidParameter('Module "%s" doesn\'t exist' % module_name)

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
                if isinstance(self.__modules_instances[module_name], CleepModule):
                    devices[module_name] = self.__modules_instances[module_name].get_module_devices()
            
            except:
                self.logger.exception('Unable to get devices of module "%s"' % module_name)

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
        module['config'] = self.__modules_instances[module_name].get_module_config() if module_name in self.__modules_instances else {}
            
        # add module events
        module['events'] = events[module_name] if module_name in events else []
    
        # started flag
        module['started'] = False if module_name in self.__modules_in_error.keys() else True

        # add library is loaded by
        module['loadedby'] = self.__dependencies[module_name] if module_name in self.__dependencies else []

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
        return self._get_modules(lambda name,module,modules: name in modules and (modules[name]['library'] or not modules[name]['installed']))

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
        installed_modules = self._get_modules(lambda name,module,modules: name in modules and modules[name]['installed'])
        modules = {}

        for module_name, module in installed_modules.items():
            try:
                # drop not launched modules
                #if module_name not in self.__modules_instances:
                #    self.logger.trace('Drop not started module "%s"' % module_name)
                #    continue
                modules[module_name] = self.get_module_infos(module_name)

            except: # pragma: no cover
                self.logger.exception('Unable to get data from module "%s"' % module_name)

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
            raise InvalidParameter('Parameter "module_filter" must be callable')
        # fix module_filter
        if module_filter is None:
            module_filter = lambda mod_name, mod_data, all_mods: True
        
        # init
        all_modules = copy.deepcopy(self.modules)
        conf = CleepConf(self.cleep_filesystem)
        cleep_config = conf.as_dict()

        # apply specified filter
        filtered_modules = {}
        for module_name, module in {k:v for k,v in all_modules.items() if module_filter(k,v,all_modules)}.items():
            filtered_modules[module_name] = module

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
            if not self.modules[module]['installed']:
                continue

            # get debug status
            try:
                debugs[module] = {
                    'debug': self.__modules_instances[module].is_debug_enabled()
                }

            except:
                self.logger.exception('Unable to get module %s debug status:' % module)
                debugs[module] = {
                    'debug': False
                }

        # append core modules
        debugs.update({
            'inventory': {
                'debug': self.is_debug_enabled()
            },
            'rpc': {
                'debug': self.__rpcserver.is_debug_enabled()
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

    def rpc_wrapper(self, route, request):
        """
        Rpc wrapper is called by rpc server when default / POST route is called.
        Inventory get all loaded CleepRpcWrapperModule modules and push the bottle request object.
        See bottle documentation for request object description https://bottlepy.org/docs/dev/tutorial.html#request-data
        """
        for module_name in self.__rpc_wrappers:
            try:
                self.__modules_instances[module_name]._wrap_request(route, request)
            except:
                self.logger.exception('RpcWrapper wrap_request function failed:')

    def get_drivers(self):
        """
        Return drivers
        """
        return self.bootstrap['drivers'].get_all_drivers()

