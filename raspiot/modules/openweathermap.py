#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
from raspiot.utils import CommandError, MissingParameter
from raspiot.libs.task import Task
from raspiot.raspiot import RaspIotModule
import urllib
import urllib2
import ssl
import json
import time

__all__ = ['Openweathermap']


class Openweathermap(RaspIotModule):
    """
    OpenWeatherMap module

    Note:
        https://openweathermap.org/api
    """

    MODULE_CONFIG_FILE = 'openweathermap.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = 'Gets weather conditions using OpenWeatherMap service'
    MODULE_LOCKED = False
    MODULE_URL = 'https://github.com/tangb/Cleep/wiki/OpenWeatherMap'
    MODULE_TAGS = ['weather']

    DEFAULT_CONFIG = {
        'apikey': None
    }

    OWM_WEATHER_URL = 'http://api.openweathermap.org/data/2.5/weather'
    OWM_FORECAST_URL = 'http://api.openweathermap.org/data/2.5/forecast'
    OWM_TASK_DELAY = 1800
    #OWM_TASK_DELAY = 60
    OWM_WEATHER_CODES = {
        200: 'Thunderstorm with light rain',
        201: 'Thunderstorm with rain',
        202: 'Thunderstorm with heavy rain',
        210: 'Light thunderstorm',
        211: 'Thunderstorm',
        212: 'Heavy thunderstorm',
        221: 'Ragged thunderstorm',
        230: 'Thunderstorm with light drizzle',
        231: 'Thunderstorm with drizzle',
        232: 'Thunderstorm with heavy drizzle',
        300: 'Light intensity drizzle',
        301: 'Drizzle',
        302: 'Heavy intensity drizzle',
        310: 'Light intensity drizzle rain',
        311: 'Drizzle rain',
        312: 'Heavy intensity drizzle rain',
        313: 'Shower rain and drizzle',
        314: 'Heavy shower rain and drizzle',
        321: 'Shower drizzle',
        500: 'Light rain',
        501: 'Moderate rain',
        502: 'Heavy intensity rain',
        503: 'Very heavy rain',
        504: 'Extreme rain',
        511: 'Freezing rain',
        520: 'Light intensity shower rain',
        521: 'Shower rain',
        522: 'Heavy intensity shower rain',
        531: 'Ragged shower rain',
        600: 'Light snow',
        601: 'Snow',
        602: 'Heavy snow',
        611: 'Sleet',
        612: 'Shower sleet',
        615: 'Light rain and snow',
        616: 'Rain and snow',
        620: 'Light shower snow',
        621: 'Shower snow',
        622: 'Heavy shower snow',
        701: 'Mist',
        711: 'Smoke',
        721: 'Haze',
        731: 'Sand, dust whirls',
        741: 'Fog',
        751: 'Sand',
        761: 'Dust',
        762: 'Volcanic ash',
        771: 'Squalls',
        781: 'Tornado',
        800: 'Clear sky',
        801: 'Few clouds',
        802: 'Scattered clouds',
        803: 'Broken clouds',
        804: 'Overcast clouds',
        900: 'Tornado',
        901: 'Tropical storm',
        902: 'Hurricane',
        903: 'Cold',
        904: 'Hot',
        905: 'Windy',
        906: 'Hail',
        951: 'Calm',
        952: 'Light breeze',
        953: 'Gentle breeze',
        954: 'Moderate breeze',
        955: 'Fresh breeze',
        956: 'Strong breeze',
        957: 'High wind, near gale',
        958: 'Gale',
        959: 'Severe gale',
        960: 'Storm',
        961: 'Violent storm',
        962: 'Hurricane'
    }
    OWM_WIND_DIRECTIONS = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW','N']

    def __init__(self, bus, debug_enabled):
        """
        Constructor

        Args:
            bus (MessageBus): MessageBus instance
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotModule.__init__(self, bus, debug_enabled)

        #members
        self.weather_task = None
        self.__owm_uuid = None
        self.__forecast = []

    def _start(self):
        """
        Start module
        """
        #add openweathermap device
        if self._get_device_count()==0:
            owm = {
                'type': 'openweathermap',
                'name': 'OpenWeatherMap',
                'lastupdate': None,
                'celsius': None,
                'fahrenheit': None,
                'humidity': None,
                'pressure': None,
                'wind_speed': None,
                'wind_direction': None
            }
            self._add_device(owm)

        #get device uuid
        devices = self.get_module_devices()
        if len(devices)==1:
            self.__owm_uuid = devices.keys()[0]
        else:
            #supposed to have only one device!
            raise Exception('Openweathermap should handle only one device')

        #update weather conditions
        last_update = devices[self.__owm_uuid]['lastupdate']
        if last_update is None or last_update+self.OWM_TASK_DELAY<time.time():
            self.logger.debug('Update weather at startup')
            self.__weather_task()

        #start weather task
        self.weather_task = Task(self.OWM_TASK_DELAY, self.__weather_task)
        self.weather_task.start()

    def _stop(self):
        """
        Stop module
        """
        if self.weather_task is not None:
            self.weather_task.stop()

    def __get_weather(self, apikey):
        """
        Get weather condition

        Returns:
            dict: weather conditions
                http://openweathermap.org/current#parameter for output format

        Raises:
            InvalidParameter, CommandError
        """
        #check parameter
        if apikey is None or len(apikey)==0:
            raise InvalidParameter('Apikey parameter is missing')

        #get position infos from system module
        resp = self.send_command('get_city', 'system')
        self.logger.debug('Get city from system resp: %s' % resp)
        if resp['error']:
            raise CommandError(resp['message'])

        #create city pattern
        pattern = resp['data']['city']
        if len(resp['data']['country'])>0:
            pattern = '%s,%s' % (resp['data']['city'], resp['data']['country'])

        #prepare request parameters
        params = urllib.urlencode({
            'appid': apikey,
            'q': pattern,
            'units': 'metric',
            'mode': 'json'
        })
        self.logger.debug('Request params: %s' % params)

        error = None
        try:
            #launch request
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            req = urllib2.urlopen('%s?%s' % (self.OWM_WEATHER_URL, params), context=context)
            res = req.read()
            req.close()

            #parse request result
            data = json.loads(res)
            self.logger.debug('Weather response: %s' % (data))
            if data.has_key('cod'):
                if data['cod']!=200:
                    #request failed, get error message
                    if data.has_key('message'):
                        error = data['message']
                    else:
                        error = 'Unknown error'
            else:
                #invalid format
                self.logger.error('Invalid response format')
                error = 'Internal error'

        except urllib2.HTTPError as e:
            if e.code==401:
                error = 'Invalid apikey'
            else:
                error = 'Unknown error'

        except:
            self.logger.exception('Unable to get weather:')
            error = 'Internal error'

        if error is not None:
            raise CommandError(error)

        return data

    def __get_forecast(self, apikey):
        """
        Get forecast (5 days with 3 hours step)

        Returns:
            dict: forecast
                http://openweathermap.org/forecast5 for output format

        Raises:
            InvalidParameter, CommandError
        """
        #check parameter
        if apikey is None or len(apikey)==0:
            raise InvalidParameter('Apikey parameter is missing')

        #get position infos from system module
        resp = self.send_command('get_city', 'system')
        self.logger.debug('Get city from system resp: %s' % resp)
        if resp['error']:
            raise CommandError(resp['message'])

        #create city pattern
        pattern = resp['data']['city']
        if len(resp['data']['country'])>0:
            pattern = '%s,%s' % (resp['data']['city'], resp['data']['country'])

        #prepare request parameters
        params = urllib.urlencode({
            'appid': apikey,
            'q': pattern,
            'units': 'metric',
            'mode': 'json'
        })
        self.logger.debug('Request params: %s' % params)

        error = None
        try:
            #launch request
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            req = urllib2.urlopen('%s?%s' % (self.OWM_FORECAST_URL, params), context=context)
            res = req.read()
            req.close()

            #parse request result
            data = json.loads(res)
            self.logger.debug('Forecast response: %s' % (data))
            if data.has_key('cod'):
                if data['cod']!='200':
                    error = 'Unknown error'
                if not data.has_key('list'):
                    error = 'No forecast data'
            else:
                #invalid format
                self.logger.error('Invalid response format')
                error = 'Internal error'

        except urllib2.HTTPError as e:
            if e.code==401:
                error = 'Invalid apikey'
            else:
                error = 'Unknown error'

        except:
            self.logger.exception('Unable to get weather:')
            error = 'Internal error'

        if error is not None:
            raise CommandError(error)

        return data['list']

    def __weather_task(self):
        """
        Weather task in charge to refresh weather condition every hours
        """
        try:
            self.logger.debug('Update weather conditions')
            #get api key
            config = self._get_config()
            if config['apikey'] is not None and len(config['apikey'])>0:
                #apikey configured, get weather
                weather = self.__get_weather(config['apikey'])
                self.__forecast = self.__get_forecast(config['apikey'])

                #save current weather conditions
                device = self._get_devices()[self.__owm_uuid]
                device['lastupdate'] = int(time.time())
                if weather.has_key('weather') and len(weather['weather'])>0:
                    if weather['weather'][0].has_key('icon'):
                        device['icon'] = 'http://openweathermap.org/img/w/%s.png' % weather['weather'][0]['icon']
                    else:
                        device['icon'] = null
                    if weather['weather'][0].has_key('id'):
                        device['condition'] = self.OWM_WEATHER_CODES[weather['weather'][0]['id']]
                        device['code'] = int(weather['weather'][0]['id'])
                    else:
                        device['condition'] = None
                        device['code'] = None
                if weather.has_key('main'):
                    if weather['main'].has_key('temp'):
                        device['celsius'] = weather['main']['temp']
                        device['fahrenheit'] = weather['main']['temp'] * 9.0 / 5.0  + 32.0
                    else:
                        device['celsius'] = None
                        device['fahrenheit'] = None
                    if weather['main'].has_key('pressure'):
                        device['pressure'] = weather['main']['pressure']
                    else:
                        device['pressure'] = None
                    if weather['main'].has_key('humidity'):
                        device['humidity'] = weather['main']['humidity']
                    else:
                        device['humidity'] = None
                if weather.has_key('wind'):
                    if weather['wind'].has_key('speed'):
                        device['wind_speed'] = weather['wind']['speed']
                    else:
                        device['wind_speed'] = None
                    if weather['wind'].has_key('deg'):
                        device['wind_degrees'] = weather['wind']['deg']
                        index = int(round( (weather['wind']['deg'] % 360) / 22.5) + 1)
                        if index>=17:
                            index = 0
                        device['wind_direction'] = self.OWM_WIND_DIRECTIONS[index]
                    else:
                        device['wind_degrees'] = None
                        device['wind_direction'] = None
                self._update_device(self.__owm_uuid, device)

                #and emit event
                self.send_event('openweathermap.weather.update', device, self.__owm_uuid)
        except Exception as e:
            self.logger.exception('Exception during weather task:')

    def set_apikey(self, apikey):
        """
        Set openweathermap apikey

        Params:
            apikey (string): apikey

        Returns:
            bool: True if config saved successfully
        """
        if apikey is None or len(apikey)==0:
            raise MissingParameter('Apikey parameter is missing')

        #test apikey
        if not self.__get_weather(apikey):
            raise CommandError('Unable to test')

        #save config
        config = self._get_config()
        config['apikey'] = apikey

        return self._save_config(config)

    def get_weather(self):
        """
        Return current weather conditions
        Useful to use it in action script

        Returns:
            dict: device information
        """
        return self._get_devices()[self.__owm_uuid]

    def get_forecast(self):
        """
        Return last forecast information.
        May be empty if raspiot just restarted.

        Returns:
            list: list of forecast data (every 3 hours)
        """
        return self.__forecast
