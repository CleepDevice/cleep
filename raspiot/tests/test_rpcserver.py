#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests', ''))
import rpcserver
from raspiot.libs.tests.lib import TestLib
from raspiot.libs.drivers.driver import Driver
from raspiot.common import MessageRequest
from raspiot.exception import NoMessageAvailable
import unittest
import logging
from boddle import boddle
from bottle import HTTPError, HTTPResponse
from unittest.mock import Mock, patch, mock_open
import json
import time

class DummyDriver(Driver):
    def __init__(self, processing=False, is_installed=False, is_installed_exception=False):
        self.__processing = processing
        self.__is_installed = is_installed
        self.__is_installed_exception = is_installed_exception
    def processing(self):
        return self.__processing
    def is_installed(self):
        if self.__is_installed_exception:
            raise Exception('Test exception')
        return self.__is_installed

class RpcServerTests(unittest.TestCase):

    DRIVERS = {
        'audio': {
            'driver1': DummyDriver(True, False),
            'driver2': DummyDriver(False, True)
        },
        'gpio': {
        }
    }
    RENDERERS = {
        'module1': ['profile1'],
        'module2' : ['profile1', 'profile2']
    }
    EVENTS = {
        'event1': {
            'modules': ['module1', 'module2'],
            'profiles': ['profile1', 'profile2']
        },
        'event2': {
            'modules': [],
            'profiles': ['profile3']
        }
    }
    MODULES = {
        'module1': {
            'name': 'module1',
            'version': '0.0.0'
        },
        'module2': {
            'name': 'module2',
            'version': '0.0.0'
        },
    }
    DEVICES = {
        'module1': {
            '123-456-789': {
                'name': 'device1'
            },
            '987-645-321': {
                'name': 'device2'
            },
        },
        'module2': {
            '456-789-312': {
                'name': 'device3'
            }
        }
    }

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        if rpcserver:
            rpcserver.sessions.clear()
            rpcserver.logger.setLevel(logging.getLogger().getEffectiveLevel())

    def _init_context(self, push_return_value=None, push_side_effect=None, no_bus=False, is_subscribed_return_value=None, is_subscribed_side_effect=None,
            pull_return_value=None, pull_side_effect=None, get_drivers_side_effect=None, get_drivers_gpio_exception=False, debug_enabled=False):
        self.crash_report = Mock()
        self.cleep_filesystem = Mock()
        self.bus = Mock()
        if push_return_value is not None:
            self.bus.push.return_value = push_return_value
        if push_side_effect is not None:
            self.bus.push.side_effect = push_side_effect
        if pull_return_value is not None:
            self.bus.pull.return_value = pull_return_value
        if pull_side_effect is not None:
            self.bus.pull.side_effect = pull_side_effect
        if is_subscribed_return_value is not None:
            self.bus.is_subscribed.return_value = is_subscribed_return_value
        if is_subscribed_side_effect is not None:
            self.bus.is_subscribed.side_effect = is_subscribed_side_effect
        self.bootstrap = {
            'message_bus': None if no_bus else self.bus,
            'cleep_filesystem': self.cleep_filesystem,
            'crash_report': self.crash_report,
        }

        self.inventory = Mock()
        self.inventory.get_renderers.return_value = self.RENDERERS
        if get_drivers_side_effect is None:
            self.inventory.get_drivers.return_value = self.DRIVERS
            if get_drivers_gpio_exception:
                self.inventory.get_drivers.return_value['gpio']['driverfailed'] = DummyDriver(is_installed_exception=True)
        else:
            self.inventory.get_drivers.side_effect = get_drivers_side_effect
        self.inventory.get_used_events.return_value = self.EVENTS
        self.inventory.get_modules.return_value = self.MODULES
        self.inventory.get_installable_modules.return_value = self.MODULES
        self.inventory.get_devices.return_value = self.DEVICES

        rpcserver.configure(self.bootstrap, self.inventory, debug_enabled)

    @patch('json.load')
    def test_load_auth_with_no_accounts_and_enabled(self, json_load_mock):
        json_load_mock.return_value = {
            'accounts': {
            },
            'enabled': True,
        }
        self._init_context()

        with boddle():
            self.assertFalse(rpcserver.auth_enabled)

    @patch('json.load')
    def test_load_auth_with_accounts_and_disabled(self, json_load_mock):
        json_load_mock.return_value = {
            'accounts': {
                'test': '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'
            },
            'enabled': False,
        }
        self._init_context()

        with boddle():
            self.assertFalse(rpcserver.auth_enabled)

    @patch('json.load')
    def test_load_auth_with_accounts_and_enabled(self, json_load_mock):
        json_load_mock.return_value = {
            'accounts': {
                'test': '$5$rounds=535000$VeU5e79jNXnS3b4z$atnocFYx/vEmrv2KAiFvofeHLPu3ztVF0uI5SLUMuo2'
            },
            'enabled': True,
        }
        self._init_context()

        with boddle():
            self.assertTrue(rpcserver.auth_enabled)
            self.assertEqual(len(rpcserver.auth_config['accounts']), 1)
            self.assertTrue('test' in rpcserver.auth_config['accounts'])

    @patch('json.load')
    def test_load_auth_failed(self, json_load_mock):
        json_load_mock.side_effect = Exception('Test exception')
        self._init_context()
        
        with boddle():
            self.assertTrue(self.crash_report.report_exception.called)

    @patch('json.load')
    def test_check_auth(self, json_load_mock):
        json_load_mock.return_value = {
            'accounts': {
                'test': '$5$rounds=535000$VeU5e79jNXnS3b4z$atnocFYx/vEmrv2KAiFvofeHLPu3ztVF0uI5SLUMuo2'
            },
            'enabled': True,
        }
        self._init_context()

        with boddle():
            self.assertEqual(len(rpcserver.sessions.keys()), 0)
            self.assertTrue(rpcserver.check_auth('test', 'test'))
            self.assertEqual(len(rpcserver.sessions.keys()), 1)
            session_key = rpcserver.sessions.keys()[0]
            old_time = rpcserver.sessions[session_key]

            # check it uses sessions
            time.sleep(1.0)
            self.assertTrue(rpcserver.check_auth('test', 'test'))
            new_time = rpcserver.sessions[session_key]
            self.assertNotEqual(new_time, old_time)

    @patch('json.load')
    def test_check_auth_bad_password(self, json_load_mock):
        json_load_mock.return_value = {
            'accounts': {
                'test': '$5$rounds=535000$tLWAIhyEYBj9JX8D$QqkTEqm9dpfz2.Fnu.C1QryHkav6lYu56/PbTb7sD3/'
            },
            'enabled': True,
        }
        self._init_context()

        with boddle():
            self.assertFalse(rpcserver.check_auth('test', 'test'))

    @patch('json.load')
    def test_check_auth_invalid_password(self, json_load_mock):
        json_load_mock.return_value = {
            'accounts': {
                'test': 'Hkav6lYu56/PbTb7sD3/'
            },
            'enabled': True,
        }
        self._init_context()

        with boddle():
            self.assertFalse(rpcserver.check_auth('test', 'test'))

    @patch('json.load')
    def test_check_auth_invalid_user(self, json_load_mock):
        json_load_mock.return_value = {
            'accounts': {
                'test': '$5$rounds=535000$tLWAIhyEYBj9JX8D$QqkTEqm9dpfz2.Fnu.C1QryHkav6lYu56/PbTb7sD3/'
            },
            'enabled': True,
        }
        self._init_context()

        with boddle():
            self.assertFalse(rpcserver.check_auth('dummy', 'test'))

    def test_set_cache_control(self):
        self._init_context()

        with boddle():
            rpcserver.set_cache_control(True)
            self.assertTrue(rpcserver.cache_enabled)

            rpcserver.set_cache_control(False)
            self.assertFalse(rpcserver.cache_enabled)

    def test_set_debug(self):
        self._init_context()

        with boddle():
            rpcserver.set_debug(True)
            self.assertEqual(rpcserver.debug_enabled, True)
            self.assertEqual(rpcserver.logger.getEffectiveLevel(), logging.DEBUG)
            self.assertTrue(rpcserver.is_debug_enabled())

            rpcserver.set_debug(False)
            self.assertEqual(rpcserver.debug_enabled, False)
            self.assertEqual(rpcserver.logger.getEffectiveLevel(), logging.getLogger().getEffectiveLevel())
            self.assertFalse(rpcserver.is_debug_enabled())

    def test_debug_enabled_with_configure(self):
        self._init_context(debug_enabled=True)

        with boddle():
            self.assertEqual(rpcserver.debug_enabled, True)
            self.assertEqual(rpcserver.logger.getEffectiveLevel(), logging.DEBUG)
            self.assertTrue(rpcserver.is_debug_enabled())

    def test_debug_disabled_with_configure(self):
        self._init_context(debug_enabled=False)

        with boddle():
            self.assertEqual(rpcserver.debug_enabled, False)
            self.assertEqual(rpcserver.logger.getEffectiveLevel(), logging.getLogger().getEffectiveLevel())
            self.assertFalse(rpcserver.is_debug_enabled())

    def test_send_command(self):
        self._init_context()

        with boddle():
            # with timeout
            r = rpcserver.send_command(command='cmd', to='module', params={}, timeout=3.0)
            self.assertTrue(self.bus.push.called_once)
            args = self.bus.push.call_args
            self.assertTrue(isinstance(args[0][0], MessageRequest))
            self.assertEqual(args[0][1], 3.0)

            # without timeout
            r = rpcserver.send_command(command='cmd', to='module', params={})
            self.assertTrue(self.bus.push.called_once)
            args = self.bus.push.call_args
            self.assertTrue(isinstance(args[0][0], MessageRequest))
            self.assertEqual(len(args[0]), 1)


    def test_events(self):
        self._init_context()

        with boddle():
            e = rpcserver.events()
            logging.debug('Events: %s' % e)
            self.assertEqual(e, json.dumps(self.EVENTS))

    def test_modules(self):
        self._init_context()

        with boddle():
            m = rpcserver.modules()
            logging.debug('Modules: %s' % m)
            self.assertEqual(m, json.dumps(self.MODULES))
            self.assertFalse(self.inventory.get_installable_modules.called)
            self.assertTrue(self.inventory.get_modules.called)

    def test_modules_with_installable_true(self):
        self._init_context()

        with boddle(json={'installable': True}):
            m = rpcserver.modules()
            logging.debug('Modules: %s' % m)
            self.assertEqual(m, json.dumps(self.MODULES))
            self.assertTrue(self.inventory.get_installable_modules.called)
            self.assertFalse(self.inventory.get_modules.called)

    def test_modules_with_installable_false(self):
        self._init_context()

        with boddle(json={'installable': False}):
            m = rpcserver.modules()
            logging.debug('Modules: %s' % m)
            self.assertEqual(m, json.dumps(self.MODULES))
            self.assertFalse(self.inventory.get_installable_modules.called)
            self.assertTrue(self.inventory.get_modules.called)

    def test_devices(self):
        self._init_context()

        with boddle(method='POST'):
            d = rpcserver.devices()
            self.assertEqual(d, json.dumps(self.DEVICES))

    def test_renderers(self):
        self._init_context()

        with boddle(method='POST'):
            r = rpcserver.renderers()
            self.assertEqual(r, json.dumps(self.RENDERERS))

    def test_drivers(self):
        self._init_context()

        with boddle(method='POST'):
            d = json.loads(rpcserver.drivers())
            logging.debug('Drivers: %s' % d)
            self.assertEqual(d, [{"drivertype": "audio", "processing": True, "drivername": "driver1", "installed": False}, {"drivertype": "audio", "processing": False, "drivername": "driver2", "installed": True}])

    def test_drivers_one_driver_exception(self):
        self._init_context(get_drivers_gpio_exception=True)

        with boddle(method='POST'):
            d = json.loads(rpcserver.drivers())
            logging.debug('Drivers: %s' % d)
            self.assertEqual(len(d), 2)

    def test_upload_missing_params(self):
        self._init_context()

        with boddle():
            r = rpcserver.upload()
            logging.debug('Response: %s' % r)
            self.assertEqual(r, {u'message': u'Missing parameters', u'data': None, u'error': True})

    def test_download_wo_params(self):
        self._init_context(push_return_value={'error': False, 'data': {'filepath':'/tmp/123456789', 'filename':'dummy.test'}, 'message': None})

        with boddle(query={'command':'cmd', 'to':'dummy'}):
            resp = rpcserver.download()
            logging.debug('Response: %s' % resp)
            args = self.bus.push.call_args
            self.assertTrue(isinstance(args[0][0], MessageRequest))
            logging.debug('MessageRequest: %s' % args[0][0].to_dict())
            self.assertEqual(args[0][0].to_dict(), {u'broadcast': False, u'params': {}, u'command': u'cmd', u'sender': u'rpcserver', u'to': u'dummy'})

    def test_download_w_params(self):
        self._init_context(push_return_value={'error': False, 'data': {'filepath':'/tmp/123456789', 'filename':'dummy.test'}, 'message': None})

        with boddle(query={'command':'cmd', 'to':'dummy', 'params': {'dummy': 'value'}}):
            resp = rpcserver.download()
            logging.debug('Response: %s' % resp)
            args = self.bus.push.call_args
            self.assertTrue(isinstance(args[0][0], MessageRequest))
            logging.debug('MessageRequest: %s' % args[0][0].to_dict())
            self.assertEqual(args[0][0].to_dict(), {u'broadcast': False, u'params': {'params': "{'dummy': 'value'}"}, u'command': u'cmd', u'sender': u'rpcserver', u'to': u'dummy'})

    def test_download_failed(self):
        self._init_context(push_return_value={'error': True, 'data': None, 'message': 'Command failed'})

        with boddle(query={'command':'cmd', 'to':'dummy', 'params': {'dummy': 'value'}}):
            resp = rpcserver.download()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {u'message': u'Command failed', u'data': None, u'error': True})

    def test_download_exception(self):
        self._init_context(push_side_effect=Exception('Test exception'))

        with boddle(query={'command':'cmd', 'to':'dummy'}):
            resp = rpcserver.download()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {u'message': u'Test exception', u'data': None, u'error': True})

    def test_command_get(self):
        return_value = {'error':False, 'data':{'key':'value'}, 'message':None}
        self._init_context(push_return_value=return_value)

        with boddle(method='GET', query={'command':'cmd', 'to':'dummy', 'params':json.dumps({'p1':'v1'}), 'timeout':3.0}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value)
            args = self.bus.push.call_args
            logging.debug(args[0][0])
            self.assertEqual(args[0][0].params, {'p1':'v1'})
            self.assertEqual(args[0][0].sender, 'rpcserver')

    def test_command_get_params_in_query(self):
        return_value = {'error':False, 'data':{'key':'value'}, 'message':None}
        self._init_context(push_return_value=return_value)

        with boddle(method='GET', query={'command':'cmd', 'to':'dummy', 'p1':'v1'}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value)
            args = self.bus.push.call_args
            logging.debug(args[0][0])
            self.assertEqual(args[0][0].params, {'p1':'v1'})

    def test_command_get_failed(self):
        return_value = {'error':True, 'data':None, 'message':'Command failed'}
        self._init_context(push_return_value=return_value)

        with boddle(method='GET', query={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value)

    def test_command_get_exception(self):
        self._init_context(push_side_effect=Exception('Test exception'))

        with boddle(method='GET', query={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {u'message': u'Test exception', u'data': None, u'error': True})

    def test_command_post(self):
        return_value = {'error':False, 'data':{'key':'value'}, 'message':None}
        self._init_context(push_return_value=return_value)

        with boddle(method='POST', json={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}, 'timeout':3.0}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value)
            args = self.bus.push.call_args
            logging.debug(args[0][0])
            self.assertEqual(args[0][0].params, {'p1':'v1'})
            self.assertEqual(args[0][0].sender, 'rpcserver')

    def test_command_post_no_params(self):
        return_value = {'error':False, 'data':{'key':'value'}, 'message':None}
        self._init_context(push_return_value=return_value)

        with boddle(method='POST', json={'command':'cmd', 'to':'dummy'}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value)
            args = self.bus.push.call_args
            logging.debug(args[0][0])
            self.assertEqual(args[0][0].sender, 'rpcserver')

    def test_command_post_not_json(self):
        return_value = {'error':False, 'data':{'key':'value'}, 'message':None}
        self._init_context(push_return_value=return_value)

        with boddle(method='POST', query={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {u'message': u'Invalid payload, json required.', u'data': None, u'error': True})

    def test_command_post_failed(self):
        return_value = {'error':True, 'data':None, 'message':'Command failed'}
        self._init_context(push_return_value=return_value)

        with boddle(method='POST', json={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value)

    def test_command_post_exception(self):
        self._init_context(push_side_effect=Exception('Test exception'))

        with boddle(method='POST', json={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {u'message': u'Test exception', u'data': None, u'error': True})

    def test_config(self):
        self._init_context()

        with boddle():
            c = json.loads(rpcserver.config())
            logging.debug('Config: %s' % c)
            self.assertTrue('modules' in c)
            self.assertTrue('events' in c)
            self.assertTrue('renderers' in c)
            self.assertTrue('devices' in c)
            self.assertTrue('drivers' in c)
            self.assertIsNotNone(c['modules'])
            self.assertIsNotNone(c['events'])
            self.assertIsNotNone(c['renderers'])
            self.assertIsNotNone(c['devices'])
            self.assertIsNotNone(c['drivers'])

    @patch('json.dumps')
    def test_config_exception(self, json_dumps_mock):
        json_dumps_mock.side_effect = [Exception('Test exception'), '{}']
        self._init_context()

        with boddle():
            c = json.loads(rpcserver.config())
            logging.debug('Config: %s' % c)
            self.assertEqual(c, {})

    def test_registerpoll(self):
        self._init_context()

        with boddle():
            resp = json.loads(rpcserver.registerpoll())
            logging.debug('Resp: %s' % resp)
            self.assertTrue('pollKey' in resp)
            self.assertIsNotNone(resp['pollKey'])
            self.assertTrue(self.bus.add_subscription.called_once)

    def test_poll_invalid_request(self):
        self._init_context()

        with boddle():
            resp = json.loads(rpcserver.poll())
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp, {u'message': u'Invalid request', u'data': None, u'error': True})

    def test_poll_no_pollkey(self):
        self._init_context()

        with boddle(json={}):
            resp = json.loads(rpcserver.poll())
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp, {u'message': u'Polling key is missing', u'data': None, u'error': True})

    def test_poll_no_bus(self):
        self._init_context(no_bus=True)

        with boddle(json={}):
            resp = json.loads(rpcserver.poll())
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp, {u'message': u'Bus not available', u'data': None, u'error': True})

    def test_poll_not_registered(self):
        self._init_context(is_subscribed_return_value=False)

        with boddle(json={'pollKey': '123-456-789'}):
            resp = json.loads(rpcserver.poll())
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp, {u'message': u'Client not registered', u'data': None, u'error': True})

    def test_poll(self):
        pull_resp = {
            'message': 'hello world'
        }
        self._init_context(pull_return_value=pull_resp)

        with boddle(json={'pollKey': '123-456-789'}):
            resp = json.loads(rpcserver.poll())
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp['data'], pull_resp['message'])
            self.assertEqual(resp['message'], '')

    def test_poll_no_message_available(self):
        pull_resp = {
            'message': 'hello world'
        }
        self._init_context(pull_side_effect=NoMessageAvailable())

        with boddle(json={'pollKey': '123-456-789'}):
            resp = json.loads(rpcserver.poll())
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp['data'], None)
            self.assertEqual(resp['message'], 'No message available')

    def test_poll_exception(self):
        pull_resp = {
            'message': 'hello world'
        }
        self._init_context(pull_side_effect=Exception('Test exception'))

        with boddle(json={'pollKey': '123-456-789'}):
            resp = json.loads(rpcserver.poll())
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp['data'], None)
            self.assertEqual(resp['message'], 'Internal error')

    def test_rpc_wrapper(self):
        self._init_context()

        with boddle(query={'p1':'v1', 'p2':'v2'}):
            rpcserver.rpc_wrapper('')
            self.assertTrue(self.inventory._rpc_wrapper.called)

    def test_default(self):
        self._init_context()

        with boddle():
            d = rpcserver.default('index.html')
            logging.debug('Default: %s' % type(d))
            self.assertTrue(isinstance(d, HTTPResponse))
            logging.debug('%s' % d.status)
            self.assertEqual(d.status, '200 OK')

    def test_index(self):
        self._init_context()

        with boddle():
            i = rpcserver.index()
            logging.debug('Index: %s' % type(i))
            self.assertTrue(isinstance(i, HTTPResponse))
            logging.debug('%s' % i.status)
            self.assertEqual(i.status, '200 OK')

    def test_logs(self):
        self._init_context()

        with patch('__builtin__.open', mock_open(read_data='raspiot log file content')) as mock_file:
            with boddle():
                resp = rpcserver.logs()
                logging.debug('Resp: %s' % resp)
            mock_file.assert_called_with('/var/log/raspiot.log', 'r')

    def test_authenticate(self):
        self._init_context()
        
        auth_enabled_restore = rpcserver.auth_enabled
        try:
            with boddle():
                rpcserver.auth_enabled = True
                c = rpcserver.config()
                logging.debug('Config: %s' % type(c))
                self.assertTrue(isinstance(c, HTTPError))
                logging.debug('%s' % c.status)
                self.assertEqual(c.status, '401 Unauthorized')

        finally:
            rpcserver.auth_enabled = auth_enabled_restore
            



if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","*test_*.py" --concurrency=thread test_rpcserver.py; coverage report -m -i
    unittest.main()

