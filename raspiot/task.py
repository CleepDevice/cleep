#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import glob
import uuid as moduuid
import json
import threading
import time

__all__ = ['Task', 'BackgroundTask']

class Task:
    """
    Run a task asynchronously
    If interval specified task is executed periodically. If interval is not specified, task is executed imediately once
    """
    def __init__(self, interval, task, task_args=[], task_kwargs={}):
        """
        Create new task
        @param interval : interval to repeat task (in s)
        @param task: function to call periodically
        """
        self._task = task
        self._args = task_args
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
        self._run_count -= 1
        run_again = False
        self._task(*self._args, **self._kwargs)

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
            self.__timer = threading.Timer(self._interval, self.__run)
            self.__timer.start()

    def set_interval(self, interval):
        """
        Define a task interval to repeat the task
        @param interval: task interval (in s)
        """
        self._interval = interval
  
    def start(self):
        """
        Start the task
        """
        if self.__timer:
            self.stop()
        self.__timer = threading.Timer(self._interval, self.__run)
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
    def __init__(self, interval, task, count=1, task_args=[], task_kwargs={}):
        """
        Constructor
        @param interval : interval to repeat task (in s)
        @param task: function to call periodically
        @param count: number of times to run task
        """
        Task.init(self, interval, task, task_args, task_kwargs)
        self._run_count = count


class BackgroundTask(threading.Thread):
    """
    Run background task indefinitely (thread helper)
    """
    def __init__(self, task, pause=0.25):
        """
        Constructor
        @param task: function to call
        @param pause: pause between task call
        """
        threading.Thread.__init__(self)
        self.task = task
        if pause<=0.25:
            pause = 0.25
        self.pause = int(float(pause)/0.25)
        self.running = True

    def __del__(self):
        self.stop()

    def run(self):
        while self.running:
            self.task()
            for i in range(self.pause):
                if not self.running:
                    break
                time.sleep(0.25)

    def stop(self):
        self.running = False


if __name__ == '__main__':
    #testu
    def tick(msg):
        print 'msg=%s' % str(msg)

    def tock():
        print 'tock'

    #t = Task(2.0, tick, ['hello'])
    #t.start()

    t = BackgroundTask(tock, 1.0)
    t.start()
    time.sleep(5.0)
    print '-> stop background task'
    t.stop()

