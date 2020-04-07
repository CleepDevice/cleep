#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('/root/cleep/raspiot/libs/drivers')
from driver import Driver
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.exception import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from raspiot.libs.internals.task import Task
from mock import Mock
import time


class DriverTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.fs = CleepFilesystem()
        self.fs.enable_write = Mock()
        self.fs.disable_write = Mock()
        #Task.start = Mock()

        self.d = Driver(self.fs, 'dummy', 'dummyname')
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
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_driver.py; coverage report -m
    unittest.main()
