#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
from raspiot.raspiot import RaspIotProvider
from raspiot.utils import CommandError, MissingParameter, CommandInfo
from raspiot.libs.profiles import PushProfile 
import urllib
import httplib
import json
import time

__all__ = ['Pushover']


class Pushover(RaspIotProvider):
    """
    Pushover module
    """

    MODULE_CONFIG_FILE = 'pushover.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = 'Sends you push alerts using Pushover service.'
    MODULE_LOCKED = False
    MODULE_URL = 'https://github.com/tangb/Cleep/wiki/ModulePushover'
    MODULE_TAGS = ['push', 'alert']

    DEFAULT_CONFIG = {
        'apikey': None,
        'userkey': None
    }
    PUSHOVER_API_URL = 'api.pushover.net:443'

    PROVIDER_PROFILES = [PushProfile()]
    PROVIDER_TYPE = 'alert.push'

    def __init__(self, bus, debug_enabled):
        """
        Constructor

        Args:
            bus (MessageBus): MessageBus instance
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotProvider.__init__(self, bus, debug_enabled)

    def __send_push(self, userkey, apikey, data):
        """
        Send push
        
        Params:
            userkey: user key
            apikey: user apikey
            data: data to push (PushProfile instance)

        Returns:
            bool: True if push sent successfully
        """
        try:
            conn = httplib.HTTPSConnection(self.PUSHOVER_API_URL)
            conn.request("POST", "/1/messages.json",
            urllib.urlencode({
                'user': userkey,
                'token': apikey,
                'message': data.message,
                'priority': 1, #high priority
                'title': 'Cleep message',
                'timestamp': int(time.time())
            }), { "Content-type": "application/x-www-form-urlencoded" })
            resp = conn.getresponse()
            self.logger.debug('Pushover response: %s' % resp)

            #check response
            error = None
            info = None
            if resp:
                read = resp.read()
                self.logger.debug('Pushover response content: %s' % read)
                resp = json.loads(read)

                if resp['status']==0:
                    #error occured
                    error = u','.join(resp['errors'])
                elif resp.has_key('info'):
                    #request ok but info message available
                    info = resp['info']

        except Exception as e:
            self.logger.exception('Exception when pushing message:')
            error = str(e)

        if error:
            raise CommandError(error)
        elif info:
            raise CommandInfo(info)

        return True

    def set_config(self, userkey, apikey):
        """
        Set configuration

        Params:
            userkey (string): user key
            apikey: user apikey

        Returns:
            bool: True if config saved successfully
        """
        if userkey is None or len(userkey)==0:
            raise MissingParameter('Userkey parameter is missing')
        if apikey is None or len(apikey)==0:
            raise MissingParameter('Apikey parameter is missing')

        #test config
        try:
            self.test(userkey, apikey)
        except CommandInfo as e:
            #info received but not used here
            self.logger.info('Test returns info: %s' % str(e))
        except Exception as e:
            raise CommandError(str(e))

        #save config
        config = self._get_config()
        config['userkey'] = userkey
        config['apikey'] = apikey

        return self._save_config(config)

    def test(self, userkey=None, apikey=None):
        """
        Send test push

        Params:
            userkey (string): user id
            apikey (string): user apikey

        Returns:
            bool: True if test succeed
        """
        if userkey is None or len(userkey)==0 or apikey is None or len(apikey)==0:
            config = self._get_config()
            if config['userkey'] is None or len(config['userkey'])==0 or config['apikey'] is None or len(config['apikey'])==0:
                raise CommandError('Please fill config first')

            userkey = config['userkey']
            apikey = config['apikey']

        #prepare data
        data = PushProfile()
        data.message = 'Hello this is Cleep'

        #send email
        self.__send_push(userkey, apikey, data)

        return True

    def _post(self, data):
        """
        Post data

        Params:
            data (SmsData): SmsData instance

        Returns:
            bool: True if post succeed, False otherwise
        """
        config = self._get_config()
        if config['userkey'] is None or len(config['userkey'])==0 or config['apikey'] is None or len(config['apikey'])==0:
            #not configured
            raise CommandError('Can\'t send push message because module is not configured')

        #send push
        self.__send_push(config['userkey'], config['apikey'], data)

        return True

