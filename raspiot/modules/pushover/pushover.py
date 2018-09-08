#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
from raspiot.raspiot import RaspIotRenderer
from raspiot.utils import CommandError, MissingParameter, CommandInfo
from raspiot.profiles import PushProfile 
import urllib
import httplib
import json
import time

__all__ = [u'Pushover']


class Pushover(RaspIotRenderer):
    """
    Pushover module
    Used to send push notifications to mobile devices
    """
    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'1.0.0'
    MODULE_PRICE = 0
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Sends you push alerts using Pushover service.'
    MODULE_LOCKED = False
    MODULE_TAGS = [u'push', u'alert']
    MODULE_COUNTRY = None
    MODULE_URLINFO = None
    MODULE_URLHELP = None
    MODULE_URLSITE = None
    MODULE_URLBUGS = None

    MODULE_CONFIG_FILE = u'pushover.conf'
    DEFAULT_CONFIG = {
        u'apikey': None,
        u'userkey': None
    }
    PUSHOVER_API_URL = u'api.pushover.net:443'

    RENDERER_PROFILES = [PushProfile]
    RENDERER_TYPE = u'alert.push'

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotRenderer.__init__(self, bootstrap, debug_enabled)

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
            conn.request(u'POST', u'/1/messages.json',
            urllib.urlencode({
                u'user': userkey,
                u'token': apikey,
                u'message': data.message,
                u'priority': 1, #high priority
                u'title': u'Cleep message',
                u'timestamp': int(time.time())
            }), { u'Content-type': u'application/x-www-form-urlencoded'})
            resp = conn.getresponse()
            self.logger.debug(u'Pushover response: %s' % resp)

            #check response
            error = None
            info = None
            if resp:
                read = resp.read()
                self.logger.debug(u'Pushover response content: %s' % read)
                resp = json.loads(read)

                if not resp:
                    #no response
                    error = u'No response'
                elif resp[u'status']==0:
                    #error occured
                    error = u','.join(resp[u'errors'])
                elif resp.has_key(u'info'):
                    #request ok but info message available
                    info = resp[u'info']

        except Exception as e:
            self.logger.exception(u'Exception when pushing message:')
            error = unicode(e)

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
            raise MissingParameter(u'Userkey parameter is missing')
        if apikey is None or len(apikey)==0:
            raise MissingParameter(u'Apikey parameter is missing')

        #test config
        try:
            self.test(userkey, apikey)
        except CommandInfo as e:
            #info received but not used here
            self.logger.info(u'Test returns info: %s' % unicode(e))
        except Exception as e:
            raise CommandError(unicode(e))

        #save config
        return self._update_config({
            u'userkey': userkey,
            u'apikey': apikey
        })

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
            if config[u'userkey'] is None or len(config[u'userkey'])==0 or config[u'apikey'] is None or len(config[u'apikey'])==0:
                raise CommandError(u'Please fill config first')

            userkey = config[u'userkey']
            apikey = config[u'apikey']

        #prepare data
        data = PushProfile()
        data.message = u'Hello this is a push test from Cleep'

        #send push
        self.__send_push(userkey, apikey, data)

        return True

    def _render(self, profile):
        """
        Render profile

        Params:
            profile (PushProfile): PushProfile instance

        Returns:
            bool: True if post succeed, False otherwise
        """
        config = self._get_config()
        if config[u'userkey'] is None or len(config[u'userkey'])==0 or config[u'apikey'] is None or len(config[u'apikey'])==0:
            #not configured
            raise CommandError(u'Can\'t send push message because module is not configured')

        #send push
        self.__send_push(config[u'userkey'], config[u'apikey'], profile)

        return True

