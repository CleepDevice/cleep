#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests', ''))
from core import RaspIot, RaspIotRpcWrapper, RaspIotModule, RaspIotResources, RaspIotRenderer
from raspiot.libs.tests.lib import TestLib
from raspiot.exception import InvalidParameter, MissingParameter
from raspiot.libs.drivers.driver import Driver
from raspiot.libs.internals.rendererprofile import RendererProfile
import unittest
import logging
from unittest.mock import Mock, MagicMock, patch
import time
import io
import copy

class DummyRaspiot(RaspIot):
    CONFIG_DIR = ''
    MODULE_VERSION = '6.6.6'

    def __init__(self, bootstrap, debug_enabled=False, sentry_dsn=None, default_config=None, with_config=True):
        if sentry_dsn:
            setattr(self, 'MODULE_SENTRY_DSN', sentry_dsn)
        if default_config:
            setattr(self, 'DEFAULT_CONFIG', default_config)
        if with_config:
            setattr(self, 'MODULE_CONFIG_FILE', 'test.conf')
        RaspIot.__init__(self, bootstrap, debug_enabled)

        self.stop_called = False
        self.event_received_called = False

    def _stop(self):
        self.stop_called = True

    def event_received(self, event):
        self.event_received_called = True

    def my_command(self, param):
        pass

class DummyDriver(Driver):
    def __init__(self, fs, dtype, dname):
        Driver.__init__(self, fs, dtype, dname)

class RaspIotTests(unittest.TestCase):

    DEFAULT_CONFIG = {
        'key': 'value1',
        'list': ['list1', 'list2'],
        'bool': True,
        'number': 123456,
        'dict': {
            'dict1': 'value1',
        },
    }

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.config_file = None
        self.r = None

    def tearDown(self):
        if self.r:
            self.r.stop()
        if self.config_file and os.path.exists(self.config_file):
            os.remove(self.config_file)

    def _init_context(self, with_sentry=False, default_config=None, current_config=None, with_config=True, read_json_side_effect=None, write_json_side_effect=None):
        self.crash_report = Mock()
        self.crash_report.is_enabled.return_value = False
        self.crash_report.get_infos.return_value = {
            'libsversion': {},
            'product': 'DummyCleep',
            'productversion': '0.0.0'
        }

        self.cleep_filesystem = Mock()
        if current_config is not None:
            self.config_file = os.path.abspath('test.conf')
            with io.open(self.config_file, 'w') as fd:
                fd.write(u'%s' % current_config)
            self.cleep_filesystem.read_json.return_value = copy.deepcopy(current_config)
        if read_json_side_effect:
            self.cleep_filesystem.read_json.side_effect = read_json_side_effect
        if write_json_side_effect:
            self.cleep_filesystem.write_json.side_effect = write_json_side_effect

        self.events_broker = Mock()
        self.drivers = Mock()

        self.bootstrap = {
            'message_bus': MagicMock(),
            'join_event': Mock(),
            'drivers': self.drivers,
            'cleep_filesystem': self.cleep_filesystem,
            'execution_step': Mock(),
            'events_broker': self.events_broker,
            'crash_report': self.crash_report,
            'test_mode': False,
        }
        sentry_dsn = 'https://8ba3f328a88a44b09zf18a02xf412612@sentry.io/1356005' if with_sentry else None

        self.r = DummyRaspiot(
            self.bootstrap,
            debug_enabled=False,
            sentry_dsn=sentry_dsn,
            default_config=copy.deepcopy(default_config),
            with_config=with_config
        )

    def test_debug_enabled(self):
        try:
            self._init_context()
            r = DummyRaspiot(self.bootstrap, debug_enabled=True)
            self.assertEqual(r.logger.getEffectiveLevel(), logging.DEBUG)

            self.assertTrue(r.is_debug_enabled())

        finally:
            # restore original log level
            r.logger.setLevel(logging.FATAL)

    def test_set_debug(self):
        self._init_context()
        r = DummyRaspiot(self.bootstrap, debug_enabled=False)

        self.assertFalse(r.is_debug_enabled())
        
        r.set_debug(True)
        self.assertTrue(r.is_debug_enabled())
        r.set_debug(False)
        self.assertFalse(r.is_debug_enabled())

    def test_module_without_config(self):
        self._init_context(with_config=False)

        config = self.r._get_config()
        logging.debug('Config: %s' % config)

        self.assertIsNotNone(config)
        self.assertEqual(config, {})

    def test_config_without_file(self):
        self._init_context(default_config=self.DEFAULT_CONFIG)

        config = self.r._get_config()
        logging.debug('Config: %s' % config)

        self.assertIsNotNone(config)
        self.assertEqual(config, self.DEFAULT_CONFIG)

    def test_config_with_empty_file(self):
        self._init_context(default_config=self.DEFAULT_CONFIG, current_config={})

        config = self.r._get_config()
        logging.debug('Config: %s' % config)

        self.assertIsNotNone(config)
        self.assertEqual(config, self.DEFAULT_CONFIG)

    def test_config_with_invalid_file(self):
        self._init_context(default_config=self.DEFAULT_CONFIG, current_config='hello world')

        config = self.r._get_config()
        logging.debug('Config: %s' % config)

        self.assertIsNotNone(config)
        self.assertEqual(config, self.DEFAULT_CONFIG)

    def test_config_exception(self):
        self._init_context(default_config=self.DEFAULT_CONFIG, current_config={}, read_json_side_effect=Exception('Test exception'))

        config = self.r._get_config()
        logging.debug('Config: %s' % config)

        self.assertIsNotNone(config)
        self.assertEqual(config, self.DEFAULT_CONFIG)

    def test_update_config(self):
        self._init_context(default_config=self.DEFAULT_CONFIG, current_config={})

        self.assertTrue(self.r._update_config({
            'newfield': 'newvalue',
            'newvalue': 666,
        }))

        config = self.r._get_config()
        logging.debug('Config: %s' % config)

        self.assertIsNotNone(config)
        self.assertTrue('newfield' in config)
        self.assertEqual(config['newfield'], 'newvalue')
        self.assertTrue('newvalue' in config)
        self.assertEqual(config['newvalue'], 666)

    def test_update_config_invalid_params(self):
        self._init_context(default_config=self.DEFAULT_CONFIG, current_config={})

        with self.assertRaises(InvalidParameter) as cm:
            self.assertTrue(self.r._update_config(666))
        self.assertEqual(cm.exception.message, 'Parameter "config" must be a dict')

    def test_update_config_rollback(self):
        self._init_context(default_config=self.DEFAULT_CONFIG, current_config=self.DEFAULT_CONFIG, write_json_side_effect=Exception('Test exception'))

        self.assertFalse(self.r._update_config({
            'newfield': 'newvalue',
            'newvalue': 666,
        }))

        config = self.r._get_config()
        logging.debug('Config: %s' % config)

        self.assertEqual(config, self.DEFAULT_CONFIG)

    def test_update_config_without_config_file(self):
        self._init_context(with_config=False)

        with self.assertRaises(Exception) as cm:
            self.r._update_config({
                'newfield': 'newvalue',
                'newvalue': 666,
            })
        self.assertEqual(cm.exception.message, 'Module DummyRaspiot has no configuration file configured')

    def test_get_config_field(self):
        self._init_context(default_config=self.DEFAULT_CONFIG, current_config=self.DEFAULT_CONFIG)

        self.assertEqual(self.r._get_config_field('key'), self.DEFAULT_CONFIG['key'])
        self.assertEqual(self.r._get_config_field('list'), self.DEFAULT_CONFIG['list'])

    def test_get_config_field_invalid_field(self):
        self._init_context(default_config=self.DEFAULT_CONFIG, current_config=self.DEFAULT_CONFIG)

        with self.assertRaises(Exception) as cm:
            self.r._get_config_field('dummy')
        self.assertEqual(cm.exception.message, 'Unknown config field "dummy"')

    def test_has_config_field(self):
        self._init_context(default_config=self.DEFAULT_CONFIG, current_config=self.DEFAULT_CONFIG)

        self.assertTrue(self.r._has_config_field('key'))
        self.assertTrue(self.r._has_config_field('list'))
        self.assertFalse(self.r._has_config_field('dummy'))

    def test_set_config_field(self):
        self._init_context(default_config=self.DEFAULT_CONFIG, current_config=self.DEFAULT_CONFIG)

        self.assertTrue(self.r._set_config_field('key', 'hello world'))

        config = self.r._get_config()
        logging.debug('Config: %s' % config)
        self.assertEqual(config['key'], 'hello world')

    def test_set_config_field_invalid_field(self):
        self._init_context(default_config=self.DEFAULT_CONFIG, current_config=self.DEFAULT_CONFIG)

        with self.assertRaises(InvalidParameter) as cm:
            self.r._set_config_field('dummy', 'hello world')
        self.assertEqual(cm.exception.message, 'Parameter "dummy" doesn\'t exist in config')

    def test_sentry_with_dsn(self):
        self._init_context(with_sentry=True)

        self.assertIsNotNone(self.r.crash_report)
        infos = self.r.crash_report.get_infos()
        logging.debug('Infos: %s' % infos)
        cr_infos = self.crash_report.get_infos()
        self.assertEqual(infos['product'], cr_infos['product'])
        self.assertEqual(infos['productversion'], cr_infos['productversion'])
        self.assertTrue(self.r.__class__.__name__.lower() in infos['libsversion'])
        self.assertEqual(infos['libsversion'][self.r.__class__.__name__.lower()], '6.6.6')

    def test_sentry_without_dsn(self):
        self._init_context()

        self.assertIsNotNone(self.r.crash_report)
        infos = self.r.crash_report.get_infos()
        logging.debug('Infos: %s' % infos)
        self.assertEqual(infos['product'], 'CleepDevice')
        self.assertEqual(infos['productversion'], '0.0.0')

    @patch('core.CORE_MODULES', ['dummyraspiot'])
    def test_sentry_core_module(self):
        self._init_context()

        self.assertIsNotNone(self.r.crash_report)
        infos = self.r.crash_report.get_infos()
        logging.debug('Infos: %s' % infos)
        cr_infos = self.crash_report.get_infos()
        self.assertEqual(infos['product'], cr_infos['product'])
        self.assertEqual(infos['productversion'], cr_infos['productversion'])
        self.crash_report.add_module_version.assert_called_once_with('DummyRaspiot', '6.6.6')

    def test_register_driver(self):
        self._init_context()
        d = DummyDriver(self.cleep_filesystem, Driver.DRIVER_AUDIO, 'dummydriver')

        self.r._register_driver(d)

        self.drivers.register.assert_called_once_with(d)

    def test_register_driver_invalid_parameters(self):
        self._init_context()

        with self.assertRaises(InvalidParameter) as cm:
            self.r._register_driver(Mock())
        self.assertEqual(cm.exception.message, 'Driver must be instance of base Driver class')

    def test_get_drivers(self):
        self._init_context()

        self.r._get_drivers(Driver.DRIVER_AUDIO)

        self.drivers.get_drivers.assert_called_once_with(Driver.DRIVER_AUDIO)

    def test_get_unique_id(self):
        self._init_context()

        uid = self.r._get_unique_id()
        logging.debug('Id: %s' % uid)

        self.assertEqual(len(uid.split('-')), 5)

    def test_get_module_config(self):
        self._init_context(default_config=self.DEFAULT_CONFIG, current_config=self.DEFAULT_CONFIG)

        config = self.r.get_module_config()
        logging.debug('Config: %s' % config)
        self.assertEqual(config, self.DEFAULT_CONFIG)

    def test_get_module_name(self):
        self._init_context()

        self.assertEqual(self.r._get_module_name(), 'dummyraspiot')

    def test_get_event(self):
        self._init_context()

        self.r._get_event('dummyevent')

        self.events_broker.get_event_instance.assert_called_once_with('dummyevent')

    def test_get_module_commands(self):
        self._init_context()

        commands = self.r.get_module_commands()
        logging.debug('Commands: %s' % commands)

        self.assertEqual(len(commands), 1)
        self.assertTrue('my_command' in commands)

    @patch('core.RaspIot.send_command')
    def test_is_module_loaded_return_true(self, send_command_mock):
        self._init_context()

        send_command_mock.return_value = {
            'error': False,
            'data': True,
            'message': ''
        }

        self.assertEqual(self.r.is_module_loaded('otherdummy'), True)

    @patch('core.RaspIot.send_command')
    def test_is_module_loaded_return_false(self, send_command_mock):
        self._init_context()

        send_command_mock.return_value = {
            'error': True,
            'data': True,
            'message': ''
        }

        self.assertEqual(self.r.is_module_loaded('otherdummy'), False)

    @patch('core.CORE_MODULES', ['dummyraspiot'])
    @patch('core.RaspIot.send_command')
    def test_is_module_loaded_exception(self, send_command_mock):
        self._init_context()

        send_command_mock.side_effect = Exception('Test exception')

        self.assertEqual(self.r.is_module_loaded('otherdummy'), False)
        self.assertTrue(self.crash_report.report_exception.called)

    def test_start_stop(self):
        self._init_context()
        
        self.r.start()
        time.sleep(1.0)
        self.r.stop()

        self.assertTrue(self.r.stop_called)

    def test_event_received(self):
        self._init_context()

        self.r._event_received({'device_id': None, 'event': 'event.test.dummy', 'params':{}})
        self.assertTrue(self.r.event_received_called)





class DummyRaspiotModule(RaspIotModule):
    CONFIG_DIR = ''
    MODULE_VERSION = '6.6.6'

    def __init__(self, bootstrap, debug_enabled=False, sentry_dsn=None, default_config=None, with_config=True):
        if sentry_dsn:
            setattr(self, 'MODULE_SENTRY_DSN', sentry_dsn)
        if default_config:
            setattr(self, 'DEFAULT_CONFIG', default_config)
        if with_config:
            setattr(self, 'MODULE_CONFIG_FILE', 'test.conf')
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        self.stop_called = False
        self.event_received_called = False

    def _stop(self):
        self.stop_called = True

    def event_received(self, event):
        self.event_received_called = True

    def my_command(self, param):
        pass

class RaspIotModuleTests(unittest.TestCase):

    DEFAULT_CONFIG = {
        'key': 'value1',
        'list': ['list1', 'list2'],
        'bool': True,
        'number': 123456,
        'dict': {
            'dict1': 'value1',
        },
    }

    DEVICE1 = {
        'lastupdate': int(time.time()),
        'name': 'dummydevice1',
        'value': 123456,
        'boolean': True,
        'common': 'common'
    }
    DEVICE2 = {
        'name': 'dummydevice2',
        'lastvalue': 'hello world',
        'common': 'common'
    }

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.config_file = None
        self.r = None

    def tearDown(self):
        if self.r:
            self.r.stop()
        if self.config_file and os.path.exists(self.config_file):
            os.remove(self.config_file)

    def _init_context(self, with_sentry=False, default_config=None, current_config=None, with_config=True, read_json_side_effect=None, write_json_side_effect=None, with_delete_event=True):
        self.crash_report = Mock()
        self.crash_report.is_enabled.return_value = False
        self.crash_report.get_infos.return_value = {
            'libsversion': {},
            'product': 'DummyCleep',
            'productversion': '0.0.0'
        }

        self.cleep_filesystem = Mock()
        if current_config is not None:
            self.config_file = os.path.abspath('test.conf')
            with io.open(self.config_file, 'w') as fd:
                fd.write(u'%s' % current_config)
            self.cleep_filesystem.read_json.return_value = copy.deepcopy(current_config)
        if read_json_side_effect:
            self.cleep_filesystem.read_json.side_effect = read_json_side_effect
        if write_json_side_effect:
            self.cleep_filesystem.write_json.side_effect = write_json_side_effect

        self.events_broker = Mock()
        self.delete_event = Mock()
        if with_delete_event:
            self.events_broker.get_event_instance.return_value = self.delete_event
        else:
            self.events_broker.get_event_instance.side_effect = Exception('Test exception')

        self.drivers = Mock()

        self.bootstrap = {
            'message_bus': MagicMock(),
            'join_event': Mock(),
            'drivers': self.drivers,
            'cleep_filesystem': self.cleep_filesystem,
            'execution_step': Mock(),
            'events_broker': self.events_broker,
            'crash_report': self.crash_report,
            'test_mode': False,
        }
        sentry_dsn = 'https://8ba3f328a88a44b09zf18a02xf412612@sentry.io/1356005' if with_sentry else None

        self.r = DummyRaspiotModule(
            self.bootstrap,
            debug_enabled=False,
            sentry_dsn=sentry_dsn,
            default_config=copy.deepcopy(default_config),
            with_config=with_config
        )

    def test_devices_section_exists(self):
        self._init_context()

        config = self.r._get_config()
        logging.debug('Config: %s' % config)

        self.assertTrue('devices' in config)

    def test_get_device(self):
        self._init_context()

        device1 = self.r._add_device(copy.deepcopy(self.DEVICE1))
        
        found = self.r._get_device(device1['uuid'])
        self.assertEqual(found, device1)

        self.assertIsNone(self.r._get_device('786d1b69-a603-4eb8-9178-fed2a195a1ed'))

    def test_get_devices(self):
        self._init_context()

        device1 = self.r._add_device(copy.deepcopy(self.DEVICE1))
        device2 = self.r._add_device(copy.deepcopy(self.DEVICE2))

        devices = self.r._get_devices()
        logging.debug('Devices: %s' % devices)
        uuids = devices.keys()
        self.assertEqual(len(devices), 2)
        self.assertTrue(device1['uuid'] in uuids)
        self.assertTrue(device2['uuid'] in uuids)

    def test_get_device_count(self):
        self._init_context()

        device1 = self.r._add_device(copy.deepcopy(self.DEVICE1))
        device2 = self.r._add_device(copy.deepcopy(self.DEVICE2))

        self.assertEqual(self.r._get_device_count(), 2)

        self.r._delete_device(device1['uuid'])
        self.assertEqual(self.r._get_device_count(), 1)

    def test_add_device(self):
        self._init_context()

        device1 = self.r._add_device(copy.deepcopy(self.DEVICE1))
        device2 = self.r._add_device(copy.deepcopy(self.DEVICE2))
        logging.debug('Device1: %s' % device1)
        logging.debug('Device2: %s' % device2)
        
        self.assertTrue('uuid' in device1)
        self.assertTrue(all(key in device1.keys() for key in self.DEVICE1.keys()))
        self.assertTrue('uuid' in device2)
        self.assertTrue(all(key in device2.keys() for key in self.DEVICE2.keys()))

        config = self.r._get_config()
        logging.debug('Config: %s' % config)

        self.assertEqual(config['devices'][device1['uuid']], device1)
        self.assertEqual(config['devices'][device2['uuid']], device2)

    def test_add_device_should_add_name_field(self):
        self._init_context()

        device3 = copy.deepcopy(self.DEVICE1)
        del device3['name']
        device = self.r._add_device(device3)
        logging.debug('Device: %s' % device)

        self.assertTrue('name' in device)
        self.assertEqual(device['name'], 'noname')

    def test_add_device_invalid_parameters(self):
        self._init_context()

        with self.assertRaises(InvalidParameter) as cm:
            self.r._add_device('hello')
        self.assertEqual(cm.exception.message, 'Parameter "data" must be a dict')

    def test_add_device_save_config_failed(self):
        self._init_context(write_json_side_effect=[True, True, Exception('Test exception')])

        self.assertIsNone(self.r._add_device(copy.deepcopy(self.DEVICE1)))

    def test_delete_device(self):
        self._init_context()

        device1 = self.r._add_device(copy.deepcopy(self.DEVICE1))
        uuid = device1['uuid']
        self.assertTrue(self.r._delete_device(device1['uuid']))

        self.delete_event.send.assert_called_with(device_id=uuid)

    def test_delete_device_without_event(self):
        self._init_context(with_delete_event=False)

        device1 = self.r._add_device(copy.deepcopy(self.DEVICE1))
        uuid = device1['uuid']
        self.assertTrue(self.r._delete_device(device1['uuid']))

        self.delete_event.send.assert_not_called()

    def test_delete_device_unknown_device(self):
        self._init_context()

        self.assertFalse(self.r._delete_device('786d1b69-a603-4eb8-9178-fed2a195a1ed'))
        self.delete_event.send.assert_not_called()

    def test_update_device(self):
        self._init_context()

        device1 = self.r._add_device(copy.deepcopy(self.DEVICE1))
        device1['value'] = 654321
        uuid = device1['uuid']
        self.assertTrue(self.r._update_device(uuid, device1))

        device1 = self.r._get_device(uuid)
        logging.debug('Device1: %s' % device1)

        self.assertEqual(device1['value'], 654321)

    def test_update_device_unknown_device(self):
        self._init_context()

        device1 = self.r._add_device(copy.deepcopy(self.DEVICE1))
        self.assertFalse(self.r._update_device('786d1b69-a603-4eb8-9178-fed2a195a1ed', device1))

    def test_update_device_with_new_field(self):
        self._init_context()

        device1 = self.r._add_device(copy.deepcopy(self.DEVICE1))
        uuid = device1['uuid']
        
        new_data = copy.deepcopy(device1)
        new_data['newfield'] = 'duckduck'
        new_data['name'] = 'newname'
        self.assertTrue(self.r._update_device(uuid, new_data))
        
        updated_device1 = self.r._get_device(uuid)
        logging.debug('Updated device1: %s' % updated_device1)
        self.assertFalse('newfield' in updated_device1)
        self.assertTrue('value' in updated_device1)
        self.assertTrue('lastupdate' in updated_device1)
        self.assertTrue('name' in updated_device1)
        self.assertEqual(updated_device1['name'], 'newname')

    def test_update_device_do_not_alter_other_device(self):
        self._init_context()

        device1 = self.r._add_device(copy.deepcopy(self.DEVICE1))
        device2 = self.r._add_device(copy.deepcopy(self.DEVICE2))
        
        devices_before = self.r.get_module_devices()
        new_data = copy.deepcopy(device1)
        self.r._update_device(device1['uuid'], new_data)

        devices_after = self.r.get_module_devices()
        self.assertEqual(devices_before, devices_after)

    def test_update_device_invalid_parameters(self):
        self._init_context()

        with self.assertRaises(InvalidParameter) as cm:
            self.r._update_device('786d1b69-a603-4eb8-9178-fed2a195a1ed', 'string')
        self.assertEqual(cm.exception.message, 'Parameter "data" must be a dict')

        with self.assertRaises(InvalidParameter) as cm:
            self.r._update_device('786d1b69-a603-4eb8-9178-fed2a195a1ed', True)

    def test_search_device(self):
        self._init_context()

        device1 = self.r._add_device(copy.deepcopy(self.DEVICE1))
        device2 = self.r._add_device(copy.deepcopy(self.DEVICE2))

        search = self.r._search_device('name', 'dummydevice1')
        self.assertEqual(search, device1)

        search = self.r._search_device('value', 123456)
        self.assertEqual(search, device1)

        search = self.r._search_device('boolean', True)
        self.assertEqual(search, device1)

        search = self.r._search_device('lastvalue', 'hello world')
        self.assertEqual(search, device2)

        self.assertIsNone(self.r._search_device('name', 'a name'))

    def test_search_device_while_no_device(self):
        self._init_context()

        self.assertIsNone(self.r._search_device('name', 'dummydevice1'))

    def test_search_devices(self):
        self._init_context()

        device1 = self.r._add_device(copy.deepcopy(self.DEVICE1))
        device2 = self.r._add_device(copy.deepcopy(self.DEVICE2))

        searches = self.r._search_devices('common', 'common')
        logging.debug('Searches: %s' % searches)
        uuids = [d['uuid'] for d in searches]
        self.assertEqual(len(searches), 2)
        self.assertTrue(device1['uuid'] in uuids)
        self.assertTrue(device2['uuid'] in uuids)

    def test_search_devices_while_no_device(self):
        self._init_context()

        self.assertEqual(self.r._search_devices('common', 'common'), [])

    def test_get_module_config(self):
        self._init_context(default_config=self.DEFAULT_CONFIG, current_config=self.DEFAULT_CONFIG)

        config = self.r.get_module_config()
        logging.debug('Config: %s' % config)
        self.assertEqual(config, self.DEFAULT_CONFIG)

    def test_get_module_commands(self):
        self._init_context()

        commands = self.r.get_module_commands()
        logging.debug('Commands: %s' % commands)

        self.assertEqual(len(commands), 1)
        self.assertTrue('my_command' in commands)





class DummyRaspiotRpcWrapper(RaspIotRpcWrapper):
    CONFIG_DIR = ''
    MODULE_VERSION = '6.6.6'

    def __init__(self, bootstrap, debug_enabled=False, sentry_dsn=None):
        if sentry_dsn:
            setattr(self, 'MODULE_SENTRY_DSN', sentry_dsn)
        RaspIotRpcWrapper.__init__(self, bootstrap, debug_enabled)

    def my_command(self):
        pass

class RaspIotRpcWrapperTests(unittest.TestCase):

    DEFAULT_CONFIG = {
        'key': 'value1',
        'list': ['list1', 'list2'],
        'bool': True,
        'number': 123456,
        'dict': {
            'dict1': 'value1',
        },
    }

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.r = None

    def tearDown(self):
        if self.r:
            self.r.stop()

    def _init_context(self):
        self.crash_report = Mock()
        self.crash_report.is_enabled.return_value = False
        self.crash_report.get_infos.return_value = {
            'libsversion': {},
            'product': 'DummyCleep',
            'productversion': '0.0.0'
        }

        self.cleep_filesystem = Mock()
        self.events_broker = Mock()
        self.drivers = Mock()

        self.bootstrap = {
            'message_bus': MagicMock(),
            'join_event': Mock(),
            'drivers': self.drivers,
            'cleep_filesystem': self.cleep_filesystem,
            'execution_step': Mock(),
            'events_broker': self.events_broker,
            'crash_report': self.crash_report,
            'test_mode': False,
        }
        sentry_dsn = 'https://8ba3f328a88a44b09zf18a02xf412612@sentry.io/1356005'

        self.r = DummyRaspiotRpcWrapper(
            self.bootstrap,
            debug_enabled=False,
            sentry_dsn=sentry_dsn,
        )

    def test_rpcwrapper(self):
        try:
            self._init_context()
        except:
            logging.exception('Exception occured')
            self.fail('Should create RaspIotRpcWrapper without exception')

    def test_get_module_commands(self):
        self._init_context()

        commands = self.r.get_module_commands()
        logging.debug('Commands: %s' % commands)

        self.assertEqual(len(commands), 1)
        self.assertTrue('my_command' in commands)





class DummyRaspiotResources(RaspIotResources):
    CONFIG_DIR = ''
    MODULE_VERSION = '6.6.6'

    MODULE_RESOURCES = {
        'audio.playback': {
            'permanent': False
        },
        'audio.capture': {
            'permanent': False
        },
    }

    def __init__(self, bootstrap, debug_enabled=False, sentry_dsn=None):
        if sentry_dsn:
            setattr(self, 'MODULE_SENTRY_DSN', sentry_dsn)
        RaspIotResources.__init__(self, bootstrap, debug_enabled)

    def my_command(self):
        pass

class RaspIotResourcesTests(unittest.TestCase):

    DEFAULT_CONFIG = {
        'key': 'value1',
        'list': ['list1', 'list2'],
        'bool': True,
        'number': 123456,
        'dict': {
            'dict1': 'value1',
        },
    }

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.r = None

    def tearDown(self):
        if self.r:
            self.r.stop()

    def _init_context(self):
        self.crash_report = Mock()
        self.crash_report.is_enabled.return_value = False
        self.crash_report.get_infos.return_value = {
            'libsversion': {},
            'product': 'DummyCleep',
            'productversion': '0.0.0'
        }

        self.cleep_filesystem = Mock()
        self.events_broker = Mock()
        self.drivers = Mock()

        self.critical_resources = Mock()

        self.bootstrap = {
            'message_bus': MagicMock(),
            'join_event': Mock(),
            'drivers': self.drivers,
            'cleep_filesystem': self.cleep_filesystem,
            'execution_step': Mock(),
            'events_broker': self.events_broker,
            'crash_report': self.crash_report,
            'test_mode': False,
            'critical_resources': self.critical_resources,
        }
        sentry_dsn = 'https://8ba3f328a88a44b09zf18a02xf412612@sentry.io/1356005'

        self.r = DummyRaspiotResources(
            self.bootstrap,
            debug_enabled=False,
            sentry_dsn=sentry_dsn,
        )

    def test_raspiot_resources(self):
        self._init_context()
        r = RaspIotResources(self.bootstrap, False)

        with self.assertRaises(NotImplementedError) as cm:
            r._resource_acquired('dummy')
        self.assertEqual(cm.exception.message, 'Method "_resource_acquired" must be implemented in "RaspIotResources"')

        with self.assertRaises(NotImplementedError) as cm:
            r._resource_needs_to_be_released('dummy')
        self.assertEqual(cm.exception.message, 'Method "_resource_needs_to_be_released" must be implemented in "RaspIotResources"')

    def test_get_module_commands(self):
        self._init_context()

        commands = self.r.get_module_commands()
        logging.debug('Commands: %s' % commands)

        self.assertEqual(len(commands), 1)
        self.assertTrue('my_command' in commands)

    def test_need_resource(self):
        self._init_context()

        self.r._need_resource('dummy')

        self.critical_resources.acquire_resource.assert_called_with('DummyRaspiotResources', 'dummy')

    def test_release_resource(self):
        self._init_context()

        self.r._release_resource('dummy')

        self.critical_resources.release_resource.assert_called_with('DummyRaspiotResources', 'dummy')

    def test_get_resources(self):
        self._init_context()

        self.r._get_resources()

        self.critical_resources.get_resources.assert_called_with()





class DummyRaspiotRenderer(RaspIotRenderer):
    CONFIG_DIR = ''
    MODULE_VERSION = '6.6.6'
    RENDERER_PROFILES = [RendererProfile]

    def __init__(self, bootstrap, debug_enabled=False, sentry_dsn=None):
        if sentry_dsn:
            setattr(self, 'MODULE_SENTRY_DSN', sentry_dsn)
        RaspIotRenderer.__init__(self, bootstrap, debug_enabled)

    def my_command(self):
        pass

class RaspIotRendererTests(unittest.TestCase):

    DEFAULT_CONFIG = {
        'key': 'value1',
        'list': ['list1', 'list2'],
        'bool': True,
        'number': 123456,
        'dict': {
            'dict1': 'value1',
        },
    }

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.r = None

    def tearDown(self):
        if self.r:
            self.r.stop()

    def _init_context(self):
        self.crash_report = Mock()
        self.crash_report.is_enabled.return_value = False
        self.crash_report.get_infos.return_value = {
            'libsversion': {},
            'product': 'DummyCleep',
            'productversion': '0.0.0'
        }

        self.cleep_filesystem = Mock()
        self.events_broker = Mock()
        self.drivers = Mock()

        self.critical_resources = Mock()

        self.bootstrap = {
            'message_bus': MagicMock(),
            'join_event': Mock(),
            'drivers': self.drivers,
            'cleep_filesystem': self.cleep_filesystem,
            'execution_step': Mock(),
            'events_broker': self.events_broker,
            'crash_report': self.crash_report,
            'test_mode': False,
            'critical_resources': self.critical_resources,
        }
        sentry_dsn = 'https://8ba3f328a88a44b09zf18a02xf412612@sentry.io/1356005'

        self.r = DummyRaspiotRenderer(
            self.bootstrap,
            debug_enabled=False,
            sentry_dsn=sentry_dsn,
        )

    def test_raspiot_renderer(self):
        self._init_context()
        r = RaspIotRenderer(self.bootstrap, False)

        with self.assertRaises(NotImplementedError) as cm:
            r._render('dummy')
        self.assertEqual(cm.exception.message, 'Method "_render" must be implemented in "RaspIotRenderer"')

    def test_get_module_commands(self):
        self._init_context()

        commands = self.r.get_module_commands()
        logging.debug('Commands: %s' % commands)

        self.assertEqual(len(commands), 1)
        self.assertTrue('my_command' in commands)

    def test_get_renderer_config(self):
        self._init_context()

        renderer_config = self.r._get_renderer_config()
        logging.debug('Renderer config: %s' % renderer_config)
        self.assertTrue(isinstance(renderer_config, dict))
        self.assertTrue('profiles' in renderer_config)
        self.assertEqual(len(renderer_config), 1)
        self.assertEqual(len(self.r.profiles_types), 1)
        logging.debug('%s' % self.r.profiles_types)
        self.assertEqual(self.r.profiles_types[0], 'RendererProfile')

    def test_get_renderer_config_no_member_declared(self):
        self._init_context()

        r = RaspIotRenderer(self.bootstrap, False)
        with self.assertRaises(Exception) as cm:
            r._get_renderer_config()
        self.assertEqual(cm.exception.message, 'RENDERER_PROFILES is not defined in "RaspIotRenderer"')

    def test_render(self):
        self._init_context()
        p = RendererProfile()
        class Context():
            called = False
        def custom_render(p):
            Context.called = True
        self.r._render = custom_render
        self.r._get_renderer_config()

        self.assertTrue(self.r.render(p))
        self.assertTrue(Context.called)

    def test_render_invalid_profile(self):
        self._init_context()
        p = RendererProfile()

        with self.assertRaises(InvalidParameter) as cm:
            self.r.render(p)
        self.assertEqual(cm.exception.message, 'Profile "RendererProfile" is not supported in this renderer')

    def test_render_exception(self):
        self._init_context()
        p = RendererProfile()
        def custom_render(p):
            raise Exception('Test exception')
        self.r._render = custom_render
        self.r._get_renderer_config()

        self.assertFalse(self.r.render(p))


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","*test_*.py" --concurrency=thread test_core.py; coverage report -m -i
    unittest.main()


