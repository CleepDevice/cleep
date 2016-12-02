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

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG);

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

    def __compute_sun(self):
        """
        Compute sunset/sunrise times
        """
        logger.debug('Compute sunset/sunrise')

        #compute now
        now = int(time.time())
        dt = datetime.fromtimestamp(now)

        if self._config.has_key('city'):
            try:
                a = Astral(GoogleGeocoder)
                loc = a.geocoder[self._config['city']]
                sun = loc.sun()
                self.sunset = sun['sunset']
                self.sunrise = sun['sunrise']
                logger.debug('Sunset:%d:%d sunrise:%d:%d' % (self.sunset.hour, self.sunset.minute, self.sunrise.hour, self.sunrise.minute))
            except:
                logger.exception('Unable to compute sunset/sunrise time:')

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
        now_formatted =self.__format_time()

        req = bus.MessageRequest()
        req.event = 'event.time.now'
        req.params = now_formatted
        self.push(req)

        #handle sunset
        if self.sunset:
            if self.sunset.hour==now_formatted['hour'] and self.sunset.minute==now_formatted['minute']:
                #sunset time
                req = bus.MessageRequest()
                req.event = 'event.time.sunset'
                self.push(req)

        #handle sunrise
        if self.sunrise:
            if self.sunrise.hour==now_formatted['hour'] and self.sunrise.minute==now_formatted['minute']:
                #sunrise time
                req = bus.MessageRequest()
                req.event = 'event.time.sunrise'
                self.push(req)

        #compute sunset/sunrise at midnight
        if now_formatted['hour']==0 and now_formatted['minute']==0:
            self.__compute_sun()

    def get_time(self):
        """
        Return current time
        """
        return self.__format_time()

    def get_sun(self):
        """
        Return sunset and sunrise timestamps
        """
        return {
            'sunset': int(time.mktime(self.sunset.timetuple())),
            'sunrise': int(time.mktime(self.sunrise.timetuple()))
        }

    def get_city(self):
        """
        Return configured city
        """
        return self._config['city']

    def set_city(self, city):
        """
        Set city name
        @param city: closest city name
        """
        #save city
        config = self._get_config()
        config['city'] = city
        self._save_config(config)

        #compute sunset/sunrise
        self.__compute_sun()

        return self.get_sun()

