#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.tests.lib import TestLib
import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from driver import Driver
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.exception import MissingParameter, InvalidParameter, CommandError
import unittest
import logging
from cleep.libs.internals.task import Task
from unittest.mock import Mock
import time
from cleep.libs.tests.common import get_log_level
from cleep.libs.internals.taskfactory import TaskFactory
from threading import Event

LOG_LEVEL = get_log_level()


class DriverTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.fs = CleepFilesystem()
        self.fs.enable_write = Mock()
        self.fs.disable_write = Mock()
        self.task_factory = TaskFactory({ "app_stop_event": Event() })

        self.d = Driver('dummy', 'dummyname')
        self.d.configure({
            'cleep_filesystem': self.fs,
            'task_factory': self.task_factory,
        })
        self.end_called = False
        self.end_result = None

    def tearDown(self):
        self.end_called = False

    def _end_callback(self, driver_type, driver_name, success, message):
        logging.debug('End callback triggered')
        self.end_result = {
            'driver_type': driver_type,
            'driver_name': driver_name,
            'success': success,
            'message': message,
        }
        self.end_called = True

    def test_processing_is_installing(self):
        def custom_callback(params):
            time.sleep(.5)
        self.d._install = custom_callback
        t = self.d.install(self._end_callback)
        self.assertEqual(self.d.processing(), self.d.PROCESSING_INSTALLING)
        t.wait()
        self.assertEqual(self.d.processing(), self.d.PROCESSING_NONE)

    def test_processing_is_uninstalling(self):
        def custom_callback(params):
            time.sleep(.5)
        self.d._uninstall = custom_callback
        t = self.d.uninstall(self._end_callback)
        self.assertEqual(self.d.processing(), self.d.PROCESSING_UNINSTALLING)
        t.wait()
        self.assertEqual(self.d.processing(), self.d.PROCESSING_NONE)

    def test_install(self):
        def custom_callback(params):
            pass
        self.d._install = custom_callback
        t = self.d.install(self._end_callback)
        t.wait()
        self.assertTrue(self.end_called)
        self.assertTrue(self.end_result['success'])

    def test_install_failed(self):
        def custom_callback(params):
            raise Exception('test exception')
        self.d._install = custom_callback
        t = self.d.install(self._end_callback)
        t.wait()
        self.assertTrue(self.end_called)
        self.assertFalse(self.end_result['success'])
        self.assertEqual(self.end_result['message'], 'test exception')

    def test_install_already_running(self):
        def custom_callback(params):
            time.sleep(0.5)
        self.d._install = custom_callback
        t = self.d.install(self._end_callback)
        with self.assertRaises(CommandError) as cm:
            self.assertIsNone(self.d.install(self._end_callback))
        self.assertEqual(cm.exception.message, 'Driver is already installing')
        t.wait()

    def test_uninstall(self):
        def custom_callback(params):
            pass
        self.d._uninstall = custom_callback
        t = self.d.uninstall(self._end_callback)
        t.wait()
        self.assertTrue(self.end_called)
        self.assertTrue(self.end_result['success'])

    def test_uninstall_failed(self):
        def custom_callback(params):
            raise Exception('test exception')
        self.d._uninstall = custom_callback
        t = self.d.uninstall(self._end_callback)
        t.wait()
        self.assertTrue(self.end_called)
        self.assertFalse(self.end_result['success'])
        self.assertEqual(self.end_result['message'], 'test exception')

    def test_uninstall_already_running(self):
        def custom_callback(params):
            time.sleep(0.5)
        self.d._uninstall = custom_callback
        t = self.d.uninstall(self._end_callback)
        with self.assertRaises(CommandError) as cm:
            self.assertIsNone(self.d.uninstall(self._end_callback))
        self.assertEqual(cm.exception.message, 'Driver is already uninstalling')
        t.wait()

    def test_make_sure_filesystem_is_writable_during_install(self):
        def custom_callback(params):
            pass
        self.d._install = custom_callback
        t = self.d.install(self._end_callback)
        t.wait()
        self.assertTrue(self.fs.enable_write.called)
        self.assertTrue(self.fs.disable_write.called)

    def test_make_sure_filesystem_is_writable_during_install_with_exception(self):
        def custom_callback(params):
            raise Exception()
        self.d._install = custom_callback
        t = self.d.install(self._end_callback)
        t.wait()
        self.assertTrue(self.fs.enable_write.called)
        self.assertTrue(self.fs.disable_write.called)

    def test_make_sure_filesystem_is_writable_during_uninstall(self):
        def custom_callback(params):
            pass
        self.d._uninstall = custom_callback
        t = self.d.uninstall(self._end_callback)
        t.wait()
        self.assertTrue(self.fs.enable_write.called)
        self.assertTrue(self.fs.disable_write.called)

    def test_make_sure_filesystem_is_writable_during_uninstall_with_exception(self):
        def custom_callback(params):
            raise Exception()
        self.d._uninstall = custom_callback
        t = self.d.uninstall(self._end_callback)
        t.wait()
        self.assertTrue(self.fs.enable_write.called)
        self.assertTrue(self.fs.disable_write.called)


if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_driver.py; coverage report -m -i
    unittest.main()

