from raspiot.libs.internals.crashreport import CrashReport
from raspiot.eventsFactory import EventsFactory
from raspiot.formattersFactory import FormattersFactory
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.utils import NoResponse
from raspiot import bus
from raspiot.events import event
import raspiot.libs.internals.tools as tools
from threading import Event
import os
import logging
import types


class Session():
    """
    Create session to be able to run tests on a Cleep module
    """

    def __init__(self, debug_enabled=False):
        """
        Constructor

        Args:
            debug_enabled (bool): set it to True to enable debug log messages
        """
        tools.install_trace_logging_level()
        self.bootstrap = self.__build_bootstrap_objects(debug_enabled)
        self.__setup_executed = False
        self.__bus_command_handlers = {}
        self.__event_handlers = {}
        self.__module_class = None
        self.__module_instance = None
        self.__debug_enabled = False

    def __build_bootstrap_objects(self, debug):
        """
        Build bootstrap object with appropriate singleton instances
        All data is pre-configured for tests
        """
        debug = False
        crash_report = CrashReport(None, u'Test', u'0.0.0', {}, debug, True)

        events_factory = EventsFactory(debug)
        events_factory.get_event_instance = self._events_factory_get_event_instance_mock

        message_bus = bus.MessageBus(crash_report, debug)
        message_bus.push = self._message_bus_push_mock

        cleep_filesystem = CleepFilesystem()
        #enable writings during tests
        cleep_filesystem.enable_write(True, True)

        return {
            'message_bus': message_bus,
            'events_factory': events_factory,
            'formatters_factory': EventsFactory(debug),
            'cleep_filesystem': cleep_filesystem,
            'crash_report': crash_report,
            'join_event': Event(),
            'test_mode': True
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

        #config
        path = os.path.join(self.__module_instance.CONFIG_DIR, self.__module_instance.MODULE_CONFIG_FILE)
        if os.path.exists(path):
            os.remove(path)

        #process
        self.__module_instance.stop()
        self.__module_instance.join()

    def add_command_handler(self, command, handler, disabled=False):
        """
        Add command handler

        Args:
            command (string): name of command to handle
            handler (function): function to call when command triggered
            disable (bool): if True will return error like if the command has failed
        """
        self.__bus_command_handlers[command] = {
            u'handler': handler,
            u'calls': 0,
            u'disabled': False
        }

    def enable_command_handler(self, command):
        """
        Enable specified command, will return valid response
        """
        if command in self.__bus_command_handlers:
            self.__bus_command_handlers[command][u'disabled'] = False

    def disable_command_handler(self, command):
        """
        Disable specified command, useful to return temporarly an error
        """
        if command in self.__bus_command_handlers:
            self.__bus_command_handlers[command][u'disabled'] = True

    def get_command_handler_calls(self, command):
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

    def get_event_send_calls(self, event_name):
        """
        """
        if event_name in self.__event_handlers:
            return self.__event_handlers[event_name][u'sends']

        return 0

    def _message_bus_push_mock(self, request, timeout):
        """
        Mocked message bus push method
        """
        if request and request.command in self.__bus_command_handlers:
            logging.debug('TEST: push command "%s"' % request.command)
            self.__bus_command_handlers[request.command][u'calls'] += 1

            if self.__bus_command_handlers[request.command][u'disabled']:
                logging.debug('TEST: command "%s" disabled for tests')
                return {
                    'error': True,
                    'data': None,
                    'message': 'TEST: command disabled for tests'
                }

            res = self.__bus_command_handlers[request.command][u'handler']()
            return res

        return {
            'error': True,
            'data': None,
            'message': 'TEST: Command "%s" not handled. Please mock it.' % request.command
        }

    def _events_factory_get_event_instance_mock(self, event_name):
        """
        Create monkey-patched Event of specified name
        """
        e_ = event.Event
        e_.EVENT_NAME = event_name
        instance = e_(self.bootstrap['message_bus'], self.bootstrap['formatters_factory'], self.bootstrap['events_factory'])
        self.__event_handlers[event_name] = {
            u'sends': 0
        }
        event_handler = self.__event_handlers[event_name]
        #monkey patch new event send() method
        def event_send_mock(self, params=None, device_id=None, to=None, render=True):
            logging.debug('TEST: send event "%s"' % event_name)
            event_handler[u'sends'] += 1
        instance.send = types.MethodType(event_send_mock, instance)

        return instance



