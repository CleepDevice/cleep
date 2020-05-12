#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from console import EndlessConsole, Console, AdvancedConsole
from cleep.libs.tests.lib import TestLib
import unittest
import logging
import time
from unittest.mock import Mock

class ConsoleTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.counter_stdout = 0
        self.counter_stderr = 0
        self.return_code = None
        self.killed = None

    def tearDown(self):
        self.counter_stdout = 0
        self.counter_stderr = 0
        self.return_code = None
        self.killed = None

    def _std_callback(self, stdout, stderr):
        if stdout:
            self.counter_stdout +=1
        if stderr:
            self.counter_stderr += 1

    def _end_callback(self, return_code, killed):
        logging.debug('end_callback called')
        self.return_code = return_code
        self.killed = killed

    def _result_callback(self, result):
        logging.debug('Result: %s' % result)
        self.counter_stdout = len(result['stdout'])
        self.counter_stderr = len(result['stderr'])
        self.return_code = result['returncode']
        self.killed = result['killed']

    def test_endless_console(self):
        e = EndlessConsole('sleep 1; echo tick; sleep 1; 1>&2 echo tock', self._std_callback, self._end_callback)
        e.start()
        time.sleep(3.0)
        self.assertNotEqual(e.get_start_time(), 0)
        self.assertFalse(self.killed)
        self.assertEqual(self.return_code, 0)
        self.assertEqual(self.counter_stdout, 1)
        self.assertEqual(self.counter_stderr, 1)

    def test_endless_console_kill(self):
        e = EndlessConsole('sleep 1; echo tick; sleep 1; 1>&2 echo tock', self._std_callback, self._end_callback)
        e.start()
        time.sleep(1)
        e.stop() # kill() alias
        time.sleep(2.0)
        self.assertTrue(self.killed)

    def test_endless_console_no_callbacks(self):
        e = EndlessConsole('sleep 1; echo tick; sleep 1; 1>&2 echo tock', None)
        e.start()
        time.sleep(3.0)
        self.assertIsNone(self.killed)
        self.assertIsNone(self.return_code)
        self.assertEqual(self.counter_stdout, 0)
        self.assertEqual(self.counter_stderr, 0)

    def test_endless_console_exception_in_std_callback(self):
        e = EndlessConsole('sleep 1; echo tick; sleep 1; 1>&2 echo tock', Mock(side_effect=Exception('test exception')))
        e.start()
        time.sleep(3.0)
        self.assertNotEqual(e.get_start_time(), 0)
        self.assertEqual(self.counter_stdout, 0)
        self.assertEqual(self.counter_stderr, 0)

    def test_endless_console_exception_in_end_callback(self):
        e = EndlessConsole('sleep 1; echo tick; sleep 1; 1>&2 echo tock', self._std_callback, Mock(side_effect=Exception('test exception')))
        e.start()
        time.sleep(3.0)
        self.assertNotEqual(e.get_start_time(), 0)
        self.assertEqual(self.counter_stdout, 1)
        self.assertEqual(self.counter_stderr, 1)

    def test_console(self):
        c = Console()
        res = c.command('echo tick; 1>&2 echo tock')
        logging.debug('Result: %s' % res)
        self.assertEqual(c.get_last_return_code(), 0)
        self.assertTrue(isinstance(res, dict))
        self.assertTrue('returncode' in res)
        self.assertTrue('error' in res)
        self.assertTrue('killed' in res)
        self.assertTrue('stdout' in res)
        self.assertTrue('stderr' in res)
        self.assertFalse(res['killed'])
        self.assertEqual(res['returncode'], 0)
        self.assertEqual(len(res['stdout']), 1)
        self.assertEqual(len(res['stderr']), 1)

    def test_console_command_failed(self):
        c = Console()
        res = c.command('echo tick; 1>&2 echo tock; exit 2')
        logging.debug('Result: %s' % res)
        self.assertEqual(c.get_last_return_code(), 2)
        self.assertEqual(res['returncode'], 2)

    def test_console_invalid_parameters(self):
        c = Console()
        with self.assertRaises(Exception) as cm:
            res = c.command('echo tick; 1>&2 echo tock', None)
        self.assertEqual(str(cm.exception), 'Timeout is mandatory and must be greater than 0')
        with self.assertRaises(Exception) as cm:
            res = c.command('echo tick; 1>&2 echo tock', 0)
        self.assertEqual(str(cm.exception), 'Timeout is mandatory and must be greater than 0')

    def test_console_timeout(self):
        c = Console()
        start = time.time()
        res = c.command('echo tick; 1>&2 echo tock; sleep 3', 1)
        self.assertLessEqual(start - time.time(), 1.25)
        self.assertTrue(res['killed'])

    def test_console_delayed_command(self):
        c = Console()
        logging.debug('Start delayed command')
        c.command_delayed('echo tick; 1>&2 echo tock', 2.0, callback=self._result_callback)
        time.sleep(3.0)
        self.assertEqual(self.return_code, 0)
        self.assertFalse(self.killed)
        self.assertEqual(self.counter_stdout, 1)
        self.assertEqual(self.counter_stderr, 1)

    def test_console_delayed_command_timeout(self):
        c = Console()
        logging.debug('Start delayed command')
        c.command_delayed('echo tick; 1>&2 echo tock; sleep 3', 1.0, callback=self._result_callback)
        time.sleep(4.0)
        self.assertTrue(self.killed)

    def test_advanced_console(self):
        c = AdvancedConsole()
        res = c.find('echo tick; 1>&2 echo tock; echo tack', r'(t.ck)')
        logging.debug('Result: %s' % res)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0][1][0], 'tick')
        self.assertEqual(res[1][1][0], 'tack')

    def test_advanced_console_command_failed(self):
        c = AdvancedConsole()
        res = c.find('echo tick; exit 2', r'(t.ck)')
        logging.debug('Result: %s' % res)
        self.assertEqual(len(res), 0)
        

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python*/*","*test_*.py" --concurrency=thread test_console.py; coverage report -m -i
    unittest.main()

