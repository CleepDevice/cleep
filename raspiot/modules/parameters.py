#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import time
import copy
from raspiot.raspiot import RaspIotModule
from raspiot.utils import CommandError
from raspiot.libs.configs.hostname import Hostname
from raspiot.libs.internals.sun import Sun
from raspiot.libs.internals.console import Console
from raspiot.libs.internals.task import Task
import reverse_geocode
from timezonefinder import TimezoneFinder
from pytz import timezone
from tzlocal import get_localzone
from datetime import datetime
import re

__all__ = [u'Parameters']

class Parameters(RaspIotModule):
    """
    Allow to configure RaspIot parameters:
      - system time(current time, sunset, sunrise) according to position
      - system locale

    Useful doc:
        debian timezone: https://wiki.debian.org/TimeZoneChanges
        python datetime handling: https://hackernoon.com/avoid-a-bad-date-and-have-a-good-time-423792186f30
    """
    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'1.0.0'
    MODULE_PRICE = 0
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Configure generic parameters of your device'
    MODULE_LOCKED = True
    MODULE_TAGS = [u'configuration', u'date', u'time', u'locale', u'lang']
    MODULE_COUNTRY = None
    MODULE_URLINFO = None
    MODULE_URLHELP = None
    MODULE_URLBUGS = None
    MODULE_URLSITE = None

    MODULE_CONFIG_FILE = u'parameters.conf'
    #default position to raspberry pi foundation
    DEFAULT_CONFIG = {
        u'position': {
            u'latitude': 52.2040,
            u'longitude': 0.1208
        },
        u'country': {
            u'country': u'United Kingdom',
            u'alpha2': u'GB'
        },
        u'timezone': u'Europe/London'
    }

    SYSTEM_ZONEINFO_DIR = u'/usr/share/zoneinfo/'
    SYSTEM_LOCALTIME = u'/etc/localtime'
    SYSTEM_TIMEZONE = u'/etc/timezone'

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #members
        self.hostname = Hostname(self.cleep_filesystem)
        self.sun = Sun()
        self.sunset = None
        self.sunrise = None
        self.suns = {
            u'sunset': 0,
            u'sunset_iso': '',
            u'sunrise': 0,
            u'sunrise_iso': ''
        }
        self.timezonefinder = TimezoneFinder()
        self.timezone_name = None
        self.timezone = None
        self.time_task = None
        self.__clock_uuid = None
        self.__hostname_pattern = r'^[a-zA-Z][0-9a-zA-Z\-]{3,}[^-]$'

        #events
        self.systemTimeNow = self._get_event(u'system.time.now')
        self.systemTimeSunrise = self._get_event(u'system.time.sunrise')
        self.systemTimeSunset = self._get_event(u'system.time.sunset')
        self.systemHostnameUpdate = self._get_event(u'system.hostname.update')
        self.systemCountryUpdate = self._get_event(u'system.country.update')

    def _configure(self):
        """
        Configure module
        """
        #add clock device if not already added
        if self._get_device_count()<1:
            self.logger.debug(u'Add default devices')
            clock = {
                u'type': u'clock',
                u'name': u'Clock'
            }
            self._add_device(clock)

        #prepare country
        country = self._get_config_field(u'country')
        if not country:
            self.set_country()

        #prepare timezone
        timezone_name = self._get_config_field(u'timezone')
        if timezone_name:
            self.timezone = timezone(timezone_name)
        else:
            self.logger.info(u'No timezone defined, use default one. It will be updated when user set its position.')
            self.timezone = get_localzone()

        #compute sun times
        self.set_sun()

        #store device uuids for events
        #get_module_devices need to have timezone configured !
        devices = self.get_module_devices()
        for uuid in devices:
            if devices[uuid][u'type']==u'clock':
                self.__clock_uuid = uuid

        #launch time task
        self.time_task = Task(60.0, self.__time_task, self.logger)
        self.time_task.start()

    def get_module_config(self):
        """
        Get full module configuration
        """
        config = {}

        config[u'hostname'] = self.get_hostname()
        config[u'position'] = self.get_position()
        config[u'sun'] = self.get_sun()
        config[u'country'] = self.get_country()
        config[u'timezone'] = self.get_timezone()

        return config

    def get_module_devices(self):
        """
        Return clock as parameters device

        Returns:
            dict: devices
        """
        devices = super(Parameters, self).get_module_devices()
        
        for uuid in devices:
            if devices[uuid][u'type']==u'clock':
                data = self.__format_time()
                data.update({
                    u'sunrise': self.suns[u'sunrise'],
                    u'sunset': self.suns[u'sunset']
                })
                devices[uuid].update(data)

	return devices

    def __format_time(self, now=None):
        """
        Return time with different splitted infos

        Args:
            now (int): timestamp to use. If None current timestamp if used

        Returns:
            dict: time data::
                {
                    timestamp (int): current timestamp
                    iso (string): current datetime in iso 8601 format
                    year (int)
                    month (int)
                    day (int)
                    hour (int)
                    minute (int)
                    weekday (int): 0=monday, 1=tuesday... 6=sunday
                    weekday_literal (string): english literal weekday value (monday, tuesday, ...)
                }
        """
        #current time
        if not now:
            now = int(time.time())
        dt = datetime.fromtimestamp(now)
        dt = self.timezone.localize(dt)
        weekday = dt.weekday()
        if weekday==0:
            weekday_literal = u'monday'
        elif weekday==1:
            weekday_literal = u'tuesday'
        elif weekday==2:
            weekday_literal = u'wednesday'
        elif weekday==3:
            weekday_literal = u'thursday'
        elif weekday==4:
            weekday_literal = u'friday'
        elif weekday==5:
            weekday_literal = u'saturday'
        elif weekday==6:
            weekday_literal = u'sunday'

        return {
            u'timestamp': now,
            u'iso': dt.isoformat(),
            u'year': dt.year,
            u'month': dt.month,
            u'day': dt.day,
            u'hour': dt.hour,
            u'minute': dt.minute,
            u'weekday': weekday,
            u'weekday_literal': weekday_literal
        }

    def __time_task(self):
        """
        Time task used to refresh time
        """
        now = int(time.time())
        now_formatted = self.__format_time()

        #send now event
        now_event_params = copy.deepcopy(now_formatted)
        now_event_params.update({
            u'sunrise': self.suns[u'sunrise'],
            u'sunset': self.suns[u'sunset']
        })
        self.systemTimeNow.send(params=now_event_params, device_id=self.__clock_uuid)
        self.systemTimeNow.render([u'sound', u'display'], params=now_formatted)

        #send sunrise event
        if self.sunrise:
            if now_formatted[u'hour']==self.sunrise.hour and now_formatted[u'minute']==self.sunrise.minute:
                self.systemTimeSunrise.send(device_id=self.__clock_uuid)
                self.systemTimeSunrise.render([u'display', u'sound'], params=self.__clock_uuid)

        #send sunset event
        if self.sunset:
            if now_formatted[u'hour']==self.sunset.hour and now_formatted[u'minute']==self.sunset.minute:
                self.systemTimeSunset.send(device_id=self.__clock_uuid)
                self.systemTimeSunset.render([u'display', u'sound'], params=self.__clock_uuid)

        #update sun times after midnight
        if now_formatted[u'hour']==0 and now_formatted[u'minute']==5:
            self.set_sun()

    def set_hostname(self, hostname):
        """
        Set raspi hostname

        Args:
            hostname (string): hostname

        Return:
            bool: True if hostname saved successfully, False otherwise
        """
        #check hostname
        if re.match(self.__hostname_pattern, hostname) is None:
            raise CommandError(u'Hostname is not valid')

        #update hostname
        res = self.hostname.set_hostname(hostname)

        #send event to update hostname on all devices
        if res:
            self.systemHostnameUpdate.send(params={u'hostname': hostname})

        return res

    def get_hostname(self):
        """
        Return raspi hostname

        Returns:
            string: raspi hostname
        """
        return self.hostname.get_hostname()

    def set_position(self, latitude, longitude):
        """
        Set device position
        
        Args:
            latitude (float): latitude
            longitude (float): longitude
        """
        #save new position
        position = {
            u'latitude': latitude,
            u'longitude': longitude
        }

        if not self._set_config_field(u'position', position):
            raise CommandError(u'Unable to save position')

        #and position related stuff
        self.set_timezone()
        self.set_country()
        self.set_sun()

    def get_position(self):
        """
        Return device position

        Returns:
            dict: position coordinates::
                {
                    latitude (float),
                    longitude (float)
                }
        """
        return self._get_config_field(u'position')

    def get_sun(self):
        """
        Compute sun times

        Returns:
            dict: sunset/sunrise timestamps::
                {
                    sunrise (int),
                    sunset (int)
                }
        """
        return self.suns

    def set_sun(self):
        """"
        Compute sun times (sunrise and sunset) according to configured position
        """
        #get position
        position = self._get_config_field(u'position')
        timezone = self._get_config_field(u'timezone')

        #compute sun times
        self.sunset = None
        self.sunrise = None
        if position[u'latitude']!=0 and position[u'longitude']!=0:
            self.sun.setPosition(position[u'latitude'], position[u'longitude'], timezone)
            self.sunset = self.sun.sunset()
            self.sunrise = self.sun.sunrise()
            self.logger.debug('Found sunrise:%s sunset:%s' % (self.sunset, self.sunrise))

            #save times
            self.suns[u'sunrise'] = int(self.sunrise.strftime('%s'))
            self.suns[u'sunrise_iso'] = self.sunrise.isoformat()
            self.suns[u'sunset'] = int(self.sunset.strftime('%s'))
            self.suns[u'sunset_iso'] = self.sunset.isoformat()

    def set_country(self):
        """
        Compute country (and associated alpha) from current internal position
        /!\ This function can take some time to find country info on slow device like raspi 1st generation (~15secs)
        """
        #get position
        position = self._get_config_field(u'position')

        #get country from position
        country = {
            u'country': None,
            u'alpha2': None
        }
        if position[u'latitude']!=0 and position[u'longitude']!=0:
            try:
                #search country
                coordinates = (position[u'latitude'], position[u'longitude']),
                geo = reverse_geocode.search(coordinates)
                self.logger.debug('Found country infos from position %s: %s' % (position, geo))
                if geo and len(geo)>0 and u'country_code' in geo[0] and u'country' in geo[0]:
                    country[u'alpha2'] = geo[0][u'country_code']
                    country[u'country'] = geo[0][u'country']

                #save new country
                self._set_config_field(u'country', country)

                #send event
                self.systemCountryUpdate.send(params=country);

            except:
                self.logger.exception(u'Unable to find country for position %s:' % position)

        else:
            self.logger.debug(u'Unable to get country from unspecified position (%s)' % position)

    def get_country(self):
        """
        Get country from position

        """
        return self._get_config_field(u'country')

    def set_timezone(self):
	"""
        Set timezone according to coordinates
        """
        #get position
        position = self._get_config_field(u'position')

        #compute timezone
        timezone = None
        if position[u'latitude']!=0 and position[u'longitude']!=0:
            try:
                timezone = self.timezonefinder.timezone_at(lat=position[u'latitude'], lng=position[u'longitude'])
                if timezone is None:
                    timezone = self.timezonefinder.closest_timezone_at(lat=position[u'latitude'], lng=position[u'longitude'])
                    #TODO increase delta_degree to extend research, careful it use more CPU !

            except ValueError:
                #the coordinates were out of bounds
                self.logger.exception(u'Coordinates out of bounds')

        #save timezone value
        self.logger.debug('Save new timezone: %s' % timezone)
        if not self._set_config_field(u'timezone', timezone):
            raise CommandError(u'Unable to save timezone')

        #configure system timezone
        if timezone:
            zoneinfo = os.path.join(self.SYSTEM_ZONEINFO_DIR, timezone)
            self.logger.debug(u'Checking zoneinfo file: %s' % zoneinfo)
            if os.path.exists(zoneinfo):
                self.cleep_filesystem.rm(self.SYSTEM_LOCALTIME)
                if not self.cleep_filesystem.write_data(self.SYSTEM_TIMEZONE, u'%s' % timezone):
                    self.logger.error(u'Unable to write timezone data on "%s". System timezone is not configured!' % self.SYSTEM_TIMEZONE)
                    return False

                #launch timezone update in background
                self.logger.debug(u'Updating system timezone')
                command = Console()
                res = command.command(u'/usr/sbin/dpkg-reconfigure -f noninteractive tzdata', timeout=15.0)
                self.logger.debug('Timezone update command result: %s' % res)
                # /!\ can't check command res because command output is printed on stderr :(
                
            else:
                self.logger.warning(u'Unable to set device timezone on non existing zoneinfo file: %s' % zoneinfo)
                return False

        return True

    def get_timezone(self):
        """
        Return timezone

        Returns:
            string: current timezone name
        """
        return self._get_config_field(u'timezone')

