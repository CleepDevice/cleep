#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import bus
from raspiot import RaspIot
from datetime import datetime
import time
import task
from astral import Astral, GoogleGeocoder, AstralError

__all__ = ['Scheduler']

class Scheduler(RaspIot):

    MODULE_CONFIG_FILE = 'scheduler.conf'
    MODULE_DEPS = []

    DEFAULT_CONFIG = {
        'city': None
    }

    def __init__(self, bus):
        #init
        RaspIot.__init__(self, bus)
        self.logger = logging.getLogger(self.__class__.__name__)

        #check config
        self._check_config(Scheduler.DEFAULT_CONFIG)

        #members
        self.sunset = time.mktime(datetime.min.timetuple())
        self.sunrise = time.mktime(datetime.min.timetuple())

        #launch time task
        self.time_task = task.Task(60.0, self.__send_time_event)
        self.time_task.start()

        #compute sun times
        self.__compute_sun()

    def stop(self):
        RaspIot.stop(self)
        if self.time_task:
            self.time_task.stop()

    def __search_city(self, city):
        """
        Search for specified city
        @return astral location (from geocoder function)
        """
        try:
            a = Astral(GoogleGeocoder)
            return a.geocoder[city]
        except AstralError as e:
            if e.message and e.message.find('Unable to locate')>=0:
                raise Exception('Unable to find city. Please specify a bigger city.')
            else:
                raise Exception(e.message)

    def __compute_sun(self, city=None):
        """
        Compute sunset/sunrise times
        """
        self.logger.debug('Compute sunset/sunrise')

        #force city from configurated one if city not specified
        if not city:
            if self._config.has_key('city') and self._config['city'] is not None:
                city = self._config['city']
            else:
                #no city available
                city = None
                
        if city:
            loc = self.__search_city(city)
            sun = loc.sun()
            self.sunset = sun['sunset']
            self.sunrise = sun['sunrise']
            self.logger.debug('Sunset:%d:%d sunrise:%d:%d' % (self.sunset.hour, self.sunset.minute, self.sunrise.hour, self.sunrise.minute))
            
        else:
            self.sunset = None
            self.sunrise = None
            self.logger.warning('No city configured, scheduler will only return current timestamp')

    def __format_time(self, now=None):
        """
        Return current time object
        """
        #current time
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

        #sunset and sunrise
        sunset = None
        if self.sunset:
            sunset = time.mktime(self.sunset.timetuple())
        sunrise = None
        if self.sunrise:
            sunrise = time.mktime(self.sunrise.timetuple())

        return {
            'time': now,
            'year': dt.year,
            'month': dt.month,
            'day': dt.day,
            'hour': dt.hour,
            'minute': dt.minute,
            'weekday': weekday,
            'weekday_literal': weekday_literal,
            'sunset': sunset,
            'sunrise': sunrise
        }

    def __send_time_event(self):
        """
        Send time event every minute
        Send sunset/sunrise
        """
        now = int(time.time())
        now_formatted = self.__format_time()

        req = bus.MessageRequest()
        req.event = 'scheduler.time.now'
        req.params = now_formatted
        self.push(req)

        #handle sunset
        if self.sunset:
            if self.sunset.hour==now_formatted['hour'] and self.sunset.minute==now_formatted['minute']:
                #sunset time
                req = bus.MessageRequest()
                req.event = 'scheduler.time.sunset'
                self.push(req)

        #handle sunrise
        if self.sunrise:
            if self.sunrise.hour==now_formatted['hour'] and self.sunrise.minute==now_formatted['minute']:
                #sunrise time
                req = bus.MessageRequest()
                req.event = 'scheduler.time.sunrise'
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
        sunset = None
        if self.sunset:
            sunset = int(time.mktime(self.sunset.timetuple()))
        sunrise = None
        if self.sunrise:
            sunrise = int(time.mktime(self.sunrise.timetuple()))
        return {
            'sunset': sunset,
            'sunrise': sunrise
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
        #compute sunset/sunrise
        self.__compute_sun(city)
        
        #save city (exception raised before if error occured)
        config = self._get_config()
        config['city'] = city
        self._save_config(config)

        return self.get_sun()

