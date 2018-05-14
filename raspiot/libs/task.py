#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import glob
import uuid as moduuid
import json
from threading import Timer, Thread
import time

__all__ = [u'Task', u'BackgroundTask', u'CountTask']

class Task:
    """
    Run a task asynchronously
    If interval specified task is executed periodically. If interval is not specified, task is executed immediately once
    """
    def __init__(self, interval, task, logger, task_args=[], task_kwargs={}):
        """
        Create new task
        
        Args:
            interval (float): interval to repeat task (in seconds)
            task (callback): function to call periodically
            logger (logger): logger instance used to log message in task
        """
        self._task = task
        self._args = task_args
        self.logger = logger
        self._kwargs = task_kwargs
        if interval is None:
            self._interval = 0.0
        else:
            self._interval = interval
        self.__timer = None
        self._run_count = None

    def __run(self):
        """
        Run the task
        """
        #execute task
        if self._run_count is not None:
            self._run_count -= 1
        run_again = False
        try:
            self._task(*self._args, **self._kwargs)
        except:
            #exception occured
            if self.logger:
                self.logger.exception(u'Exception occured in task execution:')

        #launch again the timer if periodic task
        if self._interval:
            if self._run_count is None:
                #interval specified + run_count is NOT configured
                run_again = True
            else:
                #interval specified + run_count is configured
                if self._run_count>0:
                    run_again = True
        else:
            #interval not configured, don't run task again
            self._timer = None

        #run again task?
        if run_again:
            self.__timer = Timer(self._interval, self.__run)
            self.__timer.start()

    def set_interval(self, interval):
        """
        Define a task interval to repeat the task

        Args:
            interval (int): task interval (in seconds)
        """
        self._interval = interval
  
    def start(self):
        """
        Start the task
        """
        if self.__timer:
            self.stop()
        self.__timer = Timer(self._interval, self.__run)
        self.__timer.start()
  
    def stop(self):
        """
        Stop the task
        """
        if self.__timer:
            self.__timer.cancel()
            self.__timer = None


class CountTask(Task):
    """
    Run task X times
    """

    def __init__(self, interval, task, count, task_args=[], task_kwargs={}):
        """
        Constructor
        
        Args:
            interval (int): interval to repeat task (in seconds)
            task (function): function to call periodically
            count (int): number of times to run task
        """
        Task.__init__(self, interval, task, task_args, task_kwargs)
        self._run_count = count


class BackgroundTask(Thread):
    """
    Run background task indefinitely (thread helper)
    Difference between Task class is BackgroundTask does not add pause between callback (task) execution.
    It's just a thread helper
    """

    def __init__(self, task, logger, pause=0.25):
        """
        Constructor
        Args:
            task (callback): function to call
            logger (logger): logger instance to log task messages
            pause (int): pause between task call (in seconds)
        """
        Thread.__init__(self)
        Thread.daemon = True
        self.task = task
        self.logger = logger
        if pause<=0.25:
            pause = 0.25
        self.pause = int(float(pause)/0.25)
        self.running = True

    def __del__(self):
        """
        Destructor
        """
        self.stop()

    def run(self):
        """
        Run task
        """
        while self.running:
            try:
                self.task()
            except:
                if self.logger:
                    self.logger.exception(u'Exception occured during task execution:')
            for i in range(self.pause):
                if not self.running:
                    break
                time.sleep(0.25)

    def stop(self):
        """
        Stop task
        """
        self.running = False


if __name__ == '__main__':
    #testu
    def tick(msg):
        print 'msg=%s' % unicode(msg)

    def tock():
        print 'tock'

    #t = Task(2.0, tick, ['hello'])
    #t.start()

    #t = BackgroundTask(1.0, tock)
    #t.start()

    t = CountTask(1.0, tick, 1, ['coucou'])
    t.start()

    time.sleep(10.0)
    print '-> stop task'
    t.stop()
