#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import bus
from raspiot import RaspIot
from datetime import datetime
import time
import task

__all__ = ['Scheduler']

#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO);

class Scheduler(RaspIot):

    CONFIG_FILE = 'scheduler.conf'
    DEPS = []

    def __init__(self, bus):
        RaspIot.__init__(self, bus)

        #launch time task
        self.time_task = task.Task(60.0, self.__send_time_event)
        self.time_task.start()

    def stop(self):
        RaspIot.stop(self)
        if self.time_task:
            self.time_task.stop()

    def __send_time_event(self):
        """
        Send time event every minute
        """
        req = bus.MessageRequest()
        req.event = 'event.time.now'
        req.params = {'time': int(time.time()) }
        self.push(req)

