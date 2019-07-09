#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.crashreport import CrashReport
from raspiot.libs.internals.eventsbroker import EventsBroker
from raspiot.libs.internals.formattersbroker import FormattersBroker
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.libs.internals.criticalresources import CriticalResources
from raspiot.utils import NoResponse
from raspiot import bus
from raspiot.libs.internals import event
import raspiot.libs.internals.tools as tools
from raspiot.utils import ExecutionStep
from raspiot.libs.internals.drivers import Drivers
from threading import Event
import os
import logging
import types

logging.basicConfig(format=u'%(name)-12s[%(filename)s:%(lineno)d] %(levelname)-5s : %(message)s')

class Session():
    """
    Create session to be able to run tests on a Cleep module
    """

    def __init__(self, log_level):
        """
        Constructor

        Args:
            debug_enabled (bool): set it to True to enable debug log messages
        """
        logging.getLogger().setLevel(log_level)
        self.logger = logging.getLogger('TestSession')
        self.logger.setLevel(log_level)
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        tools.install_trace_logging_level()
        self.__debug_enabled = True if log_level==logging.DEBUG else False
        self.bootstrap = self.__build_bootstrap_objects(self.__debug_enabled)
        self.__setup_executed = False
        self.__bus_command_handlers = {}
        self.__event_handlers = {}
        self.__module_class = None
        self.__module_instance = None

    def __build_bootstrap_objects(self, debug):
        """
        Build bootstrap object with appropriate singleton instances
        All data is pre-configured for tests
        """
        debug = False
        crash_report = CrashReport(None, u'Test', u'0.0.0', {}, debug, True)

        events_broker = EventsBroker(debug)
        events_broker.get_event_instance = self._events_broker_get_event_instance_mock

        message_bus = bus.MessageBus(crash_report, debug)
        message_bus.push = self._message_bus_push_mock

        cleep_filesystem = CleepFilesystem()
        #enable writings during tests
        cleep_filesystem.enable_write(True, True)

        critical_resources = CriticalResources(debug)

        return {
            'message_bus': message_bus,
            'events_broker': events_broker,
            'formatters_broker': EventsBroker(debug),
            'cleep_filesystem': cleep_filesystem,
            'crash_report': crash_report,
            'join_event': Event(),
            'test_mode': True,
            'critical_resources': critical_resources,
            'execution_step': ExecutionStep(),
            'drivers': Drivers(debug),
        }

    def setup(self, module_class, debug_enabled = False):
        """
        Instanciate specified module overwriting some stuff and initalizing it with appropriate content
        Can be called during test setup.

        Args:
            module_class (type): module class type
            debug_enable (bool): enable debug on module

        Returns:
            Object: returns module_class instance
        """
        self.__setup_executed = True
        self.__module_class = module_class
        self.__debug_enabled = debug_enabled

        #config
        module_class.CONFIG_DIR = '/tmp'
        
        #instanciate
        self.__module_instance = module_class(self.bootstrap, debug_enabled)
        self.__module_instance.start()

        #wait for module to be started
        self.bootstrap['join_event'].wait()

        return self.__module_instance

    def respawn_module(self):
        """
        Respawn module instance (simulate module start)

        Returns:
            Object: returns module_class instance or None if setup not executed before
        """
        if not self.__setup_executed:
            return None

        #stop current running module instance
        self.__module_instance.stop()
        self.__module_instance.join()

        #start new module instance
        return self.setup(self.__module_class, self.__debug_enabled)

    def clean(self):
        """
        Clean all stuff.
        Can be called during test tear down.
        """
        if not self.__setup_executed:
            return

        #process
        self.__module_instance.stop()
        self.__module_instance.join()

        #config
        path = os.path.join(self.__module_instance.CONFIG_DIR, self.__module_instance.MODULE_CONFIG_FILE)
        if os.path.exists(path):
            os.remove(path)


    def mock_command(self, command, handler, fail=False, no_response=False):
        """
        Mock command handler

        Args:
            command (string): name of command to handle
            handler (function): function to call when command triggered
            fail (bool): if True will return error like if the command has failed
            no_response: if True will simulate no response
        """
        self.__bus_command_handlers[command] = {
            u'handler': handler,
            u'calls': 0,
            u'fail': fail,
            u'no_response': no_response
        }

    def succeed_command(self, command):
        """
        Flag command as succeed will return handler output
        """
        if command in self.__bus_command_handlers:
            self.__bus_command_handlers[command][u'fail'] = False

    def fail_command(self, command):
        """
        Flag command as fail will return error when called
        """
        if command in self.__bus_command_handlers:
            self.__bus_command_handlers[command][u'fail'] = True

    def get_command_calls(self, command):
        """
        Return how many times the command handler has been called

        Args:
            command (string): command name

        Returns:
            int: number of times handler has been called
        """
        if command in self.__bus_command_handlers:
            return self.__bus_command_handlers[command][u'calls']

        return 0

    def get_event_calls(self, event_name):
        """
        Returns event calls count

        Returns:
            int: number of event calls count or 0 if event not handled
        """
        if event_name in self.__event_handlers:
            return self.__event_handlers[event_name][u'sends']

        return 0

    def get_event_last_params(self, event_name):
        """
        Returns event params of last call

        Returns:
            dict: last event call params or None if event not handled
        """
        if event_name in self.__event_handlers:
            return self.__event_handlers[event_name][u'lastparams']

        return None

    def _message_bus_push_mock(self, request, timeout):
        """
        Mocked message bus push method
        """
        if request and request.command in self.__bus_command_handlers:
            self.logger.debug('TEST: push command "%s"' % request.command)
            self.__bus_command_handlers[request.command][u'calls'] += 1

            if self.__bus_command_handlers[request.command][u'fail']:
                self.logger.debug('TEST: command "%s" fails for tests' % request.command)
                return {
                    'error': True,
                    'data': None,
                    'message': 'TEST: command fails for tests'
                }
            elif self.__bus_command_handlers[request.command][u'no_response']:
                self.logger.debug('TEST: command "%s" returns no response for tests' % request.command)
                return None

            res = self.__bus_command_handlers[request.command][u'handler']()
            return res

        return {
            'error': True,
            'data': None,
            'message': 'TEST: Command "%s" not handled. Please mock it.' % request.command
        }

    def _events_broker_get_event_instance_mock(self, event_name):
        """
        Create monkey-patched Event of specified name
        """
        e_ = event.Event
        e_.EVENT_NAME = event_name
        instance = e_(self.bootstrap['message_bus'], self.bootstrap['formatters_broker'], self.bootstrap['events_broker'])
        self.__event_handlers[event_name] = {
            u'sends': 0,
            u'lastparams': None,
            u'lastdeviceid': None,
        }
        event_handlers = self.__event_handlers
        #monkey patch new event send() method
        def event_send_mock(self, params=None, device_id=None, to=None, render=True):
            self.logger.debug('TEST: send event "%s"' % event_name)
            event_handlers[event_name][u'sends'] += 1
            event_handlers[event_name][u'lastparams'] = params
            event_handlers[event_name][u'lastdeviceid'] = device_id
        instance.send = types.MethodType(event_send_mock, instance)

        return instance

