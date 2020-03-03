#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, io, shutil
import sys, time
sys.path.append('%s/../../../libs/internals' % os.getcwd())
# from profileformattersbroker import ProfileFormattersBroker, CORE_MODULES
import profileformattersbroker
from raspiot.libs.tests.lib import TestLib
from raspiot.libs.internals.formatter import Formatter
from raspiot.libs.internals.rendererprofile import RendererProfile
from raspiot.utils import MissingParameter, InvalidParameter
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

DUMMY_PROFILE = u'''from raspiot.libs.internals.rendererprofile import RendererProfile
class DummyProfile(RendererProfile):
    pass
'''
FORMATTER_CONTENT = u'''from raspiot.libs.internals.profileformatter import ProfileFormatter
import sys; sys.path.append('../')
from dummyprofile import DummyProfile
class %(formatter_class)s(ProfileFormatter):
    def __init__(self, events_broker):
        ProfileFormatter.__init__(self, events_broker, '%(event_name)s', DummyProfile())

    def _fill_profile(self, event_values, profile):
        return profile
'''
FORMATTER_CONTENT_INVALID_CLASSNAME = u'''from raspiot.libs.internals.profileformatter import ProfileFormatter
import sys; sys.path.append('../')
from dummyprofile import DummyProfile
class Dummy(ProfileFormatter):
    def __init__(self, events_broker):
        ProfileFormatter.__init__(self, events_broker, '%(event_name)s', DummyProfile())

    def _fill_profile(self, event_values, profile):
        return profile
'''
FORMATTER_CONTENT_SYNTAX_ERROR = u'''from raspiot.libs.internals.profileformatter import ProfileFormatter
import sys; sys.path.append('../')
from dummyprofile import DummyProfile
class Dummy(ProfileFormatter):
    def __init__(self, events_broker):
        ProfileFormatter.__init__(self, events_broker, '%(event_name)s', DummyProfile())

    def _fill_profile(self, event_values, profile):
        return profile

    def invalid(self):
        # syntax error missing surrounding string quotes
        print(syntax error)
'''

class ProfileFormattersBrokerTests(unittest.TestCase):

    MODULES_DIR = 'test_modules'
    EVENT_NAME1 = 'event1'
    EVENT_NAME2 = 'event2'

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.crash_report = Mock()
        self.bus = Mock()
        self.formatters_broker = Mock()
        self.events_broker = Mock()

        CORE_MODULES = []
        self.p = profileformattersbroker.ProfileFormattersBroker(debug_enabled=False)
        self.bootstrap = {
            'message_bus': self.bus,
            'formatters_broker': self.formatters_broker,
            'events_broker': self.events_broker,
            'crash_report': self.crash_report,
        }

    def tearDown(self):
        if os.path.exists(self.MODULES_DIR):
            shutil.rmtree(self.MODULES_DIR)

        # unload imported formatters
        if 'app1.app1Formatter' in sys.modules:
            del sys.modules['app1.app1Formatter']
        if 'app2.app2Formatter' in sys.modules:
            del sys.modules['app2.app2Formatter']
        if 'dummyprofile' in sys.modules:
            del sys.modules['dummyprofile']

    def _init_context(self, formatter_content=FORMATTER_CONTENT, add_apps=True, core_modules=None, event_name=None):
        # build fake apps tree
        os.mkdir(self.MODULES_DIR)
        if add_apps:
            with io.open(os.path.join(self.MODULES_DIR, 'dummyprofile.py'), 'w') as fd:
                fd.write(DUMMY_PROFILE)
            for app_name in ['app1', 'app2']:
                app_dir = os.path.join(self.MODULES_DIR, app_name)
                formatter_class = '%sFormatter' % app_name
                os.mkdir(app_dir)
                with io.open(os.path.join(app_dir, '__init__.py'), 'w') as fd:
                    fd.write(u'')
                with io.open(os.path.join(app_dir, '%s.py' % app_name), 'w') as fd:
                    fd.write(u'')
                with io.open(os.path.join(app_dir, '%s.py' % formatter_class), 'w') as fd:
                    fd.write(formatter_content % {
                        'formatter_class': formatter_class,
                        'event_name': 'test.event.%s' % app_name if event_name is None else event_name
                    })
        # inject fake apps root dir to import path
        sys.path.append(os.path.join(os.getcwd(), self.MODULES_DIR))

        # overwrite module paths
        self.p.MODULES_DIR = '../../tests/libs/internals/%s' % self.MODULES_DIR
        self.p.PYTHON_RASPIOT_IMPORT_PATH = ''

    def test_configure_with_formatters(self):
        self._init_context()
        self.p.configure(self.bootstrap)
        formatters = self.p._get_loaded_formatters()
        logging.debug('Loaded formatters=%s' % formatters)
        self.assertEqual(len(formatters.keys()), 2)
        self.assertTrue('test.event.app1' in formatters.keys())
        self.assertTrue('test.event.app2' in formatters.keys())

    def test_configure_without_formatters(self):
        self._init_context(add_apps=False)
        self.p.configure(self.bootstrap)
        formatters = self.p._get_loaded_formatters()
        self.assertEqual(len(formatters.keys()), 0)

    def test_enable_debug(self):
        e = profileformattersbroker.ProfileFormattersBroker(debug_enabled=True)
        self.assertEqual(e.logger.getEffectiveLevel(), logging.DEBUG)
        # restore original log level
        e.logger.setLevel(logging.getLogger().getEffectiveLevel())

    def test_invalid_modules_path(self):
        self.p.MODULES_DIR = 'dummy'
        self.p.PYTHON_RASPIOT_IMPORT_PATH = ''

        with self.assertRaises(Exception) as cm:
            self.p.configure(self.bootstrap)
        self.assertTrue(cm.exception.message.startswith('Invalid modules path'))

    def test_load_events_invalid_classname(self):
        self._init_context(formatter_content=FORMATTER_CONTENT_INVALID_CLASSNAME)
        self.p.configure(self.bootstrap)

        self.assertEqual(len(self.p._get_loaded_formatters()), 0)
    
    def test_load_events_invalid_syntax(self):
        self._init_context(formatter_content=FORMATTER_CONTENT_SYNTAX_ERROR)
        self.p.configure(self.bootstrap)

        self.assertEqual(len(self.p._get_loaded_formatters()), 0)

    def test_register_renderer(self):
        self._init_context(event_name='test.event.app1')
        self.p.configure(self.bootstrap)

        self.p.register_renderer('app1', [DummyProfile])
        formatters = self.p.get_renderers_formatters('test.event.app1')
        logging.debug('Formatters: %s' % formatters)
        self.assertEqual(len(formatters), 1)
        self.assertEqual(formatters.keys()[0], 'DummyProfile')
        self.assertEqual(len(formatters[formatters.keys()[0]].keys()), 1)
        self.assertEqual(formatters[formatters.keys()[0]].keys()[0], 'app1')

        self.p.register_renderer('app2', [DummyProfile])
        formatters = self.p.get_renderers_formatters('test.event.app1')
        logging.debug('Formatters: %s' % formatters)
        self.assertEqual(len(formatters), 1)
        self.assertEqual(formatters.keys()[0], 'DummyProfile')
        self.assertEqual(len(formatters[formatters.keys()[0]].keys()), 2)
        self.assertTrue('app1' in formatters[formatters.keys()[0]].keys())
        self.assertTrue('app2' in formatters[formatters.keys()[0]].keys())

    def test_register_renderer_other(self):
        self._init_context()
        self.p.configure(self.bootstrap)

        self.p.register_renderer('app1', [DummyProfile])
        self.p.register_renderer('app2', [DummyProfile])

        formatters = self.p.get_renderers_formatters('test.event.app1')
        logging.debug('Formatters: %s' % formatters)
        self.assertEqual(len(formatters), 1)
        self.assertEqual(formatters[formatters.keys()[0]].keys()[0], 'app1')

        formatters = self.p.get_renderers_formatters('test.event.app2')
        logging.debug('Formatters: %s' % formatters)
        self.assertEqual(len(formatters), 1)
        self.assertEqual(formatters[formatters.keys()[0]].keys()[0], 'app2')

    def test_register_renderer_unknown_event(self):
        self._init_context()
        self.p.configure(self.bootstrap)

        self.p.register_renderer('app1', [DummyProfile])
        formatters = self.p.get_renderers_formatters('test.event.dummy')
        logging.debug('Formatters: %s' % formatters)
        self.assertIsNone(formatters)

    def test_register_renderer_invalid_parameters(self):
        self._init_context()
        self.p.configure(self.bootstrap)

        with self.assertRaises(MissingParameter) as cm:
            self.p.register_renderer('dummymodule', None)
        self.assertEqual(cm.exception.message, 'Parameter "profiles" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.p.register_renderer('dummymodule', {})
        self.assertEqual(cm.exception.message, 'Parameter "profiles" must be a list')

        with self.assertRaises(InvalidParameter) as cm:
            self.p.register_renderer('dummymodule', [])
        self.assertEqual(cm.exception.message, 'Parameter "profiles" must contains at least one profile')

    def test_register_renderer_already_registered(self):
        self._init_context()
        self.p.configure(self.bootstrap)

        self.p.register_renderer('app1', [DummyProfile])
        formatters = self.p.get_renderers_formatters('test.event.app1')
        logging.debug('Formatters: %s' % formatters)
        self.assertEqual(len(formatters), 1)

        self.p.register_renderer('app1', [DummyProfile])
        formatters = self.p.get_renderers_formatters('test.event.app1')
        logging.debug('Formatters: %s' % formatters)
        self.assertEqual(len(formatters), 1)

    def test_register_renderer_best_in_core(self):
        previous_core_modules = profileformattersbroker.CORE_MODULES
        try:
            profileformattersbroker.CORE_MODULES = ['app1']
            self._init_context()
            self.p.configure(self.bootstrap)
            self.p.register_renderer('app2', [DummyProfile])
        finally:
            profileformattersbroker.CORE_MODULES = previous_core_modules

    def test_get_renderers_profiles(self):
        self._init_context()
        self.p.configure(self.bootstrap)
        self.p.register_renderer('app1', [DummyProfile])

        profiles = self.p.get_renderers_profiles()
        logging.debug('Renderers profiles: %s' % profiles)
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles.keys()[0], 'app1')
        self.assertEqual(profiles.values()[0][0], 'DummyProfile')

    def test_get_renderers(self):
        self._init_context()
        self.p.configure(self.bootstrap)
        self.p.register_renderer('app1', [DummyProfile])
        self.p.register_renderer('app2', [DummyProfile])

        renderers = self.p.get_renderers()
        logging.debug('Renderers: %s' % renderers)
        self.assertEqual(len(renderers), 2)
        self.assertTrue('app1' in renderers)
        self.assertTrue('app2' in renderers)



if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_profileformattersbroker.py; coverage report -m
    unittest.main()

