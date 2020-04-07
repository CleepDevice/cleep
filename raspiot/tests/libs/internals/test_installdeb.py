#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('%s/../../../libs/internals' % os.getcwd())
from installdeb import InstallDeb
from raspiot.libs.tests.lib import TestLib
from raspiot.exception import MissingParameter, InvalidParameter
import unittest
import logging
import time
from mock import Mock, patch
import subprocess
import tempfile
from threading import Timer


class InstallDebTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.data_path = os.path.abspath('../../data')
        self.archive_name = 'wiringpi'
        self.archive_path = os.path.join(self.data_path, '%s.deb' % self.archive_name)
        self.fs = Mock()
        self.crash_report = Mock()
        self.crash_report.manual_report = Mock()
        self.restore_watchdog_timeout = InstallDeb.WATCHDOG_TIMEOUT

        self.stdout_mock = tempfile.NamedTemporaryFile(delete=False)
        self.stderr_mock = tempfile.NamedTemporaryFile(delete=False)

    def tearDown(self):
        if os.path.exists('/usr/bin/gpio'):
            logging.info('Uninstalling "%s"...' % self.archive_name)
            os.system('/usr/bin/yes 2>/dev/null | apt-get purge %s > /dev/null 2>&1' % self.archive_name)
        self.stdout_mock.close()
        os.remove(self.stdout_mock.name)
        self.stderr_mock.close()
        os.remove(self.stderr_mock.name)
        InstallDeb.WATCHDOG_TIMEOUT = self.restore_watchdog_timeout

    def callback(self, status):
        logging.debug('Callback status=%s' % status)

    @patch('subprocess.Popen')
    def test_install_blocking(self, popen_mock):
        popen_mock.return_value.pid = 12345
        popen_mock.return_value.returncode = None
        popen_mock.return_value.stdout = self.stdout_mock
        popen_mock.return_value.stderr = self.stderr_mock
        def stop():
            popen_mock.return_value.returncode = 0
        timer = Timer(1.0, stop)
        timer.start()

        i = InstallDeb(self.fs, self.crash_report)
        res = i.install(self.archive_path, blocking=True)
        self.assertTrue(res)

        status = i.get_status()
        self.assertTrue('status' in status)
        self.assertTrue('returncode' in status)
        self.assertTrue('stdout' in status)
        self.assertEqual(status['status'], i.STATUS_DONE)
        self.assertEqual(status['returncode'], 0)
        self.assertEqual(len(status['stdout']), 0)

    @patch('subprocess.Popen')
    def test_install_blocking_failed(self, popen_mock):
        popen_mock.return_value.pid = 12345
        popen_mock.return_value.returncode = None
        popen_mock.return_value.stdout = self.stdout_mock
        popen_mock.return_value.stderr = self.stderr_mock
        def stop():
            popen_mock.return_value.returncode = 1
        timer = Timer(1.0, stop)
        timer.start()

        i = InstallDeb(self.fs, self.crash_report)
        res = i.install(self.archive_path, blocking=True)
        self.assertFalse(res)

        status = i.get_status()
        self.assertEqual(status['status'], i.STATUS_ERROR)
        self.assertEqual(status['returncode'], 1)
        self.assertEqual(len(status['stdout']), 0)

    @patch('subprocess.Popen')
    def test_install_blocking_timeout(self, popen_mock):
        popen_mock.return_value.pid = 12345
        popen_mock.return_value.returncode = None
        popen_mock.return_value.stdout = self.stdout_mock
        popen_mock.return_value.stderr = self.stderr_mock

        InstallDeb.WATCHDOG_TIMEOUT = 1
        i = InstallDeb(self.fs, self.crash_report)
        res = i.install(self.archive_path, blocking=True)
        self.assertFalse(res)
        self.assertTrue(self.crash_report.manual_report.called)

        status = i.get_status()
        self.assertEqual(status['status'], i.STATUS_TIMEOUT)
        self.assertIsNone(status['returncode'])

    @patch('subprocess.Popen')
    def test_install_blocking_callback(self, popen_mock):
        popen_mock.return_value.pid = 12345
        popen_mock.return_value.returncode = None
        self.stdout_mock.write('stdout')
        self.stderr_mock.write('stderr')
        self.stdout_mock.seek(0)
        self.stderr_mock.seek(0)
        popen_mock.return_value.stdout = self.stdout_mock
        popen_mock.return_value.stderr = self.stderr_mock
        def stop():
            popen_mock.return_value.returncode = 0
        timer = Timer(1, stop)
        timer.start()

        i = InstallDeb(self.fs, self.crash_report)
        res = i.install(self.archive_path, blocking=True, status_callback=self.callback)
        logging.debug('Result: %s' % res)
        self.assertTrue(res)
        status = i.get_status()
        self.assertTrue('stdout' in status['stdout'])
        self.assertTrue('stderr' in status['stdout'])

    @patch('subprocess.Popen')
    def test_install_non_blocking(self, popen_mock):
        popen_mock.return_value.pid = 12345
        popen_mock.return_value.returncode = 0
        popen_mock.return_value.stdout = self.stdout_mock
        popen_mock.return_value.stderr = self.stderr_mock

        i = InstallDeb(self.fs, self.crash_report)
        res = i.install(self.archive_path, blocking=True, status_callback=self.callback)
        while True:
            status = i.get_status()
            if status['status']!=i.STATUS_RUNNING:
                break
            time.sleep(0.25)

        self.assertEqual(status['status'], i.STATUS_DONE)

    @patch('subprocess.Popen')
    def test_install_non_blocking_stop(self, popen_mock):
        popen_mock.return_value.pid = 12345
        popen_mock.return_value.returncode = None
        popen_mock.return_value.stdout = self.stdout_mock
        popen_mock.return_value.stderr = self.stderr_mock

        i = InstallDeb(self.fs, self.crash_report)
        res = i.install(self.archive_path, blocking=False, status_callback=self.callback)
        self.assertIsNone(res)
        time.sleep(1)
        i.stop()
        status = i.get_status()
        self.assertEqual(status['status'], i.STATUS_KILLED)
        self.assertTrue(i._console.killed)

    @patch('subprocess.Popen')
    def test_install_non_blocking_is_terminated(self, popen_mock):
        popen_mock.return_value.pid = 12345
        popen_mock.return_value.returncode = None
        popen_mock.return_value.stdout = self.stdout_mock
        popen_mock.return_value.stderr = self.stderr_mock
        def stop():
            popen_mock.return_value.returncode = 0
        timer = Timer(1.0, stop)
        timer.start()

        i = InstallDeb(self.fs, self.crash_report)
        res = i.install(self.archive_path, blocking=False, status_callback=self.callback)
        time.sleep(0.25)
        self.assertFalse(i.is_terminated())
        time.sleep(0.25)
        self.assertFalse(i.is_terminated())
        time.sleep(1.5)
        self.assertTrue(i.is_terminated())

    def test_install_invalid_parameters(self):
        i = InstallDeb(self.fs, self.crash_report)

        with self.assertRaises(MissingParameter) as cm:
            i.install(None, blocking=False, status_callback=self.callback)
        self.assertEqual(cm.exception.message, 'Parameter "deb" is missing')
        with self.assertRaises(MissingParameter) as cm:
            i.install('', blocking=False, status_callback=self.callback)
        self.assertEqual(cm.exception.message, 'Parameter "deb" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            i.install('dummy', blocking=False, status_callback=self.callback)
        self.assertEqual(cm.exception.message, 'Deb archive "dummy" does not exist')

        with self.assertRaises(MissingParameter) as cm:
            i.install('dummy', blocking=False)
        self.assertEqual(cm.exception.message, 'Parameter "status_callback" is mandatary if blocking mode enabled')

    @patch('subprocess.Popen')
    def test_dry_run(self, popen_mock):
        popen_mock.return_value.pid = 12345
        popen_mock.return_value.returncode = None
        popen_mock.return_value.stdout = self.stdout_mock
        popen_mock.return_value.stderr = self.stderr_mock
        def stop():
            popen_mock.return_value.returncode = 0
        timer = Timer(1.0, stop)
        timer.start()

        i = InstallDeb(self.fs, self.crash_report)
        res = i.dry_run(self.archive_path, status_callback=self.callback)
        self.assertTrue(res)

        status = i.get_status()
        self.assertTrue('status' in status)
        self.assertTrue('returncode' in status)
        self.assertTrue('stdout' in status)
        self.assertEqual(status['status'], i.STATUS_DONE)
        self.assertEqual(status['returncode'], 0)
        self.assertEqual(len(status['stdout']), 0)

    @patch('subprocess.Popen')
    def test_dry_run_callback(self, popen_mock):
        popen_mock.return_value.pid = 12345
        popen_mock.return_value.returncode = None
        self.stdout_mock.write('stdout')
        self.stderr_mock.write('stderr')
        self.stdout_mock.seek(0)
        self.stderr_mock.seek(0)
        popen_mock.return_value.stdout = self.stdout_mock
        popen_mock.return_value.stderr = self.stderr_mock
        def stop():
            popen_mock.return_value.returncode = 0
        timer = Timer(1, stop)
        timer.start()

        i = InstallDeb(self.fs, self.crash_report)
        res = i.dry_run(self.archive_path, status_callback=self.callback)
        logging.debug('Result: %s' % res)
        self.assertTrue(res)
        status = i.get_status()
        self.assertTrue('stdout' in status['stdout'])
        self.assertTrue('stderr' in status['stdout'])

    @patch('subprocess.Popen')
    def test_dry_run_timeout(self, popen_mock):
        popen_mock.return_value.pid = 12345
        popen_mock.return_value.returncode = None
        popen_mock.return_value.stdout = self.stdout_mock
        popen_mock.return_value.stderr = self.stderr_mock

        InstallDeb.WATCHDOG_TIMEOUT = 1
        i = InstallDeb(self.fs, self.crash_report)
        res = i.dry_run(self.archive_path, status_callback=self.callback)
        self.assertFalse(res)
        self.assertTrue(self.crash_report.manual_report.called)

        status = i.get_status()
        self.assertEqual(status['status'], i.STATUS_TIMEOUT)
        self.assertIsNone(status['returncode'])

class InstallDebFunctionalTests(unittest.TestCase):

    def setUp(self):
        t = TestLib(self)
        t.declare_functional_test()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.data_path = os.path.abspath('../../data')
        self.archive_name = 'wiringpi'
        self.archive_path = os.path.join(self.data_path, '%s.deb' % self.archive_name)
        self.fs = Mock()
        self.crash_report = Mock()
        self.crash_report.manual_report = Mock()

    def tearDown(self):
        if os.path.exists('/usr/bin/gpio'):
            logging.info('Uninstalling "%s"...' % self.archive_name)
            os.system('/usr/bin/yes 2>/dev/null | apt-get purge %s > /dev/null 2>&1' % self.archive_name)

    def callback(self, status):
        logging.debug('Callback status=%s' % status)

    def test_install_blocking(self):
        i = InstallDeb(self.fs, self.crash_report)
        res = i.install(self.archive_path, blocking=True, status_callback=self.callback)
        self.assertTrue(res)

        # check deb is installed
        self.assertTrue(os.path.exists('/usr/bin/gpio'))

        # make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_non_blocking(self):
        i = InstallDeb(self.fs, self.crash_report)
        res = i.install(self.archive_path, blocking=False, status_callback=self.callback)
        self.assertIsNone(res)

        # wait end of install
        while not i.is_terminated():
            time.sleep(0.25)

        # check deb is installed
        self.assertTrue(os.path.exists('/usr/bin/gpio'))

        # make sure cleepfilesystem free everything
        time.sleep(1.0)

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_installdeb.py; coverage report -m
    unittest.main()

