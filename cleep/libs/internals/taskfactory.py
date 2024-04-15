#!/usr/bin/env python
# -*- coding: utf-8 -*-

from inspect import currentframe, getframeinfo, getmodulename
from pathlib import Path
import logging
from cleep.libs.internals.task import Task

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

    def create_task(self, interval, task, task_args=None, task_kwargs=None, end_callback=None):
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
        logger = caller_instance.logger or self.logger

        # create new task
        task = Task(interval, task, logger, self.__app_stop_event, task_args, task_kwargs, end_callback);
        self.tasks.append(task)
        return task

    def stop_all_tasks(self):
        """
        Stop all task
        """
        for task in tasks:
            if task.is_alive():
                task.cancel()
