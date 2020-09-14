#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests', ''))
from inventory import Inventory
from cleep.libs.tests.lib import TestLib
from cleep.exception import InvalidParameter
import unittest
import logging
from unittest.mock import Mock, patch
import io, shutil
import time


class InventoryTests(unittest.TestCase):

    MODULE = u"""
from cleep.core import CleepModule, CleepRpcWrapper, CleepRenderer

class %(module_name)s(%(inherit)s):
    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'0.0.0'
    MODULE_CATEGORY = u'APPLICATION'
    MODULE_DEPS = %(module_deps)s
    MODULE_DESCRIPTION = u'desc'
    MODULE_LONGDESCRIPTION = u'long desc'
    MODULE_TAGS = ['tag']
    MODULE_COUNTRY = None

    RENDERER_PROFILES = []

    def __init__(self, bootstrap, debug_enabled):
        %(inherit)s.__init__(self, bootstrap, debug_enabled)
        self.exception = %(exception)s
        %(startup_error)s

    def is_debug_enabled(self):
        if self.exception:
            raise Exception('Test exception')
        return self.debug_enabled

    def _protected(self):
        pass

    def __private(self):
        pass

    def dummy(self):
        pass

    def _wrap_request(self, route, request):
        if self.exception:
            raise Exception('Test exception')
        self.logger.info('--> Request wrapped for route "'+route+'" and request "'+str(request)+'"')

    def get_module_devices(self):
        if self.exception:
            raise Exception('Test exception')
        return {
            '123-456-789': {}
        }
    """

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.i = None

    def tearDown(self):
        if self.i:
            self.i.unload_modules()
        if os.path.exists('modules'):
            shutil.rmtree('modules')
        for to_unload in [mod for mod in sys.modules if mod.startswith('modules.module')]:
            del sys.modules[to_unload]

    def _init_context(self, debug_enabled=False, configured_modules=[], debug_modules=[],
            mod1_deps=[], mod2_deps=[], mod3_deps=[],
            mod1_exception=False, mod2_exception=False, mod3_exception=False,
            mod1_inherit='CleepModule', mod2_inherit='CleepModule', mod3_inherit='CleepModule',
            mod1_startup_error=''):
        os.mkdir('modules')
        with io.open(os.path.join('modules', '__init__.py'), 'w') as fd:
            fd.write(u'')
        # module1
        os.mkdir(os.path.join('modules', 'module1'))
        with io.open(os.path.join('modules', 'module1', 'module1.py'), 'w') as fd:
            fd.write(self.MODULE % {'module_name': 'Module1', 'module_deps': mod1_deps, 'exception':mod1_exception, 'inherit':mod1_inherit, 'startup_error':mod1_startup_error})
        with io.open(os.path.join('modules', 'module1', '__init__.py'), 'w') as fd:
            fd.write(u'')
        # module2
        os.mkdir(os.path.join('modules', 'module2'))
        with io.open(os.path.join('modules', 'module2', 'module2.py'), 'w') as fd:
            fd.write(self.MODULE % {'module_name': 'Module2', 'module_deps': mod2_deps, 'exception':mod2_exception, 'inherit':mod2_inherit, 'startup_error':''})
        with io.open(os.path.join('modules', 'module2', '__init__.py'), 'w') as fd:
            fd.write(u'')
        # module3
        os.mkdir(os.path.join('modules', 'module3'))
        with io.open(os.path.join('modules', 'module3', 'module3.py'), 'w') as fd:
            fd.write(self.MODULE % {'module_name': 'Module3', 'module_deps': mod3_deps, 'exception':mod3_exception, 'inherit':mod3_inherit, 'startup_error':''})
        with io.open(os.path.join('modules', 'module3', '__init__.py'), 'w') as fd:
            fd.write(u'')

        self.rpcserver = Mock()
        self.rpcserver.is_debug_enabled.return_value = True
        self.cleep_filesystem = Mock()
        self.events_broker = Mock()
        self.events_broker.get_modules_events.return_value = {
            'module1': ['event1'],
            'module2': [],
            'module3': ['event3'],
            'module4': ['event4']
        }
        self.drivers = Mock()
        self.crash_report = Mock()
        self.formatters_broker = Mock()

        def side_effect(*args, **kwargs):
            time.sleep(3.0)
        self.bus = Mock()
        self.bus.pull.side_effect = side_effect

        self.bootstrap = {
            'message_bus': self.bus,
            'module_join_event': Mock(),
            'drivers': self.drivers,
            'cleep_filesystem': self.cleep_filesystem,
            'execution_step': Mock(),
            'events_broker': self.events_broker,
            'crash_report': self.crash_report,
            'test_mode': False,
            'formatters_broker': self.formatters_broker
        }

        debug_config = {
            'trace_enabled': False,
            'debug_modules': debug_modules,
        }
        self.i = Inventory(self.bootstrap, self.rpcserver, debug_enabled, configured_modules, debug_config=debug_config)
        Inventory.PYTHON_CLEEP_IMPORT_PATH = 'modules.'
        Inventory.PYTHON_CLEEP_MODULES_PATH = 'tests/modules'

    def test_event_received_module_install(self):
        self._init_context()
        self.i.modules['module1'] = {
            'processing': None
        }

        event = {
            'event': 'system.module.install',
            'params': {
                'module': 'module1',
                'status': 1
            }
        }
        self.i.event_received(event)
        self.assertEqual(self.i.modules['module1']['processing'], 'install')

    def test_event_received_module_uninstall(self):
        self._init_context()
        self.i.modules['module1'] = {
            'processing': None
        }

        event = {
            'event': 'system.module.uninstall',
            'params': {
                'module': 'module1',
                'status': 1
            }
        }
        self.i.event_received(event)
        self.assertEqual(self.i.modules['module1']['processing'], 'uninstall')

    def test_event_received_module_update(self):
        self._init_context()
        self.i.modules['module1'] = {
            'processing': None
        }

        event = {
            'event': 'system.module.update',
            'params': {
                'module': 'module1',
                'status': 1
            }
        }
        self.i.event_received(event)
        self.assertEqual(self.i.modules['module1']['processing'], 'update')

    def test_event_received_module_processing_reset(self):
        self._init_context()
        self.i.modules['module1'] = {
            'processing': 'install'
        }

        event = {
            'event': 'system.module.update',
            'params': {
                'module': 'module1',
                'status': 2
            }
        }
        self.i.event_received(event)
        self.assertEqual(self.i.modules['module1']['processing'], None)

    @patch('inventory.ModulesJson')
    def test_get_modules_json_exists_true(self, modulesjson_mock):
        json_content = {
            'update': 0,
            'list': ['module1', 'module2']
        }
        modulesjson_mock.return_value.get_json.return_value = json_content
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context()
        
        j = self.i._get_modules_json()
        logging.debug('ModulesJson: %s' % j)
        self.assertEqual(j, json_content)

    @patch('inventory.ModulesJson')
    def test_get_modules_json_exists_false(self, modulesjson_mock):
        json_content = {
            'update': 0,
            'list': ['module1', 'module2']
        }
        modulesjson_mock.return_value.get_json.return_value = json_content
        modulesjson_mock.return_value.exists.return_value = False
        self._init_context()
        
        j = self.i._get_modules_json()
        logging.debug('ModulesJson: %s' % j)
        self.assertTrue(modulesjson_mock.return_value.update.called)
        self.assertEqual(j, json_content)

    @patch('inventory.ModulesJson')
    def test_get_modules_json_exists_false_update_failed(self, modulesjson_mock):
        json_content = {
            'update': 123,
            'list': []
        }
        modulesjson_mock.return_value.get_empty.return_value = json_content
        modulesjson_mock.return_value.exists.return_value = False
        modulesjson_mock.return_value.update.return_value = False
        self._init_context()
        
        j = self.i._get_modules_json()
        logging.debug('ModulesJson: %s' % j)
        self.assertTrue(modulesjson_mock.return_value.update.called)
        self.assertFalse(modulesjson_mock.return_value.get_json.called)
        self.assertEqual(j, json_content)

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module2'])

        # we use _configure instead of "self.i._load_modules()" just to cover this function
        self.i._configure()
        logging.debug('Modules: %s' % self.i.modules)
        
        self.assertEqual(len(self.i.modules), 3)
        self.assertTrue('module1' in self.i.modules)
        self.assertTrue('module2' in self.i.modules)
        self.assertTrue('module3' in self.i.modules)

        # check modules.json module content
        self.assertTrue('core' in self.i.modules['module1'])
        self.assertTrue('description' in self.i.modules['module1'])
        self.assertEqual(self.i.modules['module1']['description'], 'desc')
        self.assertTrue('tags' in self.i.modules['module1'])
        self.assertTrue(len(self.i.modules['module1']['tags']), 1)
        self.assertTrue(self.i.modules['module1']['tags'][0], 'tag')
        self.assertTrue('processing' in self.i.modules['module1'])
        self.assertTrue('library' in self.i.modules['module1'])
        self.assertTrue('installed' in self.i.modules['module1'])
        self.assertTrue('urls' in self.i.modules['module1'])
        self.assertTrue('screenshots' in self.i.modules['module1'])
        self.assertTrue('loadedby' in self.i.modules['module1'])
        self.assertTrue('category' in self.i.modules['module1'])
        self.assertTrue('name' in self.i.modules['module1'])
        self.assertTrue('author' in self.i.modules['module1'])
        self.assertTrue('country' in self.i.modules['module1'])
        self.assertTrue('updatable' in self.i.modules['module1'])
        self.assertTrue('version' in self.i.modules['module1'])
        self.assertEqual(self.i.modules['module1']['version'], '0.0.0')
        self.assertTrue('deps' in self.i.modules['module1'])
        self.assertTrue('local' in self.i.modules['module1'])
        self.assertTrue('pending' in self.i.modules['module1'])

        # check unloaded local module content
        self.assertTrue('core' in self.i.modules['module3'])
        self.assertFalse('description' in self.i.modules['module3'])
        self.assertFalse('tags' in self.i.modules['module3'])
        self.assertTrue('processing' in self.i.modules['module3'])
        self.assertTrue('library' in self.i.modules['module3'])
        self.assertTrue('installed' in self.i.modules['module3'])
        self.assertFalse('urls' in self.i.modules['module3'])
        # self.assertTrue('screenshots' in self.i.modules['module3'])
        self.assertTrue('loadedby' in self.i.modules['module3'])
        self.assertFalse('category' in self.i.modules['module3'])
        self.assertTrue('name' in self.i.modules['module3'])
        self.assertFalse('author' in self.i.modules['module3'])
        self.assertFalse('country' in self.i.modules['module3'])
        self.assertTrue('updatable' in self.i.modules['module3'])
        self.assertFalse('version' in self.i.modules['module3'])
        self.assertTrue('deps' in self.i.modules['module3'])
        self.assertTrue('local' in self.i.modules['module3'])
        self.assertTrue('pending' in self.i.modules['module3'])

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_with_cleeprenderer_module(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module2'], mod1_inherit='CleepRenderer')

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)
        
        self.assertEqual(len(self.i.modules), 3)
        self.assertTrue('module1' in self.i.modules)
        self.assertTrue('module2' in self.i.modules)
        self.assertTrue('module3' in self.i.modules)

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_with_rpcwrapper_module(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module2'], mod1_inherit='CleepRpcWrapper')

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)
        
        self.assertEqual(len(self.i.modules), 3)
        self.assertTrue('module1' in self.i.modules)
        self.assertTrue('module2' in self.i.modules)
        self.assertTrue('module3' in self.i.modules)

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_with_unknown_module(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'dummy'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.assertTrue(self.i.is_module_loaded('module1'))
        self.assertFalse(self.i.is_module_loaded('module2'))
        self.assertFalse(self.i.is_module_loaded('module3'))

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_with_deps(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(mod1_deps=['module2'], configured_modules=['module1'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.assertFalse(self.i.modules['module1']['library'])
        self.assertTrue(self.i.modules['module2']['library'])
        self.assertTrue(self.i.is_module_loaded('module1'))
        self.assertTrue(self.i.is_module_loaded('module2'))
        self.assertFalse(self.i.is_module_loaded('module3'))

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_with_unknown_dep(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1'], mod1_deps=['dummy'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.assertFalse(self.i.is_module_loaded('module1'))
        self.assertFalse(self.i.is_module_loaded('module2'))
        self.assertFalse(self.i.is_module_loaded('module3'))

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_with_circular_deps(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(mod1_deps=['module2'], mod2_deps=['module1'], configured_modules=['module1', 'module2'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.assertFalse(self.i.modules['module1']['library'])
        self.assertFalse(self.i.modules['module2']['library'])
        self.assertTrue(self.i.is_module_loaded('module1'))
        self.assertTrue(self.i.is_module_loaded('module2'))
        self.assertFalse(self.i.is_module_loaded('module3'))

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_with_dep_already_loaded(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}, 'module3':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(mod1_deps=['module3'], mod2_deps=['module3'], configured_modules=['module1', 'module2'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.assertFalse(self.i.modules['module1']['library'])
        self.assertFalse(self.i.modules['module2']['library'])
        self.assertTrue(self.i.modules['module3']['library'])
        self.assertTrue(self.i.is_module_loaded('module1'))
        self.assertTrue(self.i.is_module_loaded('module2'))
        self.assertTrue(self.i.is_module_loaded('module3'))

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_with_local_module(self, modulesjson_mock):
        # module3 is installed locally
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module2'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.assertFalse(self.i.modules['module1']['local'])
        self.assertFalse(self.i.modules['module2']['local'])
        self.assertTrue(self.i.modules['module3']['local'])
        self.assertTrue(self.i.is_module_loaded('module1'))
        self.assertTrue(self.i.is_module_loaded('module2'))
        self.assertFalse(self.i.is_module_loaded('module3'))

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_with_local_module_as_dep(self, modulesjson_mock):
        # module3 is installed locally
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(mod1_deps=['module3'], configured_modules=['module1', 'module2'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.assertFalse(self.i.modules['module1']['local'])
        self.assertFalse(self.i.modules['module2']['local'])
        self.assertTrue(self.i.modules['module3']['local'])
        self.assertTrue(self.i.is_module_loaded('module1'))
        self.assertTrue(self.i.is_module_loaded('module2'))
        self.assertTrue(self.i.is_module_loaded('module3'))

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_with_cascading_deps(self, modulesjson_mock):
        # deps tree : module1 --> module2 --> module3
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(mod1_deps=['module2'], mod2_deps=['module3'], configured_modules=['module1'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.assertTrue(self.i.is_module_loaded('module1'))
        self.assertTrue(self.i.is_module_loaded('module2'))
        self.assertTrue(self.i.is_module_loaded('module3'))

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_with_cascading_deps_final_circular(self, modulesjson_mock):
        # deps tree : module1 --> module2 --> module3 --> module1
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(mod1_deps=['module2'], mod2_deps=['module3'], mod3_deps=['module1'], configured_modules=['module1'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.assertTrue(self.i.is_module_loaded('module1'))
        self.assertTrue(self.i.is_module_loaded('module2'))
        self.assertTrue(self.i.is_module_loaded('module3'))

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_with_tree_deps(self, modulesjson_mock):
        # deps tree : module1 --> module2
        #                     --> module3
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(mod1_deps=['module2', 'module3'], configured_modules=['module1'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.assertTrue(self.i.is_module_loaded('module1'))
        self.assertTrue(self.i.is_module_loaded('module2'))
        self.assertTrue(self.i.is_module_loaded('module3'))

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_with_tree_deps_circular_first_leaf(self, modulesjson_mock):
        # deps tree : module1 --> module2 --> module1
        #                     --> module3 
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(mod1_deps=['module2', 'module3'], mod2_deps=['module1'], configured_modules=['module1'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.assertTrue(self.i.is_module_loaded('module1'))
        self.assertTrue(self.i.is_module_loaded('module2'))
        self.assertTrue(self.i.is_module_loaded('module3'))

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_with_tree_deps_circular_other_leaf(self, modulesjson_mock):
        # deps tree : module1 --> module2
        #                     --> module3 --> module1
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(mod1_deps=['module2', 'module3'], mod3_deps=['module1'], configured_modules=['module1'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.assertTrue(self.i.is_module_loaded('module1'))
        self.assertTrue(self.i.is_module_loaded('module2'))
        self.assertTrue(self.i.is_module_loaded('module3'))

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_updatable_flag(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{'version': '1.0.0' }, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.assertEqual(self.i.modules['module1']['version'], '0.0.0')
        self.assertEqual(self.i.modules['module1']['updatable'], '1.0.0')

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_load_modules_load_again(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{'version': '1.0.0' }, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)
        with self.assertRaises(Exception) as cm:
            self.i._load_modules()
        self.assertEqual(str(cm.exception), 'Modules loading must be performed only once. If you want to refresh modules list, use reload_modules instead')

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', ['module1'])
    def test_load_modules_core_modules(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{'version': '1.0.0' }, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module2'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        # module1 should be loaded event if not configured (core module so mandatory)
        self.assertTrue(self.i.is_module_loaded('module1'))
        self.assertTrue(self.i.is_module_loaded('module2'))
        self.assertFalse(self.i.is_module_loaded('module3'))

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', ['module1'])
    @patch('cleep.core.CORE_MODULES', ['module1'])
    def test_load_modules_core_modules_exception(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{'version': '1.0.0' }, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module2'], mod1_startup_error='raise Exception("Startup exception")')

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        # module1 should be loaded event if not configured (core module so mandatory)
        self.assertFalse(self.i.is_module_loaded('module1'))
        self.assertTrue(self.i.is_module_loaded('module2'))
        self.assertFalse(self.i.is_module_loaded('module3'))
        self.assertTrue(self.crash_report.report_exception.called)

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_reload_modules(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.side_effect = [
            {
                'update': 1587168000,
                'list': {'module1':{'version':'0.0.0'}, 'module2':{'version':'0.0.0'}}
            },
            {
                'update': 1587254400,
                'list': {'module1':{'version': '1.0.0'}, 'module2':{'version':'0.0.0'}, 'module4': {}}
            },
        ]
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module2'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)
        self.assertEqual(len(self.i.modules), 3)

        self.i.reload_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.assertEqual(len(self.i.modules), 4)
        self.assertTrue('module1' in self.i.modules)
        self.assertTrue('module2' in self.i.modules)
        self.assertTrue('module3' in self.i.modules)
        self.assertTrue('module4' in self.i.modules)
        self.assertEqual(self.i.modules['module1']['updatable'], '1.0.0')
        self.assertEqual(self.i.modules['module2']['updatable'], '')

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_unload_modules(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{'version': '1.0.0' }, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.i.unload_modules()

        self.assertFalse(self.i.is_module_loaded('module1'))
        self.assertFalse(self.i.is_module_loaded('module2'))
        self.assertFalse(self.i.is_module_loaded('module3'))

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_get_devices(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module2'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        devices = self.i.get_devices()
        logging.debug('Devices: %s' % devices)

        self.assertEqual(len(devices), 2)
        self.assertTrue('module1' in devices)
        self.assertTrue('module2' in devices)
        self.assertEqual(devices['module1'], {'123-456-789': {}})
        self.assertEqual(devices['module2'], {'123-456-789': {}})

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_get_devices_exception(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module2'], mod2_exception=True)

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        devices = self.i.get_devices()
        logging.debug('Devices: %s' % devices)

        self.assertEqual(len(devices), 1)
        self.assertTrue('module1' in devices)
        self.assertFalse('module2' in devices)
        self.assertEqual(devices['module1'], {'123-456-789': {}})

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_get_devices_no_cleepmodule(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module2'], mod2_inherit='CleepRpcWrapper')

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        devices = self.i.get_devices()
        logging.debug('Devices: %s' % devices)

        self.assertEqual(len(devices), 1)
        self.assertTrue('module1' in devices)
        self.assertFalse('module2' in devices)
        self.assertEqual(devices['module1'], {'123-456-789': {}})

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_get_module_device(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        module = self.i.get_module_device('123-456-789')
        logging.debug('Module: %s' % module)

        self.assertEqual(module, 'module1')

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_get_module_device_unknown_device(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        module = self.i.get_module_device('789-456-123')
        logging.debug('Module: %s' % module)

        self.assertIsNone(module)

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_get_module_devices(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        devices = self.i.get_module_devices('module1')
        logging.debug('Devices: %s' % devices)

        self.assertEqual(len(devices), 1)
        self.assertTrue('123-456-789' in devices)

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_get_module_devices_unknown_module(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}, 'module3': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1'])

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        with self.assertRaises(InvalidParameter) as cm:
            self.i.get_module_devices('dummy')
        self.assertEqual(cm.exception.message, 'Module "dummy" doesn\'t exist')

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_get_module_infos(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2': {}, 'module3':{}, 'module4': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module3'], mod1_deps=['module2'])
        self.i._load_modules()

        infos = self.i.get_module_infos('module2')
        logging.debug('Infos: %s' % infos)

        self.assertTrue('core' in infos)
        self.assertTrue('description' in infos)
        self.assertTrue('tags' in infos)
        self.assertTrue('processing' in infos)
        self.assertTrue('library' in infos)
        self.assertTrue('installed' in infos)
        self.assertTrue('urls' in infos)
        self.assertTrue('screenshots' in infos)
        self.assertTrue('loadedby' in infos)
        self.assertTrue('category' in infos)
        self.assertTrue('name' in infos)
        self.assertTrue('author' in infos)
        self.assertTrue('country' in infos)
        self.assertTrue('updatable' in infos)
        self.assertTrue('version' in infos)
        self.assertTrue('deps' in infos)
        self.assertTrue('local' in infos)
        self.assertTrue('pending' in infos)
        # volatile data
        self.assertTrue('events' in infos)
        self.assertTrue('started' in infos)
        self.assertTrue('config' in infos)
        self.assertTrue('module1' in infos['loadedby'])

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_get_module_infos_local_module(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module3'])
        self.i._load_modules()

        infos = self.i.get_module_infos('module3')
        logging.debug('Infos: %s' % infos)

        self.assertTrue('core' in infos)
        self.assertTrue('description' in infos)
        self.assertTrue('tags' in infos)
        self.assertTrue('processing' in infos)
        self.assertTrue('library' in infos)
        self.assertTrue('installed' in infos)
        self.assertTrue('urls' in infos)
        self.assertTrue('screenshots' in infos)
        self.assertTrue('loadedby' in infos)
        self.assertTrue('category' in infos)
        self.assertTrue('name' in infos)
        self.assertTrue('author' in infos)
        self.assertTrue('country' in infos)
        self.assertTrue('updatable' in infos)
        self.assertTrue('version' in infos)
        self.assertTrue('deps' in infos)
        self.assertTrue('local' in infos)
        self.assertTrue('pending' in infos)
        # volatile data
        self.assertTrue('events' in infos)
        self.assertTrue('started' in infos)
        self.assertTrue('config' in infos)
        self.assertEqual(len(infos['loadedby']), 0)

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_get_module_infos_unknown_module(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module3'])
        self.i._load_modules()

        infos = self.i.get_module_infos('module4')
        logging.debug('Infos: %s' % infos)

        self.assertEqual(infos, {})

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    @patch('inventory.CleepConf')
    def test_get_installable_modules(self, cleep_conf_mock, modulesjson_mock):
        cleep_conf_mock.return_value.as_dict.return_value = {
            'general': {
                'modules': ['module1', 'module2'],
                'updated': ['module1'],
            }
        }
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2': {}, 'module3':{}, 'module4': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module3'], mod1_deps=['module2'])
        self.i._load_modules()

        modules = self.i.get_installable_modules()
        logging.debug('Modules: %s' % modules)

        self.assertFalse('module1' in modules)
        self.assertTrue('module2' in modules) # exists in list because lib is installable
        self.assertFalse('module3' in modules)
        self.assertTrue('module4' in modules)
        self.assertTrue(modules['module2']['installed']) # its a lib so installed
        self.assertFalse(modules['module4']['installed'])
        self.assertFalse('config' in modules['module2'])
        self.assertFalse('config' in modules['module4'])
        self.assertFalse('started' in modules['module2'])
        self.assertFalse('started' in modules['module4'])

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    @patch('inventory.CleepConf')
    def test_get_modules(self, cleep_conf_mock, modulesjson_mock):
        cleep_conf_mock.return_value.as_dict.return_value = {
            'general': {
                'modules': ['module1', 'module2'],
                'updated': ['module1'],
            }
        }
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2': {}, 'module3':{}, 'module4': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module3'], mod1_deps=['module2'])
        self.i._load_modules()

        modules = self.i.get_modules()
        logging.debug('Modules: %s' % modules)

        self.assertTrue('module1' in modules)
        self.assertTrue('module2' in modules)
        self.assertTrue('module3' in modules)
        self.assertFalse('module4' in modules)
        self.assertTrue(modules['module1']['installed'])
        self.assertTrue(modules['module2']['installed'])
        self.assertTrue(modules['module3']['installed'])
        self.assertEqual(modules['module1']['events'], ['event1'])
        self.assertEqual(modules['module2']['events'], [])
        self.assertEqual(modules['module3']['events'], ['event3'])
        self.assertTrue('config' in modules['module1'])
        self.assertTrue('config' in modules['module2'])
        self.assertTrue('config' in modules['module3'])
        self.assertTrue(modules['module1']['started'])
        self.assertTrue(modules['module2']['started'])
        self.assertTrue(modules['module3']['started'])

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    @patch('inventory.CleepConf')
    def test_get_modules_module_failed(self, cleep_conf_mock, modulesjson_mock):
        cleep_conf_mock.return_value.as_dict.return_value = {
            'general': {
                'modules': ['module1', 'module2'],
                'updated': ['module1'],
            }
        }
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2': {}, 'module3':{}, 'module4': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module3'], mod1_deps=['module2'], mod1_startup_error='raise Exception("Startup exception")')
        self.i._load_modules()

        modules = self.i.get_modules()
        logging.debug('Modules: %s' % modules)

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    @patch('inventory.CleepConf')
    def test_get_modules_no_filter(self, cleep_conf_mock, modulesjson_mock):
        cleep_conf_mock.return_value.as_dict.return_value = {
            'general': {
                'modules': ['module1', 'module2'],
                'updated': ['module1'],
            }
        }
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2': {}, 'module3':{}, 'module4': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module3', 'module4'])
        self.i._load_modules()

        modules = self.i._get_modules()
        logging.debug('Modules: %s' % modules)
        
        self.assertEqual(len(modules), 4)
        self.assertTrue('module1' in modules)
        self.assertTrue('module2' in modules)
        self.assertTrue('module3' in modules)

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    @patch('inventory.CleepConf')
    def test_get_modules_invalid_filter(self, cleep_conf_mock, modulesjson_mock):
        cleep_conf_mock.return_value.as_dict.return_value = {
            'general': {
                'modules': ['module1', 'module2'],
                'updated': ['module2'],
            }
        }
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2': {}, 'module3':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module3'])
        self.i._load_modules()

        with self.assertRaises(InvalidParameter) as cm:
            self.i._get_modules('dummy')
        self.assertEqual(cm.exception.message, 'Parameter "module_filter" must be callable')

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    @patch('inventory.CleepConf')
    def test_get_modules_with_filter(self, cleep_conf_mock, modulesjson_mock):
        cleep_conf_mock.return_value.as_dict.return_value = {
            'general': {
                'modules': ['module1', 'module2'],
                'updated': ['module2'],
            }
        }
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2': {}, 'module4': {}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module3'], mod1_deps=['module2'])
        self.i._load_modules()
    
        # exclude library
        mod_filter = lambda mod_name, mod_data, all_mods: not mod_data['library']
        modules = self.i._get_modules(mod_filter)
        logging.debug('Modules: %s' % modules)
        self.assertEqual(len(modules), 3)
        self.assertTrue('module1' in modules)
        self.assertFalse('module2' in modules)
        self.assertTrue('module3' in modules)

        # get only local modules
        mod_filter = lambda mod_name, mod_data, all_mods: mod_data['local']
        modules = self.i._get_modules(mod_filter)
        logging.debug('Modules: %s' % modules)
        self.assertEqual(len(modules), 1)
        self.assertFalse('module1' in modules)
        self.assertFalse('module2' in modules)
        self.assertTrue('module3' in modules)

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_get_module_commands(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2': {}, 'module3':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module3'])
        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        commands = self.i.get_module_commands('module1')
        logging.debug('Commands: %s' % commands)

        self.assertEqual(len(commands), 1)
        self.assertTrue('dummy' in commands)

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_get_module_commands_unknown_module(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2': {}, 'module3':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module3'])
        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        commands = self.i.get_module_commands('dummy')
        logging.debug('Commands: %s' % commands)

        self.assertEqual(commands, [])

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_get_modules_debug(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2': {}, 'module3':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module3'], debug_modules=['module3'])
        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        debugs = self.i.get_modules_debug()
        logging.debug('Debugs: %s' % debugs)

        self.assertTrue('rpc' in debugs)
        self.assertTrue('inventory' in debugs)
        self.assertTrue('module1' in debugs)
        self.assertFalse('module2' in debugs)
        self.assertTrue('module3' in debugs)
        self.assertTrue(debugs['rpc']['debug'])
        self.assertFalse(debugs['inventory']['debug'])
        self.assertFalse(debugs['module1']['debug'])
        self.assertTrue(debugs['module3']['debug'])

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_get_modules_debug_exception(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2': {}, 'module3':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module3'], mod3_exception=True)
        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        debugs = self.i.get_modules_debug()
        logging.debug('Debugs: %s' % debugs)

        self.assertTrue(debugs['rpc']['debug'])
        self.assertFalse(debugs['inventory']['debug'])
        self.assertFalse(debugs['module1']['debug'])
        self.assertFalse(debugs['module3']['debug'])

    def test_set_rpc_debug(self):
        self._init_context()

        self.i.set_rpc_debug(True)
        self.rpcserver.set_debug.assert_called_with(True)

        self.i.set_rpc_debug(False)
        self.rpcserver.set_debug.assert_called_with(False)

    def test_set_rpc_cache_control(self):
        self._init_context()

        self.i.set_rpc_cache_control(True)
        self.rpcserver.set_cache_control.assert_called_with(True)

        self.i.set_rpc_cache_control(False)
        self.rpcserver.set_cache_control.assert_called_with(False)

    def test_get_renderers(self):
        self._init_context()

        self.i.get_renderers()
        self.formatters_broker.get_renderers_profiles.assert_called_with()

    def test_get_modules_events(self):
        self._init_context()

        self.i.get_modules_events()
        self.events_broker.get_modules_events.assert_called_with()

    def test_get_used_events(self):
        self._init_context()

        self.i.get_used_events()
        self.events_broker.get_used_events.assert_called_with()

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_rpc_wrapper(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module2'], mod1_inherit='CleepRpcWrapper')

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.i._rpc_wrapper('a_route', {})
        # can't perform some check call was a success. We add info log message on stdout

    @patch('inventory.ModulesJson')
    @patch('inventory.CORE_MODULES', [])
    def test_rpc_wrapper_exception(self, modulesjson_mock):
        modulesjson_mock.return_value.get_json.return_value = {
            'list': {'module1':{}, 'module2':{}}
        }
        modulesjson_mock.return_value.exists.return_value = True
        self._init_context(configured_modules=['module1', 'module2'], mod1_inherit='CleepRpcWrapper', mod1_exception=True)

        self.i._load_modules()
        logging.debug('Modules: %s' % self.i.modules)

        self.i._rpc_wrapper('a_route', {})
        # can't perform some check call was a success. We add info log message on stdout
        # but in this test case, exception mustn't fail rpc_wrapper call
        
    def test_get_drivers(self):
        self._init_context()

        self.i.get_drivers()
        self.drivers.get_all_drivers.assert_called_with()


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python*/*","*test_*.py" --concurrency=thread test_inventory.py; coverage report -i -m
    unittest.main()

