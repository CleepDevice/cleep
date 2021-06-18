#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from readwrite import ReadWrite, Console, ReadWriteContext
from cleep.libs.tests.lib import TestLib
from cleep.libs.tests.session import AnyArg
import unittest
import logging
from unittest.mock import Mock, patch

class ReadWriteTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.crash_report = Mock()

    def tearDown(self):
        pass

    def _get_console_command_return_value(self, error=False, killed=False, returncode=0, stdout=[], stderr=[]):
        return {
            'error': error,
            'killed': killed,
            'returncode': returncode,
            'stdout': stdout,
            'stderr': stderr,
        }

    def _init_context(self, console_mock, command_return_value=None, command_side_effect=None, on_cleep=True):
        if command_side_effect:
            console_mock.return_value.command = Mock(side_effect=command_side_effect)
        else:
            console_mock.return_value.command = Mock(return_value=command_return_value)
        self.r = ReadWrite()
        if not on_cleep:
            self.r.CLEEP_DIR = '/dummy'
        else:
            self.r.CLEEP_DIR = '/tmp' # set a file/dir that exists
        self.r.set_crash_report(self.crash_report)

    def test_crash_report(self):
        self.r = ReadWrite()
        self.r.set_crash_report(self.crash_report)
        self.assertEqual(self.crash_report, self.r.crash_report)

    def test_is_path_on_root(self):
        self.r = ReadWrite()
        self.assertTrue(self.r.is_path_on_root('/root/dummy'))
        self.assertTrue(self.r.is_path_on_root('/etc/network/interfaces'))
        self.assertTrue(self.r.is_path_on_root('/home/pi/dummy'))
        self.assertFalse(self.r.is_path_on_root('/boot/dummy'))

    @patch('readwrite.Console')
    def test_get_status_all_not_readonly(self, console_mock):
        console_return_value = self._get_console_command_return_value(stdout=['rw'])
        self._init_context(console_mock, console_return_value)
        status = self.r.get_status()
        logging.debug('Status=%s' % status)

        self.assertTrue('boot' in status)
        self.assertTrue('root' in status)
        self.assertEqual(status['root'], self.r.STATUS_WRITE)
        self.assertEqual(status['boot'], self.r.STATUS_WRITE)

    @patch('readwrite.Console')
    def test_get_status_all_readonly(self, console_mock):
        console_return_value = self._get_console_command_return_value(stdout=['ro'])
        self._init_context(console_mock, console_return_value)
        status = self.r.get_status()
        logging.debug('Status=%s' % status)

        self.assertEqual(status['root'], self.r.STATUS_READ)
        self.assertEqual(status['boot'], self.r.STATUS_READ)

    @patch('readwrite.Console')
    def test_get_status_all_unknown(self, console_mock):
        console_return_value = self._get_console_command_return_value(stdout=['dummy'])
        self._init_context(console_mock, console_return_value)
        status = self.r.get_status()
        logging.debug('Status=%s' % status)

        self.assertEqual(status['root'], self.r.STATUS_UNKNOWN)
        self.assertEqual(status['boot'], self.r.STATUS_UNKNOWN)

    @patch('readwrite.Console')
    def test_get_status_different(self, console_mock):
        command_side_effect = [
            self._get_console_command_return_value(stdout=['rw']),
            self._get_console_command_return_value(stdout=['ro']),
        ]
        self._init_context(console_mock, command_side_effect=command_side_effect)
        status = self.r.get_status()
        logging.debug('Status=%s' % status)

        self.assertEqual(status['root'], self.r.STATUS_READ)
        self.assertEqual(status['boot'], self.r.STATUS_WRITE)

    @patch('readwrite.Console')
    def test_enable_write_on_boot(self, console_mock):
        command_side_effect = [
            self._get_console_command_return_value(),
            self._get_console_command_return_value(stdout=['rw']),
        ]
        self._init_context(console_mock, command_side_effect=command_side_effect)

        self.assertTrue(self.r.enable_write_on_boot())

    @patch('readwrite.Console')
    def test_enable_write_on_boot_failed(self, console_mock):
        command_side_effect = [
            self._get_console_command_return_value(),
            self._get_console_command_return_value(stdout=['ro']),
        ]
        self._init_context(console_mock, command_side_effect=command_side_effect)

        self.assertFalse(self.r.enable_write_on_boot())

    @patch('readwrite.Console')
    def test_enable_write_on_boot_error(self, console_mock):
        command_side_effect = [
            self._get_console_command_return_value(error=True),
            self._get_console_command_return_value(),
        ]
        self._init_context(console_mock, command_side_effect=command_side_effect)

        self.assertFalse(self.r.enable_write_on_boot())

    @patch('readwrite.Console')
    def test_disable_write_on_boot(self, console_mock):
        command_side_effect = [
            self._get_console_command_return_value(),
            self._get_console_command_return_value(stdout=['ro']),
        ]
        self._init_context(console_mock, command_side_effect=command_side_effect)

        context = ReadWriteContext()
        self.assertTrue(self.r.disable_write_on_boot(context))

    @patch('readwrite.Console')
    def test_disable_write_on_boot_failed(self, console_mock):
        command_side_effect = [
            self._get_console_command_return_value(),
            self._get_console_command_return_value(stdout=['rw']),
        ]
        self._init_context(console_mock, command_side_effect=command_side_effect)

        context = ReadWriteContext()
        self.assertFalse(self.r.disable_write_on_boot(context))

    @patch('readwrite.Console')
    def test_disable_write_on_boot_error(self, console_mock):
        command_side_effect = [
            self._get_console_command_return_value(error=True),
            self._get_console_command_return_value(),
        ]
        self._init_context(console_mock, command_side_effect=command_side_effect)

        context = ReadWriteContext()
        self.assertFalse(self.r.disable_write_on_boot(context))

        self.crash_report.manual_report.assert_called_with(
            'Error when turning off writing mode',
            {
                'result': AnyArg(),
                'partition': '/boot',
                'traceback': AnyArg(),
                'context': AnyArg(),
                'files': [],
            }
        )

    @patch('readwrite.Console')
    def test_disable_write_no_crash_report(self, console_mock):
        command_side_effect = [
            self._get_console_command_return_value(error=True, stderr=['busy']),
            self._get_console_command_return_value(),
        ]
        self._init_context(console_mock, command_side_effect=command_side_effect)

        context = ReadWriteContext()
        self.assertFalse(self.r.disable_write_on_boot(context))

        self.assertFalse(self.crash_report.called)

    @patch('readwrite.Console')
    def test_enable_write_on_root(self, console_mock):
        command_side_effect = [
            self._get_console_command_return_value(),
            self._get_console_command_return_value(stdout=['rw']),
        ]
        self._init_context(console_mock, command_side_effect=command_side_effect)

        self.assertTrue(self.r.enable_write_on_root())

    @patch('readwrite.Console')
    def test_enable_write_on_root_failed(self, console_mock):
        command_side_effect = [
            self._get_console_command_return_value(),
            self._get_console_command_return_value(stdout=['ro']),
        ]
        self._init_context(console_mock, command_side_effect=command_side_effect)

        self.assertFalse(self.r.enable_write_on_root())

    @patch('readwrite.Console')
    def test_enable_write_on_root_error(self, console_mock):
        command_side_effect = [
            self._get_console_command_return_value(error=True),
            self._get_console_command_return_value(),
        ]
        self._init_context(console_mock, command_side_effect=command_side_effect)

        self.assertFalse(self.r.enable_write_on_root())

    @patch('readwrite.Console')
    def test_disable_write_on_root(self, console_mock):
        command_side_effect = [
            self._get_console_command_return_value(),
            self._get_console_command_return_value(stdout=['ro']),
        ]
        self._init_context(console_mock, command_side_effect=command_side_effect)

        context = ReadWriteContext()
        self.assertTrue(self.r.disable_write_on_root(context))

    @patch('readwrite.Console')
    def test_disable_write_on_root_failed(self, console_mock):
        command_side_effect = [
            self._get_console_command_return_value(),
            self._get_console_command_return_value(stdout=['rw']),
        ]
        self._init_context(console_mock, command_side_effect=command_side_effect)

        context = ReadWriteContext()
        self.assertFalse(self.r.disable_write_on_root(context))

    @patch('readwrite.Console')
    def test_disable_write_on_root_error(self, console_mock):
        command_side_effect = [
            self._get_console_command_return_value(error=True),
            self._get_console_command_return_value(),
        ]
        self._init_context(console_mock, command_side_effect=command_side_effect)

        context = ReadWriteContext()
        self.assertFalse(self.r.disable_write_on_root(context))

    @patch('readwrite.Console')
    def test_enable_write_on_root_on_non_cleep(self, console_mock):
        self._init_context(console_mock, on_cleep=False)

        self.assertFalse(self.r.enable_write_on_root())

    @patch('readwrite.Console')
    def test_enable_write_on_boot_on_non_cleep(self, console_mock):
        self._init_context(console_mock, on_cleep=False)

        self.assertFalse(self.r.enable_write_on_boot())

    @patch('readwrite.Console')
    def test_disable_write_on_root_on_non_cleep(self, console_mock):
        self._init_context(console_mock, on_cleep=False)

        context = ReadWriteContext()
        self.assertFalse(self.r.disable_write_on_root(context))

    @patch('readwrite.Console')
    def test_disable_write_on_boot_on_non_cleep(self, console_mock):
        self._init_context(console_mock, on_cleep=False)

        context = ReadWriteContext()
        self.assertFalse(self.r.disable_write_on_boot(context))


if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_readwrite.py; coverage report -m -i
    unittest.main()

