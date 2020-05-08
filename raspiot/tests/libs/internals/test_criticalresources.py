#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from raspiot.libs.internals.task import Task
from criticalresources import CriticalResources
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
import time
from unittest.mock import Mock
import io
import shutil

class CriticalResourcesTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        enable_log = True if logging.getLogger().getEffectiveLevel()==logging.DEBUG else False

        self.c = CriticalResources(enable_log)
        self.acquired_cb_count = 0
        self.need_release_cb_count = 0
        self.acquired_cb_last_resource = None
        self.need_release_cb_last_resource = None

    def tearDown(self):
        self.acquired_cb_count = 0
        self.need_release_cb_count = 0

    def _acquired_cb(self, resource_name):
        self.acquired_cb_count += 1
        self.acquired_cb_last_resource = resource_name

    def _need_release_cb(self, resource_name):
        self.need_release_cb_count += 1
        self.need_release_cb_last_resource = resource_name

    def test_register_resource_ok(self):
        self.c.register_resource('test', 'audio.playback', self._acquired_cb, self._need_release_cb)
        self.assertIsNone(self.c.resources['audio.playback']['permanent'], 'Permanent value should be None')
        self.c.register_resource('test', 'audio.capture', self._acquired_cb, self._need_release_cb)
        self.assertIsNone(self.c.resources['audio.capture']['permanent'], 'Permanent value should be None')

        self.c.register_resource('test', 'audio.capture', self._acquired_cb, self._need_release_cb, True)
        self.assertIsNotNone(self.c.resources['audio.capture']['permanent'], 'Permanent value should not be None')

    def test_register_unkown_resource(self):
        with self.assertRaises(Exception) as cm:
            self.c.register_resource('test', 'a.resource', self._acquired_cb, self._need_release_cb)
        self.assertEqual(str(cm.exception), 'Resource "a.resource" does not exists', 'Should raise exception while registering unkown resource')

    def test_register_with_invalid_params(self):
        with self.assertRaises(Exception) as cm:
            self.c.register_resource('test', 'audio.playback', None, self._need_release_cb)
        self.assertEqual(str(cm.exception), 'Callbacks must be functions', 'Should raise exception while registering with invalid acquire_callback param')
        with self.assertRaises(Exception) as cm:
            self.c.register_resource('test', 'audio.playback', self._acquired_cb, None)
        self.assertEqual(str(cm.exception), 'Callbacks must be functions', 'Should raise exception while registering with invalid acquire_callback param')
        with self.assertRaises(Exception) as cm:
            self.c.register_resource('test', 'audio.playback', 'test', self._need_release_cb)
        self.assertEqual(str(cm.exception), 'Callbacks must be functions', 'Should raise exception while registering with invalid acquire_callback param')
        with self.assertRaises(Exception) as cm:
            self.c.register_resource('test', 'audio.playback', self._acquired_cb, 'test')
        self.assertEqual(str(cm.exception), 'Callbacks must be functions', 'Should raise exception while registering with invalid acquire_callback param')

    def test_resource_permanently_acquired_ok(self):
        self.c.register_resource('test', 'audio.playback', self._acquired_cb, self._need_release_cb, False)
        self.assertFalse(self.c.is_resource_permanently_acquired('audio.playback'), 'Resource should not be permanently acquired')

        self.c.register_resource('test', 'audio.capture', self._acquired_cb, self._need_release_cb, True)
        self.assertTrue(self.c.is_resource_permanently_acquired('audio.capture'), 'Resource should be permanently acquired')

    def test_resource_permanently_acquired_ko(self):
        self.c.register_resource('test', 'audio.playback', self._acquired_cb, self._need_release_cb, True)
        with self.assertRaises(Exception) as cm:
            self.c.is_resource_permanently_acquired('a.resource')
        self.assertEqual(str(cm.exception), 'Resource "a.resource" does not exists', 'Should raise exception while registering unkown resource')

    def test_resource_cannot_be_acquired_permanently_by_two_modules(self):
        self.c.register_resource('test1', 'audio.capture', self._acquired_cb, self._need_release_cb, True)
        with self.assertRaises(Exception) as cm:
            self.c.register_resource('test2', 'audio.capture', self._acquired_cb, self._need_release_cb, True)
        self.assertEqual(str(cm.exception), 'Resource "audio.capture" already has permanent module "test1" configured. Only one allowed', 'Should raise exception when 2 modules try to permanently acquire a resource')

    def test_acquire_resource(self):
        self.c.register_resource('test', 'audio.playback', self._acquired_cb, self._need_release_cb, False)

        self.c.acquire_resource('test', 'audio.playback')
        self.assertEqual(self.c.resources['audio.playback']['using'], 'test', 'Resource should be acquired')
        self.assertEqual(len(self.c.resources['audio.playback']['waiting']), 0, 'No module should wait for resource')
        self.assertIsNone(self.c.resources['audio.playback']['permanent'], 'Resource should not have permanent acquirer')
        self.assertIsNone(self.c.resources['audio.capture']['using'], 'Resource should not be acquired')

    def test_acquire_resource_already_acquired(self):
        self.c.register_resource('test1', 'audio.playback', self._acquired_cb, self._need_release_cb)
        self.c.register_resource('test2', 'audio.playback', self._acquired_cb, self._need_release_cb)

        t = self.c.acquire_resource('test1', 'audio.playback')
        t = self.c.acquire_resource('test2', 'audio.playback')
        t.wait()
        self.assertEqual(self.c.resources['audio.playback']['using'], 'test1', 'Module test1 should using resource')
        self.assertEqual(len(self.c.resources['audio.playback']['waiting']), 1, 'Resource should have 1 waiting module')
        self.assertEqual(self.need_release_cb_count, 1, 'need_release callback should be called once')
        self.assertEqual(self.acquired_cb_count, 1, 'acquired_release callback should be called once')
        
        t = self.c.release_resource('test1', 'audio.playback')
        t.wait()
        self.assertEqual(self.acquired_cb_count, 2, 'acquired_release callback should be called once')
        self.assertEqual(self.c.resources['audio.playback']['using'], 'test2', 'Module test2 should use the resource')
        self.assertEqual(len(self.c.resources['audio.playback']['waiting']), 0, 'Resource should have no waiting module')

    def test_acquire_module_with_permanent(self): # FAILED
        self.c.register_resource('test1', 'audio.playback', self._acquired_cb, self._need_release_cb, True)
        self.c.register_resource('test2', 'audio.playback', self._acquired_cb, self._need_release_cb)

        self.c.acquire_resource('test1', 'audio.playback')
        self.c.acquire_resource('test2', 'audio.playback')
        #test2 should acquire resource
        t = self.c.release_resource('test1', 'audio.playback')
        t.wait()
        self.assertEqual(self.c.resources['audio.playback']['using'], 'test2', 'Module test2 should use the resource')
        #test1 should acquire again resource
        self.assertTrue(self.c.release_resource('test2', 'audio.playback'), 'Resource release should succeed')
        self.assertEqual(self.c.resources['audio.playback']['using'], 'test1', 'Module test1 should uses the resource')
        self.assertEqual(len(self.c.resources['audio.playback']['waiting']), 0, 'Resource should have no waiting module')

    def test_acquire_resource_ko(self):
        self.c.register_resource('test', 'audio.playback', self._acquired_cb, self._need_release_cb, True)
        with self.assertRaises(Exception) as cm:
            self.c.acquire_resource('test', 'a.resource')
        self.assertEqual(str(cm.exception), 'Resource "a.resource" does not exists', 'Should raise exception while acquiring unknown resource')

    def test_acquire_unregistered_resource(self):
        with self.assertRaises(Exception) as cm:
            self.c.acquire_resource('test', 'audio.capture')
        self.assertEqual(str(cm.exception), 'Module "test" try to acquire resource "audio.capture" which it is not registered on', 'Should raise exception while acquiring unregistered resource')

    def test_release_resource_unacquired_resource(self):
        self.c.register_resource('test1', 'audio.playback', self._acquired_cb, self._need_release_cb)
        self.assertFalse(self.c.release_resource('test1', 'audio.playback'), 'Resource release should failed')

    def test_release_resource_unreferenced_resource(self):
        self.c.register_resource('test1', 'audio.playback', self._acquired_cb, self._need_release_cb)
        with self.assertRaises(Exception) as cm:
            self.c.release_resource('test1', 'audio.dummy')
        self.assertEqual(str(cm.exception), 'Resource "audio.dummy" does not exists')

    def test_release_resource_not_using_it(self):
        self.c.register_resource('test1', 'audio.playback', self._acquired_cb, self._need_release_cb)
        self.c.register_resource('test2', 'audio.playback', self._acquired_cb, self._need_release_cb)
        self.c.acquire_resource('test1', 'audio.playback')
        self.assertFalse(self.c.release_resource('test2', 'audio.playback'))

    def test_release_resource_exception_occured(self):
        self.c.register_resource('test1', 'audio.playback', self._acquired_cb, self._need_release_cb)
        self.c.register_resource('test2', 'audio.playback', self._acquired_cb, self._need_release_cb)
        self.c.acquire_resource('test1', 'audio.playback')
        self.c.acquire_resource('test2', 'audio.playback')
        task_start_restore = Task.start
        try:
            Task.start = Mock(side_effect=Exception)
            self.assertFalse(self.c.release_resource('test1', 'audio.playback'))
        finally:
            Task.start = task_start_restore

    def test_get_resources(self):
        resources = self.c.get_resources()
        self.assertGreater(len(resources), 0)
        self.assertEqual(len([resource for resource in resources if resource=='audio.playback']), 1, 'Resources should contain audio.playback')
        self.assertEqual(len([resource for resource in resources if resource=='audio.capture']), 1, 'Resources should contain audio.capture')

    def test_crash_report(self):
        task_start_restore = Task.start
        try:
            Task.start = Mock(side_effect=Exception)
            crash_report = Mock()
            crash_report.report_exception = Mock()
            self.c.set_crash_report(crash_report)

            self.c.register_resource('test1', 'audio.playback', self._acquired_cb, self._need_release_cb)
            self.c.acquire_resource('test1', 'audio.playback')
            self.assertTrue(crash_report.report_exception.called)
        finally:
            Task.start = task_start_restore


class CriticalResourcesTestsInvalidResourcePath(unittest.TestCase):

    CONTENT = u"""#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Mydummyresource():
    RESOURCE_NAME = u'dummy.res'"""

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.resources_dir = '/tmp/resources'

    def test_load_resources_invalid_path(self):
        c = CriticalResources
        c.RESOURCES_DIR = self.resources_dir
        c.PYTHON_RASPIOT_IMPORT_PATH = ''
        with self.assertRaises(Exception) as cm:
            c(False)
        self.assertEqual(str(cm.exception), 'Invalid resources path "%s"' % c.RESOURCES_DIR)

    def test_load_resources_invalid_resource_path(self):
        try:
            os.mkdir(self.resources_dir)
            dummy_file = os.path.join(self.resources_dir, 'dummyResource.py')
            with io.open(dummy_file, 'w') as fp:
                fp.write(self.CONTENT)

            time.sleep(1.0)
            c = CriticalResources
            c.RESOURCES_DIR = self.resources_dir
            c.PYTHON_RASPIOT_IMPORT_PATH = 'resources'
            with self.assertRaises(Exception) as cm:
                c(False)
            self.assertEqual(str(cm.exception), 'Error occured trying to load resource "dummyResource"')
        finally:
            if os.path.exists(self.resources_dir):
                shutil.rmtree(self.resources_dir)

    def test_load_resources_invalid_resource_class_name(self):
        try:
            os.mkdir(self.resources_dir)
            
            dummy_file = os.path.join(self.resources_dir, 'dummyResource.py')
            with io.open(dummy_file, 'w') as fp:
                fp.write(self.CONTENT)

            # make dummy dir content importable
            sys.path.append(self.resources_dir)

            c = CriticalResources
            c.RESOURCES_DIR = self.resources_dir
            c.PYTHON_RASPIOT_IMPORT_PATH = ''
            with self.assertRaises(Exception) as cm:
                c(False)
            self.assertEqual(str(cm.exception), 'Invalid resource "dummyResource" tryed to be loaded')
        finally:
            if os.path.exists(self.resources_dir):
                shutil.rmtree(self.resources_dir)


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","*test_*.py" --concurrency=thread test_criticalresources.py; coverage report -m -i
    unittest.main()
