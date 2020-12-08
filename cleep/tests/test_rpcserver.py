#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests', ''))
import rpcserver
from cleep.libs.tests.lib import TestLib
from cleep.libs.drivers.driver import Driver
from cleep.common import MessageRequest, MessageResponse
from cleep.exception import NoMessageAvailable
import unittest
import logging
from boddle import boddle
from bottle import HTTPError, HTTPResponse
from unittest.mock import Mock, patch, mock_open, ANY
import json
import time
from collections import OrderedDict

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
        logging.basicConfig(level=logging.FATAL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        if rpcserver:
            rpcserver.sessions.clear()
            rpcserver.logger.setLevel(logging.getLogger().getEffectiveLevel())

    def _init_context(self, push_return_value=None, push_side_effect=None, no_bus=False, is_subscribed_return_value=None, is_subscribed_side_effect=None,
            pull_return_value=None, pull_side_effect=None, get_drivers_side_effect=None, get_drivers_gpio_exception=False, debug_enabled=False):
        self.crash_report = Mock()
        self.cleep_filesystem = Mock()
        self.internal_bus = Mock()
        if push_return_value is not None:
            self.internal_bus.push.return_value = push_return_value
        if push_side_effect is not None:
            self.internal_bus.push.side_effect = push_side_effect
        if pull_return_value is not None:
            self.internal_bus.pull.return_value = pull_return_value
        if pull_side_effect is not None:
            self.internal_bus.pull.side_effect = pull_side_effect
        if is_subscribed_return_value is not None:
            self.internal_bus.is_subscribed.return_value = is_subscribed_return_value
        if is_subscribed_side_effect is not None:
            self.intrnal_bus.is_subscribed.side_effect = is_subscribed_side_effect
        self.bootstrap = {
            'internal_bus': None if no_bus else self.internal_bus,
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
            logging.debug('Sessions: %s' % type(rpcserver.sessions.keys()))
            session_key = list(rpcserver.sessions.keys())[0]
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

    @patch('rpcserver.pywsgi.WSGIServer')
    @patch('rpcserver.app.run')
    def test_start_http_default_conf(self, mock_apprun, mock_wsgi):
        self._init_context()

        rpcserver.start()

        self.assertFalse(mock_wsgi.called)
        mock_apprun.assert_called_with(server='gevent', host='0.0.0.0', port=80, quiet=True, debug=False, reloader=False)

    @patch('rpcserver.pywsgi.WSGIServer')
    @patch('rpcserver.app.run')
    def test_start_http_custom_conf(self, mock_apprun, mock_wsgi):
        self._init_context()

        rpcserver.start('1.2.3.4', 8080)

        self.assertFalse(mock_wsgi.called)
        mock_apprun.assert_called_with(server='gevent', host='1.2.3.4', port=8080, quiet=True, debug=False, reloader=False)

    @patch('rpcserver.pywsgi.WSGIServer')
    @patch('rpcserver.app.run')
    @patch('rpcserver.os.path.exists')
    def test_start_https_default_conf(self, mock_ospathexists, mock_apprun, mock_wsgi):
        mock_ospathexists.return_value = True
        self._init_context()

        rpcserver.start(key='mykey', cert='mycert')

        mock_wsgi.assert_called_with(('0.0.0.0', 80), ANY, keyfile='mykey', certfile='mycert', log=ANY)
        self.assertFalse(mock_apprun.called)

    @patch('rpcserver.pywsgi.WSGIServer')
    @patch('rpcserver.app.run')
    @patch('rpcserver.os.path.exists')
    def test_start_https_custom_conf(self, mock_ospathexists, mock_apprun, mock_wsgi):
        mock_ospathexists.return_value = True
        self._init_context()

        rpcserver.start(host='1.2.3.4', port=8080, key='mykey', cert='mycert')

        mock_wsgi.assert_called_with(('1.2.3.4', 8080), ANY, keyfile='mykey', certfile='mycert', log=ANY)
        self.assertFalse(mock_apprun.called)

    @patch('rpcserver.pywsgi.WSGIServer')
    @patch('rpcserver.app.run')
    @patch('rpcserver.os.path.exists')
    def test_start_https_invalid_conf_fallback_http(self, mock_ospathexists, mock_apprun, mock_wsgi):
        mock_ospathexists.return_value = False
        self._init_context()

        rpcserver.start(key='mykey', cert='mycert')

        self.assertFalse(mock_wsgi.called)
        mock_apprun.assert_called_with(server='gevent', host='0.0.0.0', port=80, quiet=True, debug=False, reloader=False)

    @patch('rpcserver.app.run')
    def test_start_keyboardinterrupt(self, mock_apprun):
        mock_apprun.side_effect = KeyboardInterrupt()
        self._init_context()

        rpcserver.start()

        self.assertFalse(self.crash_report.report_exception.called)

    @patch('rpcserver.app.run')
    def test_start_exception(self, mock_apprun):
        mock_apprun.side_effect = Exception('Test exception')
        self._init_context()

        rpcserver.start()

        self.crash_report.report_exception.assert_called_with({'message': 'Fatal error starting rpcserver'})

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
            self.assertTrue(self.internal_bus.push.called_once)
            args = self.internal_bus.push.call_args
            self.assertTrue(isinstance(args[0][0], MessageRequest))
            self.assertEqual(args[0][1], 3.0)

            # without timeout
            r = rpcserver.send_command(command='cmd', to='module', params={})
            self.assertTrue(self.internal_bus.push.called_once)
            args = self.internal_bus.push.call_args
            logging.debug('Args: %s' % str(args))
            self.assertTrue(isinstance(args[0][0], MessageRequest))
            self.assertEqual(args[0][1], None)


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
        a1 = OrderedDict({
            "drivertype": "audio",
            "processing": True,
            "drivername": "driver1",
            "installed": False,
        })
        a2 = OrderedDict({
            "drivertype": "audio",
            "processing": False,
            "drivername": "driver2",
            "installed": True,
        })
        with boddle(method='POST'):
            d = json.loads(rpcserver.drivers())
            logging.debug('Drivers: %s' % d)
            self.assertEqual(len(d), 2)
            self.assertTrue(d[0] in [a1, a2])
            self.assertTrue(d[1] in [a1, a2])

    def test_drivers_one_driver_exception(self):
        self._init_context(get_drivers_gpio_exception=True)

        with boddle(method='POST'):
            d = json.loads(rpcserver.drivers())
            logging.debug('Drivers: %s' % d)
            self.assertEqual(len(d), 2)

    @patch('rpcserver.bottle')
    def test_upload(self, mock_bottle):
        mock_bottle.request.forms.get = Mock(side_effect=['upload_command', 'dummymodule', None])
        mock_fileupload = Mock(filename='myfilename')
        mock_bottle.request.files.get = Mock(return_value=mock_fileupload)
        original_sendcommand = rpcserver.send_command
        rpcserver.send_command = Mock()
        self._init_context()

        try:
            resp = rpcserver.upload()

            mock_fileupload.save.assert_called_with('/tmp/myfilename')
            rpcserver.send_command.assert_called_with('upload_command', 'dummymodule', {'filepath': '/tmp/myfilename'}, 10.0)
        finally:
            rpcserver.send_command = original_sendcommand

    @patch('rpcserver.bottle')
    def test_upload_with_params(self, mock_bottle):
        mock_bottle.request.forms.get = Mock(side_effect=['upload_command', 'dummymodule', {'param': 'value'}])
        mock_fileupload = Mock(filename='myfilename')
        mock_bottle.request.files.get = Mock(return_value=mock_fileupload)
        original_sendcommand = rpcserver.send_command
        rpcserver.send_command = Mock()
        self._init_context()

        try:
            resp = rpcserver.upload()

            mock_fileupload.save.assert_called_with('/tmp/myfilename')
            rpcserver.send_command.assert_called_with('upload_command', 'dummymodule', {'filepath': '/tmp/myfilename', 'param': 'value'}, 10.0)
        finally:
            rpcserver.send_command = original_sendcommand

    def test_upload_missing_params(self):
        self._init_context()

        with boddle():
            r = rpcserver.upload()
            logging.debug('Response: %s' % r)
            self.assertEqual(r, {'message': 'Missing parameters', 'data': None, 'error': True})

    @patch('rpcserver.bottle')
    @patch('rpcserver.os.path.exists')
    @patch('rpcserver.os.remove')
    def test_upload_file_already_exists(self, mock_osremove, mock_ospathexists, mock_bottle):
        mock_ospathexists.return_value = True
        mock_bottle.request.forms.get = Mock(side_effect=['upload_command', 'dummymodule', None])
        mock_fileupload = Mock(filename='myfilename')
        mock_bottle.request.files.get = Mock(return_value=mock_fileupload)
        original_sendcommand = rpcserver.send_command
        rpcserver.send_command = Mock()
        self._init_context()

        try:
            resp = rpcserver.upload()

            mock_osremove.assert_called_with('/tmp/myfilename')
        finally:
            rpcserver.send_command = original_sendcommand

    @patch('rpcserver.bottle')
    @patch('rpcserver.os.remove')
    def test_upload_exception(self, mock_osremove, mock_bottle):
        mock_bottle.request.forms.get = Mock(side_effect=Exception('Test exception'))
        mock_fileupload = Mock(filename='myfilename')
        mock_bottle.request.files.get = Mock(return_value=mock_fileupload)
        original_sendcommand = rpcserver.send_command
        rpcserver.send_command = Mock()
        self._init_context()

        try:
            resp = rpcserver.upload()

            self.assertEqual(resp['error'], True)
            self.assertEqual(resp['message'], 'Test exception')
            self.assertFalse(mock_osremove.called)
        finally:
            rpcserver.send_command = original_sendcommand

    @patch('rpcserver.bottle')
    @patch('rpcserver.os.path.exists')
    @patch('rpcserver.os.remove')
    def test_upload_exception_with_file_deletion(self, mock_osremove, mock_ospathexists, mock_bottle):
        mock_ospathexists.return_value = True
        mock_bottle.request.forms.get = Mock(side_effect=['upload_command', 'dummymodule', None])
        mock_fileupload = Mock(filename='myfilename')
        mock_fileupload.save.side_effect = Exception('Test exception')
        mock_bottle.request.files.get = Mock(return_value=mock_fileupload)
        original_sendcommand = rpcserver.send_command
        rpcserver.send_command = Mock()
        self._init_context()

        try:
            resp = rpcserver.upload()

            self.assertEqual(resp['error'], True)
            self.assertEqual(resp['message'], 'Test exception')
            mock_osremove.assert_called_with('/tmp/myfilename')
        finally:
            rpcserver.send_command = original_sendcommand

    def test_download_wo_params(self):
        message = MessageResponse(error=False, data={'filepath':'/tmp/123456789', 'filename':'dummy.test'}, message=None)
        self._init_context(push_return_value=message)

        with boddle(query={'command':'cmd', 'to':'dummy'}):
            resp = rpcserver.download()
            logging.debug('Response: %s' % resp)
            args = self.internal_bus.push.call_args
            self.assertTrue(isinstance(args[0][0], MessageRequest))
            logging.debug('MessageRequest: %s' % args[0][0].to_dict())
            self.assertEqual(args[0][0].to_dict(), {'broadcast': False, 'params': {}, 'command': 'cmd', 'sender': 'rpcserver', 'to': 'dummy'})

    def test_download_w_params(self):
        message = MessageResponse(error=False, data={'filepath':'/tmp/123456789', 'filename':'dummy.test'}, message=None)
        self._init_context(push_return_value=message)

        with boddle(query={'command':'cmd', 'to':'dummy', 'params': {'dummy': 'value'}}):
            resp = rpcserver.download()
            logging.debug('Response: %s' % resp)
            args = self.internal_bus.push.call_args
            self.assertTrue(isinstance(args[0][0], MessageRequest))
            logging.debug('MessageRequest: %s' % args[0][0].to_dict())
            self.assertEqual(args[0][0].to_dict(), {'broadcast': False, 'params': {'params': "{'dummy': 'value'}"}, 'command': 'cmd', 'sender': 'rpcserver', 'to': 'dummy'})

    def test_download_failed(self):
        self._init_context(push_return_value=MessageResponse(error=True, data=None, message='Command failed'))

        with boddle(query={'command':'cmd', 'to':'dummy', 'params': {'dummy': 'value'}}):
            resp = rpcserver.download()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {'message': 'Command failed', 'data': None, 'error': True})

    def test_download_exception(self):
        self._init_context(push_side_effect=Exception('Test exception'))

        with boddle(query={'command':'cmd', 'to':'dummy'}):
            resp = rpcserver.download()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {'message': 'Test exception', 'data': None, 'error': True})

    def test_command_get(self):
        return_value = MessageResponse(error=False, data={'key':'value'}, message=None)
        self._init_context(push_return_value=return_value)

        with boddle(method='GET', query={'command':'cmd', 'to':'dummy', 'params':json.dumps({'p1':'v1'}), 'timeout':3.0}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value.to_dict())
            args = self.internal_bus.push.call_args
            logging.debug(args[0][0])
            self.assertEqual(args[0][0].params, {'p1':'v1'})
            self.assertEqual(args[0][0].sender, 'rpcserver')

    def test_command_get_params_in_query(self):
        return_value = MessageResponse(error=False, data={'key':'value'}, message=None)
        self._init_context(push_return_value=return_value)

        with boddle(method='GET', query={'command':'cmd', 'to':'dummy', 'p1':'v1'}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value.to_dict())
            args = self.internal_bus.push.call_args
            logging.debug(args[0][0])
            self.assertEqual(args[0][0].params, {'p1':'v1'})

    def test_command_get_failed(self):
        return_value = MessageResponse(error=True, data=None, message='Command failed')
        self._init_context(push_return_value=return_value)

        with boddle(method='GET', query={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value.to_dict())

    def test_command_get_exception(self):
        self._init_context(push_side_effect=Exception('Test exception'))

        with boddle(method='GET', query={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {'message': 'Test exception', 'data': None, 'error': True})

    def test_command_post(self):
        return_value = MessageResponse(error=False, data={'key':'value'}, message=None)
        self._init_context(push_return_value=return_value)

        with boddle(method='POST', json={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}, 'timeout':3.0}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value.to_dict())
            args = self.internal_bus.push.call_args
            logging.debug(args[0][0])
            self.assertEqual(args[0][0].params, {'p1':'v1'})
            self.assertEqual(args[0][0].sender, 'rpcserver')

    def test_command_post_no_params(self):
        return_value = MessageResponse(error=False, data={'key':'value'}, message=None)
        self._init_context(push_return_value=return_value)

        with boddle(method='POST', json={'command':'cmd', 'to':'dummy'}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value.to_dict())
            args = self.internal_bus.push.call_args
            logging.debug(args[0][0])
            self.assertEqual(args[0][0].sender, 'rpcserver')

    def test_command_post_not_json(self):
        return_value = MessageResponse(error=False, data={'key':'value'}, message=None)
        self._init_context(push_return_value=return_value)

        with boddle(method='POST', query={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {'message': 'Invalid payload, json required.', 'data': None, 'error': True})

    def test_command_post_failed(self):
        return_value = MessageResponse(error=True, data=None, message='Command failed')
        self._init_context(push_return_value=return_value)

        with boddle(method='POST', json={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value.to_dict())

    def test_command_post_exception(self):
        self._init_context(push_side_effect=Exception('Test exception'))

        with boddle(method='POST', json={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {'message': 'Test exception', 'data': None, 'error': True})

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
            self.assertTrue(self.internal_bus.add_subscription.called_once)

    def test_poll_invalid_request(self):
        self._init_context()

        with boddle():
            resp = json.loads(rpcserver.poll())
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp, {'message': 'Invalid request', 'data': None, 'error': True})

    def test_poll_no_pollkey(self):
        self._init_context()

        with boddle(json={}):
            resp = json.loads(rpcserver.poll())
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp, {'message': 'Polling key is missing', 'data': None, 'error': True})

    def test_poll_no_bus(self):
        self._init_context(no_bus=True)

        with boddle(json={}):
            resp = json.loads(rpcserver.poll())
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp, {'message': 'Bus not available', 'data': None, 'error': True})

    def test_poll_not_registered(self):
        self._init_context(is_subscribed_return_value=False)

        with boddle(json={'pollKey': '123-456-789'}):
            resp = json.loads(rpcserver.poll())
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp, {'message': 'Client not registered', 'data': None, 'error': True})

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
            self.assertTrue(self.inventory.rpc_wrapper.called)

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
        message = 'cleep log file content'
        self.cleep_filesystem.read_data.return_value = message

        with boddle():
            resp = rpcserver.logs()
            logging.debug('Resp: %s' % resp)
            self.assertTrue(message in resp)

        self.cleep_filesystem.read_data.assert_called_with('/var/log/cleep.log', 'r')

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
    # coverage run --omit="/usr/local/lib/python*/*","*test_*.py" --concurrency=thread test_rpcserver.py; coverage report -m -i
    unittest.main()

