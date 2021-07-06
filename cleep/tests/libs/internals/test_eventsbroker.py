#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, io, shutil
import sys, time
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from eventsbroker import EventsBroker
from cleep.libs.tests.lib import TestLib
from cleep.libs.internals.profileformatter import ProfileFormatter
from cleep.libs.internals.rendererprofile import RendererProfile
import unittest
import logging
from unittest.mock import Mock

class DummyProfile(RendererProfile):
    pass

class DummyFormatter(ProfileFormatter):

    def __init__(self, events_broker):
        self.events_broker = events_broker
        self.profile = DummyProfile()

    def get_event_instance(self, event_name):
        return self.events_broker.get_event_instance(event_name)

EVENT_CONTENT = """from cleep.libs.internals.event import Event
class %(event_class)s(Event):
    EVENT_NAME = '%(event_name)s'
    EVENT_PARAMS = []
    def __init__(self, params):
        Event.__init__(self, params)
"""
EVENT_CONTENT_INVALID_CLASSNAME = """from cleep.libs.internals.event import Event
class DummyEvent(Event):
    EVENT_NAME = '%(event_name)s'
    EVENT_PARAMS = []
    def __init__(self, params):
        Event.__init__(self, params)
"""
EVENT_CONTENT_SYNTAX_ERROR = """from cleep.libs.internals.event import Event
class %(event_class)s(Event):
    EVENT_NAME = '%(event_name)s'
    EVENT_PARAMS = []
    def __init__(self, params):
        Event.__init__(self, params)

    def invalid(self):
        # syntax error missing surrounding string quotes
        print(syntax error)
"""

class EventsBrokerTests(unittest.TestCase):

    MODULES_DIR = '/tmp/test_modules'
    CORE_EVENTS_DIR = '/tmp/test_core'
    EVENT_NAME1 = 'event1'
    EVENT_NAME2 = 'event2'

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.crash_report = Mock()
        self.internal_bus = Mock()
        self.formatters_broker = Mock()

        self.e = EventsBroker(debug_enabled=False)
        self.bootstrap = {
            'internal_bus': self.internal_bus,
            'formatters_broker': self.formatters_broker,
            'crash_report': self.crash_report,
            'external_bus': 'externalbusname',
        }

    def tearDown(self):
        if os.path.exists(self.MODULES_DIR):
            shutil.rmtree(self.MODULES_DIR)
        if os.path.exists(self.CORE_EVENTS_DIR):
            shutil.rmtree(self.CORE_EVENTS_DIR)

        # unload imported events
        if 'app1.app1EventTest' in sys.modules:  
            del sys.modules['app1.app1EventTest']
        if 'app2.app2EventTest' in sys.modules:  
            del sys.modules['app2.app2EventTest']
        if 'coreEventTest' in sys.modules:
            del sys.modules['coreEventTest']

    def _init_context(self, event_content=EVENT_CONTENT, add_apps=True, add_core=False):
        # build fake apps tree
        os.mkdir(self.MODULES_DIR)
        if add_apps:
            for app_name in ['app1', 'app2']:
                app_dir = os.path.join(self.MODULES_DIR, app_name)
                event_class = '%sEventTest' % app_name
                os.mkdir(app_dir)
                with io.open(os.path.join(app_dir, '__init__.py'), 'w') as fd:
                    fd.write('')
                with io.open(os.path.join(app_dir, '%s.py' % app_name), 'w') as fd:
                    fd.write('')
                with io.open(os.path.join(app_dir, '%s.py' % event_class), 'w') as fd:
                    fd.write(event_content % {
                        'event_class': event_class,
                        'event_name': 'test.event.%s' % app_name
                    })
        # inject fake apps root dir to import path
        sys.path.append(os.path.join(os.getcwd(), self.MODULES_DIR))

        # core events
        os.mkdir(self.CORE_EVENTS_DIR)
        if add_core:
            app_dir = self.CORE_EVENTS_DIR
            with io.open(os.path.join(app_dir, '__init__.py'), 'w') as fd:
                fd.write('')
            event_class = 'coreEventTest'
            with io.open(os.path.join(app_dir, '%s.py' % event_class), 'w') as fd:
                fd.write(event_content % {
                    'event_class': event_class,
                    'event_name': 'core.event.test'
                })

        # inject fake apps root dir to import path
        sys.path.append(os.path.join(os.getcwd(), self.CORE_EVENTS_DIR))

        # overwrite module paths
        self.e.MODULES_DIR = self.MODULES_DIR
        self.e.CORE_EVENTS_DIR = self.CORE_EVENTS_DIR
        self.e.PYTHON_CLEEP_APPS_IMPORT_PATH = ''
        self.e.PYTHON_CLEEP_CORE_EVENTS_IMPORT_PATH = ''

    def test_get_external_bus_name(self):
        self._init_context()
        self.e.configure(self.bootstrap)

        self.assertEqual(self.e._EventsBroker__get_external_bus_name(), 'externalbusname')

    def test_configure_with_event(self):
        self._init_context()
        self.e.configure(self.bootstrap)
        logging.debug(self.e.events_by_event)
        logging.debug(self.e.events_by_module)
        self.assertEqual(len(self.e.events_by_event.keys()), 2)
        self.assertEqual(len(self.e.events_by_module.keys()), 0)

    def test_configure_without_event(self):
        self._init_context(add_apps=False)
        self.e.configure(self.bootstrap)
        self.assertEqual(len(self.e.events_by_event.keys()), 0)
        self.assertEqual(len(self.e.events_by_module.keys()), 0)

    def test_enable_debug(self):
        e = EventsBroker(debug_enabled=True)
        self.assertEqual(e.logger.getEffectiveLevel(), logging.DEBUG)
        # restore original log level
        e.logger.setLevel(logging.getLogger().getEffectiveLevel())

    def test_invalid_modules_path(self):
        self.e.MODULES_DIR = 'dummy'
        self.e.PYTHON_CLEEP_IMPORT_PATH = ''

        with self.assertRaises(Exception) as cm:
            self.e.configure(self.bootstrap)
        self.assertTrue(str(cm.exception).startswith('Invalid modules path'))

    def test_load_events_from_core(self):
        self._init_context(add_apps=False, add_core=True)
        self.e.configure(self.bootstrap)

        logging.debug('Events: %s' % self.e.events_by_event)

        self.assertEqual(list(self.e.events_by_event.keys())[0], 'core.event.test')

    def test_load_events_from_core_crash_report(self):
        self._init_context(add_apps=False, add_core=True)
        self.e.CORE_EVENTS_DIR = '/tmp/dummy'

        with self.assertRaises(Exception) as cm:
            self.e.configure(self.bootstrap)
        self.assertEqual(str(cm.exception), 'Invalid core events path "/tmp/dummy"')
        self.crash_report.report_exception.assert_called_with({
            'message': 'Invalid core events path',
            'path': '/tmp/dummy'
        })

    def test_load_events_from_core_invalid_classname(self):
        self._init_context(add_apps=False, add_core=True, event_content=EVENT_CONTENT_INVALID_CLASSNAME)
        self.e.logger = Mock()
        self.e.configure(self.bootstrap)

        self.assertEqual(len(self.e.events_by_event), 0)
        self.e.logger.error.assert_called_with('Event class must have the same name than the filename "/tmp/test_core/coreEventTest.py"')

    def test_load_events_from_core_invalid_syntax(self):
        self._init_context(add_apps=False, add_core=True, event_content=EVENT_CONTENT_SYNTAX_ERROR)
        self.e.logger = Mock()
        self.e.configure(self.bootstrap)

        self.assertEqual(len(self.e.events_by_event), 0)
        self.e.logger.exception.assert_called_with('Event "coreEventTest" wasn\'t imported successfully. Please check event source code.')

    def test_load_events_from_apps_invalid_classname(self):
        self._init_context(event_content=EVENT_CONTENT_INVALID_CLASSNAME)
        self.e.logger = Mock()
        self.e.configure(self.bootstrap)
        
        self.assertEqual(len(self.e.events_by_event), 0)
        self.e.logger.error.assert_called_with('Event class must have the same name than the filename "/tmp/test_modules/app2/app2EventTest.py"')

    def test_load_events_from_apps_invalid_syntax(self):
        self._init_context(event_content=EVENT_CONTENT_SYNTAX_ERROR)
        self.e.logger = Mock()
        self.e.configure(self.bootstrap)
        
        self.assertEqual(len(self.e.events_by_event), 0)
        self.e.logger.exception.assert_called_with('Event "app2EventTest" wasn\'t imported successfully. Please check event source code.')

    def test_get_event_instance(self):
        self._init_context()
        self.e.configure(self.bootstrap)

        self.assertIsNotNone(self.e.get_event_instance('test.event.app1'))

    def test_get_event_instance_invalid_event(self):
        self._init_context()
        self.e.configure(self.bootstrap)

        with self.assertRaises(Exception) as cm:
            self.e.get_event_instance('dummy')
        self.assertEqual(str(cm.exception), 'Event "dummy" does not exist')

    def test_get_used_events(self):
        self._init_context()
        self.e.configure(self.bootstrap)

        # event not instanciated
        events = self.e.get_used_events()
        self.assertEqual(len(events), 0)

        # event instanciated by one app
        event = self.e.get_event_instance('test.event.app1')
        events = self.e.get_used_events()
        self.assertEqual(len(events), 1)
        logging.debug('Events: %s' % events)
        self.assertTrue('test.event.app1' in events)
        self.assertTrue('modules' in events['test.event.app1'])
        self.assertTrue('profiles' in events['test.event.app1'])
        self.assertTrue(self.__class__.__name__.lower() in events['test.event.app1']['modules'])

        # event instanciated by a formatter
        formatter = DummyFormatter(self.e)
        formatter.get_event_instance('test.event.app1')
        events = self.e.get_used_events()
        logging.debug('Events: %s' % events)
        self.assertTrue('DummyProfile' in events['test.event.app1']['profiles'])

    def test_get_modules_events(self):
        self._init_context()
        self.e.configure(self.bootstrap)

        event = self.e.get_event_instance('test.event.app1')
        events = self.e.get_modules_events()
        self.assertEqual(len(events), 1)
        self.assertTrue(self.__class__.__name__.lower() in events)

    def test_get_module_events(self):
        self._init_context()
        self.e.configure(self.bootstrap)

        event = self.e.get_event_instance('test.event.app1')
        logging.debug(self.e.events_by_module)
        self.assertEqual(len(self.e.events_by_module), 1)
        events = self.e.get_module_events(self.__class__.__name__.lower())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], 'test.event.app1')

    def test_get_module_events_invalid_module(self):
        self._init_context()
        self.e.configure(self.bootstrap)

        with self.assertRaises(Exception) as cm:
            self.e.get_module_events('dummy')
        self.assertEqual(str(cm.exception), 'Module name "dummy" is not referenced in Cleep')

    def test_set_event_renderable(self):
        self._init_context()
        self.e.configure(self.bootstrap)
        
        self.e.set_event_renderable('test.event.app1', 'renderer', False)
        logging.debug('Events not renderable: %s' % self.e.events_not_renderable)
        self.assertTrue('test.event.app1' in self.e.events_not_renderable)
        self.assertTrue('renderer' in self.e.events_not_renderable['test.event.app1'])

        self.e.set_event_renderable('test.event.app1', 'otherrenderer', False)
        logging.debug('Events not renderable: %s' % self.e.events_not_renderable)
        self.assertTrue('otherrenderer' in self.e.events_not_renderable['test.event.app1'])

        self.e.set_event_renderable('test.event.app1', 'renderer', True)
        logging.debug('Events not renderable: %s' % self.e.events_not_renderable)
        self.assertFalse('renderer' in self.e.events_not_renderable['test.event.app1'])
        
        self.e.set_event_renderable('test.event.app1', 'otherrenderer', True)
        logging.debug('Events not renderable: %s' % self.e.events_not_renderable)
        self.assertFalse('otherrenderer' in self.e.events_not_renderable['test.event.app1'])

    def test_is_event_renderable(self):
        self._init_context()
        self.e.configure(self.bootstrap)
        logging.debug('Events by event: %s' % self.e.events_by_event)
        logging.debug('Events not renderable: %s' % self.e.events_not_renderable)

        self.assertTrue(self.e.is_event_renderable('test.event.app1', 'renderer'))
        self.e.set_event_renderable('test.event.app1', 'renderer', False)
        self.assertFalse(self.e.is_event_renderable('test.event.app1', 'renderer'))


if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_eventsbroker.py; coverage report -m -i
    unittest.main()

