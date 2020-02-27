#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, io, shutil
import sys, time
sys.path.append('%s/../../../libs/internals' % os.getcwd())
from eventsbroker import EventsBroker
from raspiot.libs.tests.lib import TestLib
from raspiot.libs.internals.formatter import Formatter
from raspiot.libs.internals.rendererprofile import RendererProfile
import unittest
import logging
from mock import Mock

class DummyProfile(RendererProfile):
    pass

class DummyFormatter(Formatter):

    def __init__(self, events_broker):
        self.events_broker = events_broker
        self.profile = DummyProfile()

    def get_event_instance(self, event_name):
        return self.events_broker.get_event_instance(event_name)

EVENT_CONTENT = u"""from raspiot.libs.internals.event import Event
class %(event_class)s(Event):
    EVENT_NAME = u'%(event_name)s'
    EVENT_PARAMS = []
    def __init__(self, bus, formatters_broker):
        Event.__init__(self, bus, formatters_broker)
"""
EVENT_CONTENT_INVALID_CLASSNAME = u"""from raspiot.libs.internals.event import Event
class DummyEvent(Event):
    EVENT_NAME = u'%(event_name)s'
    EVENT_PARAMS = []
    def __init__(self, bus, formatters_broker):
        Event.__init__(self, bus, formatters_broker)
"""
EVENT_CONTENT_SYNTAX_ERROR = u"""from raspiot.libs.internals.event import Event
class %(event_class)s(Event):
    EVENT_NAME = u'%(event_name)s'
    EVENT_PARAMS = []
    def __init__(self, bus, formatters_broker):
        Event.__init__(self, bus, formatters_broker)

    def invalid(self):
        # syntax error missing surrounding string quotes
        print(syntax error)
"""

class EventsBrokerTests(unittest.TestCase):

    MODULES_DIR = 'test_modules'
    EVENT_NAME1 = 'event1'
    EVENT_NAME2 = 'event2'

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.CRITICAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.crash_report = Mock()
        self.bus = Mock()
        self.formatters_broker = Mock()

        self.e = EventsBroker(debug_enabled=False)
        self.bootstrap = {
            'message_bus': self.bus,
            'formatters_broker': self.formatters_broker,
            'crash_report': self.crash_report,
        }

    def tearDown(self):
        if os.path.exists(self.MODULES_DIR):
            shutil.rmtree(self.MODULES_DIR)

        # unload imported events
        if 'app1.app1EventTest' in sys.modules:  
            del sys.modules['app1.app1EventTest']
        if 'app2.app2EventTest' in sys.modules:  
            del sys.modules['app2.app2EventTest']

    def _init_context(self, event_content=EVENT_CONTENT, add_apps=True):
        # build fake apps tree
        os.mkdir(self.MODULES_DIR)
        if add_apps:
            for app_name in ['app1', 'app2']:
                app_dir = os.path.join(self.MODULES_DIR, app_name)
                event_class = '%sEventTest' % app_name
                os.mkdir(app_dir)
                with io.open(os.path.join(app_dir, '__init__.py'), 'w') as fd:
                    fd.write(u'')
                with io.open(os.path.join(app_dir, '%s.py' % app_name), 'w') as fd:
                    fd.write(u'')
                with io.open(os.path.join(app_dir, '%s.py' % event_class), 'w') as fd:
                    fd.write(event_content % {
                        'event_class': event_class,
                        'event_name': 'test.event.%s' % app_name
                    })
        # inject fake apps root dir to import path
        sys.path.append(os.path.join(os.getcwd(), self.MODULES_DIR))

        # overwrite module paths
        self.e.MODULES_DIR = '../../tests/libs/internals/%s' % self.MODULES_DIR
        self.e.PYTHON_RASPIOT_IMPORT_PATH = ''

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

    def test_invalid_modules_path(self):
        self.e.MODULES_DIR = 'dummy'
        self.e.PYTHON_RASPIOT_IMPORT_PATH = ''

        with self.assertRaises(Exception) as cm:
            self.e.configure(self.bootstrap)
        self.assertTrue(cm.exception.message.startswith('Invalid modules path'))

    def test_load_events_invalid_classname(self):
        self._init_context(event_content=EVENT_CONTENT_INVALID_CLASSNAME)
        self.e.configure(self.bootstrap)
        
        self.assertEqual(len(self.e.events_by_event), 0)

    def test_load_events_invalid_syntax(self):
        self._init_context(event_content=EVENT_CONTENT_SYNTAX_ERROR)
        self.e.configure(self.bootstrap)
        
        self.assertEqual(len(self.e.events_by_event), 0)

    def test_get_event_instance(self):
        self._init_context()
        self.e.configure(self.bootstrap)

        self.assertIsNotNone(self.e.get_event_instance('test.event.app1'))

    def test_get_event_instance_invalid_event(self):
        self._init_context()
        self.e.configure(self.bootstrap)

        with self.assertRaises(Exception) as cm:
            self.e.get_event_instance('dummy')
        self.assertEqual(cm.exception.message, 'Event "dummy" does not exist')

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
        self.assertEqual(cm.exception.message, 'Module name "dummy" is not referenced in raspiot')



if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_eventsbroker.py; coverage report -m
    unittest.main()
