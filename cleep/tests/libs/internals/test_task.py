#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from task import Task, CountTask
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import Mock
import time

class TaskTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        TestLib()

    def tearDown(self):
        pass

    def _init_context(self, interval=0.5, logger=None, task=None, task_args=None, task_kwargs=None, count=0, end_callback=None):
        logger = logger if logger is not None else logging.getLogger('TestTask')
        if count==0:
            logging.debug('Init Task')
            self.t = Task(interval=interval, task=task, logger=logger, task_args=task_args, task_kwargs=task_kwargs, end_callback=end_callback)
        else:
            logging.debug('Init CountTask')
            self.t = CountTask(interval=interval, task=task, logger=logger, task_args=task_args, task_kwargs=task_kwargs, count=count, end_callback=end_callback)

    def test_task(self):
        def delay():
            time.sleep(0.5)
        task = Mock(side_effect=delay)
        self._init_context(task=task)

        self.t.start()
        time.sleep(0.25)
        self.t.wait()
        time.sleep(0.25)
        self.t.wait()
        time.sleep(0.25)
        self.t.wait()
        time.sleep(0.25)
        self.assertTrue(self.t.is_running())
        self.t.stop()

        self.assertTrue(task.called)
        self.assertEqual(task.call_count, 4)

    def test_task_list_parameters(self):
        task = Mock()
        args = ['a string', 666]
        self._init_context(task=task, task_args=args)

        self.t.start()
        self.t.wait()
        self.t.stop()
        
        logging.debug('args: %s' % str(task.call_args))
        self.assertEqual(task.call_args[0], (args[0], args[1]))

    def test_task_dict_parameters(self):
        task = Mock()
        kwargs = {
            'string': 'a string',
            'number': 666,
        }
        self._init_context(task=task, task_kwargs=kwargs)

        self.t.start()
        self.t.wait()
        self.t.stop()
        
        logging.debug('Args: %s' % str(task.call_args[0]))
        self.assertEqual(task.call_args[0], ())
        logging.debug('Kwargs: %s' % str(task.call_args[1]))
        self.assertEqual(task.call_args[1], kwargs)

    def test_task_no_interval(self):
        task = Mock()
        self._init_context(interval=None, task=task)

        self.t.start()
        self.t.wait()

        self.assertFalse(self.t.is_running())
        self.assertTrue(task.called)
        self.assertEqual(task.call_count, 1)

    def test_task_restart_task(self):
        task = Mock()
        self._init_context(task=task)

        self.t.start()
        self.t.wait()
        self.t.start()
        self.t.wait()
        self.t.stop()

        self.assertFalse(self.t.is_running())
        self.assertTrue(task.called)
        self.assertEqual(task.call_count, 3)

    def test_task_exception(self):
        task = Mock(side_effect=Exception('Test'))
        self._init_context(task=task)
        self.t.start()
        self.t.wait()
        
        self.assertFalse(self.t.is_running())
        self.assertTrue(task.called)
        self.assertEqual(task.call_count, 1)

    def test_task_end_callback(self):
        task = Mock()
        mock_endcb = Mock()
        self._init_context(interval=None, task=task, end_callback=mock_endcb)

        self.t.start()
        time.sleep(0.5)
        self.t.wait()

        self.assertFalse(self.t.is_running())

        self.assertTrue(mock_endcb.called)

    def test_count_task(self):
        task = Mock()
        self._init_context(task=task, interval=0.25, count=4)
        self.t.start()
        self.t.wait()

        self.assertEqual(task.call_count, 4)

    def test_count_task_end_callback(self):
        task = Mock()
        mock_endcb = Mock()
        self._init_context(task=task, interval=0.25, count=4, end_callback=mock_endcb)
        self.t.start()
        self.t.wait()

        self.assertEqual(mock_endcb.call_count, 1)
        self.assertEqual(task.call_count, 4)



if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_task.py; coverage report -m -i
    unittest.main()

