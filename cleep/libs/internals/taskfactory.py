#!/usr/bin/env python
# -*- coding: utf-8 -*-

from inspect import currentframe, getframeinfo, getmodulename
from pathlib import Path
import logging
from cleep.libs.internals.task import Task, CountTask, CancelableTimer


class TaskFactory:
    """
    Class factory to properly handle thread in Cleep application
    """

    def __init__(self, bootstrap):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap context
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.__app_stop_event = bootstrap["app_stop_event"]
        self.tasks = []

    def create_task(
        self, interval, task, task_args=None, task_kwargs=None, end_callback=None
    ):
        """
        Create new task

        Args:
            interval (float): interval to repeat task (in seconds). If None task is executed once
            task (callback): function to call periodically
            task_args (list): list of task parameters
            task_kwargs (dict): dict of task parameters
            end_callback (function): call this function as soon as task is terminatedœ
        """
        # get logger instance from caller
        caller_frame = currentframe().f_back
        first_arg_name = caller_frame.f_code.co_varnames[0]
        caller_instance = caller_frame.f_locals[first_arg_name]
        logger = self.__get_logger(caller_instance)

        # create new task
        task = Task(
            interval,
            task,
            logger,
            self.__app_stop_event,
            task_args,
            task_kwargs,
            end_callback,
        )
        self.tasks.append(task)
        return task

    def create_count_task(
        self, interval, task, count, task_args=None, task_kwargs=None, end_callback=None
    ):
        """
        Create new count task

        Args:
            interval (float): interval to repeat task (in seconds). If None task is executed once
            task (callback): function to call periodically
            count (int): number of time to run task before stopping
            task_args (list): list of task parameters
            task_kwargs (dict): dict of task parameters
            end_callback (function): call this function as soon as task is terminatedœ

        Returns:
            Task instance
        """
        # get logger instance from caller
        caller_frame = currentframe().f_back
        first_arg_name = caller_frame.f_code.co_varnames[0]
        caller_instance = caller_frame.f_locals[first_arg_name]
        logger = self.__get_logger(caller_instance)

        # create new task
        task = CountTask(
            interval,
            task,
            count,
            logger,
            self.__app_stop_event,
            task_args,
            task_kwargs,
            end_callback,
        )
        self.tasks.append(task)
        return task

    def create_timer(self, interval, task, task_args=None, task_kwargs=None):
        """
        Create new timer (that is really cancelable)

        Args:
            interval (float): run task after interval has passed
            task (callback): function to run

        Returns:
            CancelableTimer instance
        """
        timer = CancelableTimer(interval, task, task_args, task_kwargs)
        self.tasks.append(timer)
        return timer

    def stop_all_tasks(self):
        """
        Stop all tasks
        """
        for task in self.tasks:
            if task.is_alive():
                task.cancel()

    def __get_logger(self, caller_instance):
        """
        Get logger from caller instance or from internal logger

        Returns:
            logger instance
        """
        if not caller_instance or not hasattr(caller_instance, "logger"):
            return self.logger
        return caller_instance.logger
