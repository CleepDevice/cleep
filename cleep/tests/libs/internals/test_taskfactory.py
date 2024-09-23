#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.tests.lib import TestLib
import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from taskfactory import TaskFactory
import unittest
import logging
from unittest.mock import Mock, patch
import time
from cleep.libs.tests.common import get_log_level
from threading import Event

LOG_LEVEL = get_log_level()


class TaskFactoryTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        TestLib(self)

    def tearDown(self):
        pass

    def init_context(self):
        self.stop_event = Mock()
        self.lib = TaskFactory(bootstrap={'app_stop_event': self.stop_event})

    @patch('taskfactory.Task')
    def test_create_task_without_args(self, mock_task):
        task_fn = Mock()
        self.init_context()

        result = self.lib.create_task(1.0, task_fn)

        self.assertEqual(result, mock_task.return_value)
        mock_task.assert_called_with(1.0, task_fn, self.lib.logger, self.stop_event, None, None, None)

    @patch('taskfactory.Task')
    def test_create_task_with_args(self, mock_task):
        task_fn = Mock()
        self.init_context()
        args = ['arg1', 'arg2']

        self.lib.create_task(1.0, task_fn, task_args=args)

        mock_task.assert_called_with(1.0, task_fn, self.lib.logger, self.stop_event, args, None, None)

    @patch('taskfactory.Task')
    def test_create_task_with_kwargs(self, mock_task):
        task_fn = Mock()
        self.init_context()
        kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}

        self.lib.create_task(1.0, task_fn, task_kwargs=kwargs)

        mock_task.assert_called_with(1.0, task_fn, self.lib.logger, self.stop_event, None, kwargs, None)

    @patch('taskfactory.Task')
    def test_create_task_with_end_callback(self, mock_task):
        task_fn = Mock()
        self.init_context()
        end_callback = Mock()

        self.lib.create_task(1.0, task_fn, end_callback=end_callback)

        mock_task.assert_called_with(1.0, task_fn, self.lib.logger, self.stop_event, None, None, end_callback)

    @patch('taskfactory.CountTask')
    def test_create_count_task_without_args(self, mock_counttask):
        task_fn = Mock()
        self.init_context()

        result = self.lib.create_count_task(1.0, task_fn, 2)

        self.assertEqual(result, mock_counttask.return_value)
        mock_counttask.assert_called_with(1.0, task_fn, 2, self.lib.logger, self.stop_event, None, None, None)

    @patch('taskfactory.CountTask')
    def test_create_count_task_with_args(self, mock_counttask):
        task_fn = Mock()
        self.init_context()
        args = ['arg1', 'arg2']

        self.lib.create_count_task(1.0, task_fn, 3, task_args=args)

        mock_counttask.assert_called_with(1.0, task_fn, 3, self.lib.logger, self.stop_event, args, None, None)

    @patch('taskfactory.CountTask')
    def test_create_count_task_with_kwargs(self, mock_counttask):
        task_fn = Mock()
        self.init_context()
        kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}

        self.lib.create_count_task(1.0, task_fn, 4, task_kwargs=kwargs)

        mock_counttask.assert_called_with(1.0, task_fn, 4, self.lib.logger, self.stop_event, None, kwargs, None)

    @patch('taskfactory.CountTask')
    def test_create_count_task_with_end_callback(self, mock_counttask):
        task_fn = Mock()
        self.init_context()
        end_callback = Mock()

        self.lib.create_count_task(1.0, task_fn, 5, end_callback=end_callback)

        mock_counttask.assert_called_with(1.0, task_fn, 5, self.lib.logger, self.stop_event, None, None, end_callback)

    @patch('taskfactory.CancelableTimer')
    def test_create_timer_without_args(self, mock_timer):
        task_fn = Mock()
        self.init_context()

        result = self.lib.create_timer(1.0, task_fn)

        self.assertEqual(result, mock_timer.return_value)
        mock_timer.assert_called_with(1.0, task_fn, None, None)

    @patch('taskfactory.CancelableTimer')
    def test_create_timer_with_args(self, mock_timer):
        task_fn = Mock()
        self.init_context()
        args = ['arg1', 'arg2']

        self.lib.create_timer(1.0, task_fn, task_args=args)

        mock_timer.assert_called_with(1.0, task_fn, args, None)

    @patch('taskfactory.CancelableTimer')
    def test_create_timer_with_kwargs(self, mock_timer):
        task_fn = Mock()
        self.init_context()
        kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}

        self.lib.create_timer(1.0, task_fn, task_kwargs=kwargs)

        mock_timer.assert_called_with(1.0, task_fn, None, kwargs)

    @patch('taskfactory.Task')
    @patch('taskfactory.CountTask')
    @patch('taskfactory.CancelableTimer')
    def test_stop_all_tasks_tasks_alive(self, mock_timer, mock_counttask, mock_task):
        self.init_context()
        mock_timer.return_value.is_alive.return_value = True
        mock_counttask.return_value.is_alive.return_value = True
        mock_task.return_value.is_alive.return_value = True
        task_fn = Mock()
        counttask_fn = Mock()
        timer_fn = Mock()
        self.lib.create_task(1.0, task_fn)
        self.lib.create_count_task(1.0, counttask_fn, 1)
        self.lib.create_timer(1.0, timer_fn)

        self.lib.stop_all_tasks()

        mock_timer.return_value.cancel.assert_called()
        mock_counttask.return_value.cancel.assert_called()
        mock_task.return_value.cancel.assert_called()

    @patch('taskfactory.Task')
    @patch('taskfactory.CountTask')
    @patch('taskfactory.CancelableTimer')
    def test_stop_all_tasks_tasks_not_alive(self, mock_timer, mock_counttask, mock_task):
        self.init_context()
        mock_timer.return_value.is_alive.return_value = False
        mock_counttask.return_value.is_alive.return_value = False
        mock_task.return_value.is_alive.return_value = False
        task_fn = Mock()
        counttask_fn = Mock()
        timer_fn = Mock()
        self.lib.create_task(1.0, task_fn)
        self.lib.create_count_task(1.0, counttask_fn, 1)
        self.lib.create_timer(1.0, timer_fn)

        self.lib.stop_all_tasks()

        mock_timer.return_value.cancel.assert_not_called()
        mock_counttask.return_value.cancel.assert_not_called()
        mock_task.return_value.cancel.assert_not_called()

    @patch('taskfactory.Task')
    def test_caller_instance_logger(self, mock_task):
        task_fn = Mock()
        self.init_context()
        self.logger = Mock()

        result = self.lib.create_task(1.0, task_fn)

        self.assertEqual(result, mock_task.return_value)
        mock_task.assert_called_with(1.0, task_fn, self.logger, self.stop_event, None, None, None)


if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_task.py; coverage report -m -i
    unittest.main()

