#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.crashreport import CrashReport
from cleep.libs.internals.eventsbroker import EventsBroker
from cleep.libs.internals.profileformattersbroker import ProfileFormattersBroker
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.libs.internals.criticalresources import CriticalResources
from cleep.exception import NoResponse
from cleep import bus
from cleep.libs.internals import event
import cleep.libs.internals.tools as tools
from cleep.common import ExecutionStep
from cleep.libs.internals.drivers import Drivers
from threading import Event
import os
import logging
import types
from mock import MagicMock

TRACE = tools.TRACE

class AnyArg(object):
    """
    Used to perform a "any" params comparison during an assert_called_with
    """
    def __eq__(a, b):
        return True

class TestSession():
    """
    Create session to be able to run tests on a Cleep module
    """

    def __init__(self, testcase):
        """
        Constructor
        """
        tools.install_trace_logging_level()

        self.testcase = testcase
        self.__setup_executed = False
        self.__module_class = None
        self.__debug_enabled = False
        self.crash_report = None
        self.cleep_filesystem = None

    def __build_bootstrap_objects(self, debug):
        """
        Build bootstrap object with appropriate singleton instances
        All data is pre-configured for tests
        """
        self.crash_report = MagicMock()

        events_broker = EventsBroker(debug)
        events_broker.get_event_instance = self._events_broker_get_event_instance_mock

        message_bus = bus.MessageBus(self.crash_report, debug)
        message_bus.push = self._message_bus_push_mock

        # enable writings during tests
        fs = CleepFilesystem()
        fs.enable_write(True, True)
        self.cleep_filesystem = MagicMock()

        critical_resources = CriticalResources(debug)
        
        core_join_event = Event()
        core_join_event.set()

        return {
            'message_bus': message_bus,
            'events_broker': events_broker,
            'formatters_broker': EventsBroker(debug),
            'cleep_filesystem': self.cleep_filesystem,
            'crash_report': self.crash_report,
            'module_join_event': Event(),
            'core_join_event': core_join_event,
            'test_mode': True,
            'critical_resources': critical_resources,
            'execution_step': ExecutionStep(),
            'drivers': Drivers(debug),
            'log_file': '/tmp/cleep.log',
        }

    def setup(self, module_class, bootstrap={}):
        """
        Instanciate specified module overwriting some stuff and initalizing it with appropriate content
        Can be called during test setup.

        Args:
            module_class (type): module class type
            bootstrap (dict): overwrite default bootstrap by specified one. You dont have to specify
                              all items, only specified ones will be replaced.

        Returns:
            Object: returns module_class instance
        """
        # logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.__debug_enabled = True if logging.getLogger().getEffectiveLevel() <= logging.DEBUG else False

        # bootstrap object
        self.bootstrap = self.__build_bootstrap_objects(self.__debug_enabled)
        self.bootstrap.update(bootstrap)
        self.__bus_command_handlers = {}
        self.__event_handlers = {}
        self.__module_class = None
        self.__module_instance = None

        # config
        module_class.CONFIG_DIR = '/tmp'
        
        # instanciate
        self.__module_instance = module_class(self.bootstrap, self.__debug_enabled)

        self.__setup_executed = True
        return self.__module_instance

    def start_module(self, module_instance):
        """
        Start module. Use this function if you disable module launch during setup

        Args:
            module_instance (instance): module instance returned by setup function
        """
        # start instace
        module_instance.start()

        # wait for module to be configured
        self.bootstrap['module_join_event'].wait()

        # wait for module to be really started
        module_instance._wait_is_started()
        self.logger.debug('===== module started =====')

    def respawn_module(self):
        """
        Respawn module instance (simulate module start)

        Returns:
            Object: returns module_class instance or None if setup not executed before
        """
        if not self.__setup_executed:
            return None

        # stop current running module instance
        self.__module_instance.stop()
        self.__module_instance.join()

        # start new module instance
        return self.setup(self.__module_class, self.__debug_enabled)

    def clean(self):
        """
        Clean all stuff.
        Can be called during test tear down.
        """
        if not self.__setup_executed:
            return

        # process
        if self.__module_instance:
            self.__module_instance.stop()
            self.__module_instance.join()

        # config
        if hasattr(self.__module_instance, 'MODULE_CONFIG_FILE'):
            path = os.path.join(self.__module_instance.CONFIG_DIR, self.__module_instance.MODULE_CONFIG_FILE)
            if os.path.exists(path):
                os.remove(path)

        if self.__module_instance:
            del self.__module_instance
            self.__module_instance = None

    def get_handled_commands(self):
        """
        Return list of handled commands
        
        Returns:
            list (string): list of commands
        """
        return list(self.__bus_command_handlers.keys())

    def make_mock_command(self, command_name, data=None, fail=False, no_response=False):
        """
        Help user to make a ready to user command object

        Args:
            command_name (string): command name
            data (any): data to return as command result
            fail (bool): set True to simulate command failure
            no_response (bool): set True to simulate command no response

        Returns:
            dict: awaited mocked command object
        """
        return {
            'command': command_name,
            'data': data,
            'fail': fail,
            'noresponse': no_response
        }

    def add_mock_command(self, command):
        """
        Mock command sent to internal message bus

        Args:
            command (dict): command object as returned by make_mock_command function
        """
        if command['command'] in self.__bus_command_handlers:
            self.logger.warning('Mock command "%s" already mocked' % command['command'])
            return

        self.__bus_command_handlers[command['command']] = {
            'data': command['data'],
            'calls': 0,
            'fail': command['fail'],
            'noresponse': command['noresponse'],
            'lastparams': None,
            'last_to': None,
        }

    def set_mock_command_succeed(self, command_name):
        """
        Flag command as succeed will return specified data

        Args:
            command_name (string): command name
        """
        if command_name in self.__bus_command_handlers:
            self.__bus_command_handlers[command_name]['fail'] = False
            self.__bus_command_handlers[command_name]['noresponse'] = False

    def set_mock_command_fail(self, command_name):
        """
        Flag command as fail will return error when called

        Args:
            command_name (string): command name
        """
        if command_name in self.__bus_command_handlers:
            self.__bus_command_handlers[command_name]['fail'] = True
            self.__bus_command_handlers[command_name]['noresponse'] = False

    def set_mock_command_no_response(self, command_name):
        """
        Flag command as not responding

        Args:
            command_name (string): command name
        """
        if command_name in self.__bus_command_handlers:
            self.__bus_command_handlers[command_name]['fail'] = False
            self.__bus_command_handlers[command_name]['noresponse'] = True

    def command_called(self, command_name):
        """
        Return False if command not called

        Args:
            command_name (string): command name

        Returns:
            bool: True if command called, False otherwise
        """
        return True if self.command_call_count(command_name) else False

    def command_call_count(self, command_name):
        """
        Return how many times the command handler has been called

        Args:
            command_name (string): command name

        Returns:
            int: number of times handler has been called
        """
        if command_name in self.__bus_command_handlers:
            return self.__bus_command_handlers[command_name]['calls']

        return 0

    def command_called_with(self, command_name, params, to=None):
        """
        Return True if command is called with specified parameters

        Args:
            command_name (string): command name
            params (dict): command parameters
            to (string): command recipient. If to is specified, the value is used to check command validity

        Returns:
            bool: True if command called with params
        """
        if command_name in self.__bus_command_handlers:
            params_check = self.__bus_command_handlers[command_name]['lastparams'] == params
            params_error = ('  Expected params: %s\n  Current params: %s' % (params, self.__bus_command_handlers[command_name]['lastparams'])
                            if not params_check else '')
            to_check = True if to is None else self.__bus_command_handlers[command_name]['lastto'] == to
            to_error = ('  Expected to: %s\n  Current to: %s' % (to, self.__bus_command_handlers[command_name]['lastto'])
                        if not to_check else '')

            check = params_check and to_check
            if not check:
                self.logger.fatal('TEST: command_called_with failed:\n%s%s%s' % (params_error, ('\n' if params_error else ''), to_error))
            return check

        self.logger.fatal('TEST: event_called_with failed: command not mocked. Please use "session.add_mock_command"')
        return False

    def assert_command_called_with(self, command_name, params, to=None):
        """
        Same as command_called_wth but with assertion
        """
        # check command call
        if command_name not in self.__bus_command_handlers:
            self.testcase.assertTrue(False, 'Command "%s" was not called' % command_name)

        # check command params
        self.testcase.assertDictEqual(
            self.__bus_command_handlers[command_name]['lastparams'],
            params,
            'Command "%s" are differents' % command_name,
        )

        # check command recipient
        if to is not None:
            self.testcase.assertEqual(
                self.__bus_command_handlers[command_name]['lastto'],
                to,
                'Command "%s" recipient is different' % command_name,
            )

    def event_called(self, event_name):
        """
        Return True if event was called

        Args:
            event_name (string): event name

        Returns:
            bool: True if event called
        """
        return True if self.event_call_count(event_name) > 0 else False

    def assert_event_called(self, event_name):
        """
        Same as event_called with assertion
        """
        self.testcase.assertTrue(self.event_call_count(event_name) > 0, 'Event "%s" was not called' % event_name)

    def event_call_count(self, event_name):
        """
        Returns event calls count

        Returns:
            int: number of event calls count or 0 if event not handled
        """
        if event_name in self.__event_handlers:
            return self.__event_handlers[event_name]['sends']

        return 0

    def event_called_with(self, event_name, params):
        """
        Return True if event was called with specified arguments

        Args:
            event_name (string): event name
            params (dict): dict of parameters

        Returns:
            bool: True if event called with params
        """
        last_params = self.get_last_event_params(event_name)
        check = True if params == last_params else False
        if not check:
            self.logger.fatal('TEST: event_called_with failed:\n  Expected: %s\n  Current:  %s' % (params, last_params))
        return check

    def assert_event_called_with(self, event_name, params):
        """
        Assert event called with

        Args:
            event_name (string): event name
            params (dict): event parameters
        """
        self.testcase.assertTrue(self.event_call_count(event_name) > 0, 'Event "%s" was not called' % event_name)
        last_params = self.get_last_event_params(event_name)
        self.testcase.assertDictEqual(params, last_params, 'Event "%s" parameters are differents' % event_name)

    def get_last_event_params(self, event_name):
        """
        Returns event params of last call

        Returns:
            dict: last event call params or None if event not handled
        """
        if event_name in self.__event_handlers:
            return self.__event_handlers[event_name]['lastparams']

        return None

    def _message_bus_push_mock(self, request, timeout):
        """
        Mocked message bus push method
        """
        self.logger.debug('TEST: Process command %s' % request)
        if request and request.command in self.__bus_command_handlers:
            self.logger.debug('TEST: push command "%s"' % request.command)
            self.__bus_command_handlers[request.command]['calls'] += 1
            self.__bus_command_handlers[request.command]['lastparams'] = request.params
            self.__bus_command_handlers[request.command]['lastto'] = request.to

            if self.__bus_command_handlers[request.command]['fail']:
                self.logger.debug('TEST: command "%s" fails for tests' % request.command)
                return {
                    'error': True,
                    'data': None,
                    'message': 'TEST: command fails for tests',
                }
            elif self.__bus_command_handlers[request.command]['noresponse']:
                self.logger.debug('TEST: command "%s" returns no response for tests' % request.command)
                raise NoResponse(request.to, 0, request.params)

            return {
                'error': False,
                'data': self.__bus_command_handlers[request.command]['data'],
                'message': '',
            }

        self.logger.fatal('TEST: Command "%s" is not handled. Please mock it.' % request.command)
        return {
            'error': True,
            'data': None,
            'message': 'TEST: Command "%s" is not handled. Please mock it.' % request.command,
        }

    def _events_broker_get_event_instance_mock(self, event_name):
        """
        Create monkey-patched Event of specified name
        """
        e_ = event.Event
        e_.EVENT_NAME = event_name
        instance = e_(self.bootstrap['message_bus'], self.bootstrap['formatters_broker'])
        self.__event_handlers[event_name] = {
            'sends': 0,
            'lastparams': None,
            'lastdeviceid': None,
        }
        event_handlers = self.__event_handlers
        # monkey patch new event send() method
        def event_send_mock(self, params=None, device_id=None, to=None, render=True):
            self.logger.debug('TEST: send event "%s"' % event_name)
            event_handlers[event_name]['sends'] += 1
            event_handlers[event_name]['lastparams'] = params
            event_handlers[event_name]['lastdeviceid'] = device_id
        instance.send = types.MethodType(event_send_mock, instance)

        return instance

    @staticmethod
    def clone_class(base_class):
        """
        Clone specified base class. This can be useful when you need to alter class (adding mock)
        keeping original one clean.

        Args:
            base_class (Class): class object (not instance!)

        Returns:
            Class: cloned class that can be instanciated. Cloned class name is prefixed by "C"
        """
        class ClonedClass(base_class):
            pass
        ClonedClass.__name__ = 'C%s' % base_class.__name__

        return ClonedClass

