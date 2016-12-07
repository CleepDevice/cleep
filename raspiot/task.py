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
    A task can be periodic or not
    A periodic task is executed at regular interval while a non periodic task is executed once
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
        self._interval = interval 
        self.__timer = None

    def __run(self):
        """
        Run the task
        """
        #execute task
        self._task(*self._args, **self._kwargs)

        #launch again the timer if periodic task
        if self._interval:
            self.__timer = threading.Timer(self._interval, self.__run)
            self.__timer.start()
        else:
            self._timer = None

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


class BackgroundTask(threading.Thread):
    def __init__(self, process, pause=0.25):
        threading.Thread.__init__(self)
        self.process = process
        if pause<=0.25:
            pause = 0.25
        self.pause = int(float(pause)/0.25)
        self.running = True

    def __del__(self):
        self.stop()

    def run(self):
        while self.running:
            self.process()
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

