#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import bus
from raspiot import RaspIot
from datetime import datetime
import time
import task
from astral import Astral, GoogleGeocoder

__all__ = ['Scheduler']

#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG);

class Scheduler(RaspIot):

    CONFIG_FILE = 'scheduler.conf'
    DEPS = []

    def __init__(self, bus):
        RaspIot.__init__(self, bus)
        self.sunset = None
        self.sunrise = None

        #launch time task
        self.time_task = task.Task(60.0, self.__send_time_event)
        self.time_task.start()

        #compute sun times
        self.__compute_sun()

    def stop(self):
        RaspIot.stop(self)
        if self.time_task:
            self.time_task.stop()

    def __compute_sun(self, now=None):
        """
        Compute sunset/sunrise times
        """
        #compute now
        if not now:
            now = int(time.time())
        dt = datetime.fromtimestamp(now)

        if self.sunrise==None or self.sunset==None or (dt.hour==0 and dt.minute==0):
            if self._config.has_key('city'):
                try:
                    a = Astral(GoogleGeocoder)
                    loc = a.geocoder[self._config['city']]
                    sun = loc.sun()
                    self.sunset = sun['sunset']
                    self.sunrise = sun['sunrise']
                    logger.debug('Sunset:%d:%d sunrise:%d:%d' % (self.sunset.hour, self.sunset.minute, self.sunrise.hour, self.sunrise.minute))
                except:
                    logger.error('Unable to compute sunset/sunrise time:')

    def __format_time(self, now=None):
        """
        Return current time object
        """
        if not now:
            now = int(time.time())
        dt = datetime.fromtimestamp(now)
        weekday = dt.weekday()
        if weekday==0:
            weekday_literal = 'monday'
        elif weekday==1:
            weekday_literal = 'tuesday'
        elif weekday==2:
            weekday_literal = 'wednesday'
        elif weekday==3:
            weekday_literal = 'thursday'
        elif weekday==4:
            weekday_literal = 'friday'
        elif weekday==5:
            weekday_literal = 'saturday'
        elif weekday==6:
            weekday_literal = 'sunday'
        return {
            'time': now,
            'year': dt.year,
            'month': dt.month,
            'day': dt.day,
            'hour': dt.hour,
            'minute': dt.minute,
            'weekday': weekday,
            'weekday_literal': weekday_literal
        }

    def __send_time_event(self):
        """
        Send time event every minute
        Send sunset/sunrise
        """
        now = int(time.time())
        params = self.__format_time()

        req = bus.MessageRequest()
        req.event = 'event.time.now'
        req.params = params
        self.push(req)

        #handle sunset
        if self.sunset:
            if self.sunset.hour==params['hour'] and self.sunset.minute==params['minute']:
                #sunset time
                req = bus.MessageRequest()
                req.event = 'event.time.sunset'
                self.push(req)

        #handle sunrise
        if self.sunrise:
            if self.sunrise.hour==params['hour'] and self.sunrise.minute==params['minute']:
                #sunrise time
                req = bus.MessageRequest()
                req.event = 'event.time.sunrise'
                self.push(req)

        #compute sunset/sunrise at midnight
        self.__compute_sun()

    def get_time(self):
        """
        Return current time
        """
        return self.__format_time()

