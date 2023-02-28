#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
import crashreport
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import Mock
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class MockedScope():
    def __init__(self):
        self.set_tag_calls = 0
        self.set_extra_calls = 0
        self.called = False
        self.tags = {}
    def __call__(self, *args, **kwargs):
        self.called = True
    def set_tag(self, *args, **kwargs):
        self.set_tag_calls += 1
        self.tags[args[0]] = args[1]
    def set_extra(self, *args, **kwargs):
        self.set_extra_calls += 1

class CrashReportTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.sentry_configure_scope = Mock()
        self.sentry_configure_scope.return_value.__enter__ = Mock()
        self.configure_scope = MockedScope()
        self.sentry_configure_scope.return_value.__enter__.return_value = self.configure_scope
        self.sentry_configure_scope.return_value.__exit__ = Mock()
        #self.sentry_configure_scope.set_tag = Mock()
        crashreport.configure_scope = self.sentry_configure_scope

        self.sentry_push_scope = Mock()
        self.sentry_push_scope.return_value.__enter__ = Mock()
        self.push_scope = MockedScope()
        self.sentry_push_scope.return_value.__enter__.return_value = self.push_scope
        self.sentry_push_scope.return_value.__exit__ = Mock()
        crashreport.SentryPushScope = self.sentry_push_scope

        self.sentry_init_mock = Mock()
        crashreport.SentryInit = self.sentry_init_mock

        self.sentry_capture_message = Mock()
        crashreport.SentryCaptureMessage = self.sentry_capture_message

        self.sentry_capture_exception = Mock()
        crashreport.SentryCaptureException = self.sentry_capture_exception

        self.c = crashreport.CrashReport('mytoken', 'myproduct', 'myversion', {'mylib': 'mylibversion'})

    def tearDown(self):
        pass

    def test_init(self):
        #crash report is disabled by default
        self.assertFalse(self.c.is_enabled())
        #crash report must init sentry stuff
        self.assertTrue(self.sentry_init_mock.called)
        #crash report must set some custom tags at startup
        self.assertTrue(self.sentry_configure_scope.return_value.__enter__.called)
        self.assertGreaterEqual(self.sentry_configure_scope.return_value.__enter__.return_value.set_tag_calls, 7)

    def test_check_disabled_at_startup(self):
        c = crashreport.CrashReport(None, 'myproduct', 'myversion')
        self.assertFalse(c.is_enabled())
        c = crashreport.CrashReport('mytoken', 'myproduct', 'myversion', disabled_by_core=True)
        self.assertFalse(c.is_enabled())

    def test_debug_mode(self):
        c = crashreport.CrashReport('mytoken', 'myproduct', 'myversion', debug=True)
        self.assertEqual(c.logger.getEffectiveLevel(), logging.DEBUG)
        c = crashreport.CrashReport('mytoken', 'myproduct', 'myversion', debug=False)
        self.assertEqual(c.logger.getEffectiveLevel(), logging.WARN)

    def test_is_enabled(self):
        self.assertFalse(self.c.is_enabled())
        self.c.enable()
        self.assertTrue(self.c.is_enabled())
        self.c.disable()
        self.assertFalse(self.c.is_enabled())

    def test_report_exception(self):
        self.c.enable()
        try:
            1/0
        except:
            self.c.report_exception(extra={'key': 'value'})
        self.assertTrue(self.sentry_capture_exception.called)
        self.assertTrue(self.sentry_push_scope.called)
        self.assertGreater(self.sentry_push_scope.return_value.__enter__.return_value.set_extra_calls, 0)

    def test_manual_report(self):
        self.c.enable()
        self.c.manual_report('test message', extra={'key': 'value'})
        self.assertTrue(self.sentry_capture_message.called)
        self.assertTrue(self.sentry_push_scope.called)
        self.assertGreater(self.sentry_push_scope.return_value.__enter__.return_value.set_extra_calls, 0)

    def test_filter_exception(self):
        self.c.enable()
        self.c.filter_exception('MyException')
        self.assertTrue('MyException' in self.c._CrashReport__filters)

    def test_get_infos(self):
        self.c.enable()
        infos = self.c.get_infos()
        logging.debug('Infos: %s' % infos)
        self.assertDictEqual(infos, {
            'libsversion': {
                'mylib': 'mylibversion'
            },
            'product': 'myproduct',
            'productversion': 'myversion'
        })

    def test_add_module_version(self):
        self.c.enable()
        self.c.add_module_version('Mymodule', '1.1.1')
        logging.debug('Tags: %s' % self.configure_scope.tags)
        self.assertTrue('Mymodule' in self.configure_scope.tags)
        self.assertEqual(self.configure_scope.tags['Mymodule'], '1.1.1')

if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_crashreport.py; coverage report -m -i
    unittest.main()

