#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
from raspiot.raspiot import RaspIotRenderer
from raspiot.utils import CommandError, MissingParameter
from raspiot.rendering.profiles import SmsProfile
import urllib
import urllib2
import ssl

__all__ = [u'Freemobilesms']


class Freemobilesms(RaspIotRenderer):
    """
    FreemobileSms renderer

    Note:
        http://developer.bulksms.com/eapi/submission/send_sms/
    """

    MODULE_CONFIG_FILE = u'freemobilesms.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Sends you SMS alerts using french Freemobile provider.'
    MODULE_LOCKED = False
    MODULE_TAGS = [u'sms', u'alert']
    MODULE_COUNTRY = u'fr'
    MODULE_LINK = None

    DEFAULT_CONFIG = {
        u'userid': None,
        u'apikey': None
    }

    RENDERER_PROFILES = [SmsProfile()]
    RENDERER_TYPE = u'alert.sms'

    FREEMOBILESMS_API_URL = u'https://smsapi.free-mobile.fr/sendmsg'
    FREEMOBILESMS_RESPONSE = {
        200: u'Message sent',
        400: u'Missing parameter',
        402: u'Limit reached',
        403: u'Service not enabled',
        500: u'Server error'
    }

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Params:
            bootstrap (dict): bootstrap objects
            debug_enabled: debug status
        """
        #init
        RaspIotRenderer.__init__(self, bootstrap, debug_enabled)

    def set_credentials(self, userid, apikey):
        """
        Set FreemobileSms credentials

        Params:
            userid: userid (string)
            apikey: apikey (string)

        Returns:
            bool: True if credentials saved successfully
        """
        if userid is None or len(userid)==0:
            raise MissingParameter(u'Userid parameter is missing')
        if apikey is None or len(apikey)==0:
            raise MissingParameter(u'Apikey parameter is missing')

        #test credentials
        if not self.test(userid, apikey):
            raise CommandError(u'Unable to send test')

        #save config
        config = self._get_config()
        config[u'userid'] = userid
        config[u'apikey'] = apikey

        return self._save_config(config)

    def test(self, userid=None, apikey=None):
        """
        Send test sms

        Params:
            userid: userid. If not specified use userid from config
            apikey: apikey. If not specified use apikey from config

        Returns:
            bool: True if test succeed
        """
        if userid is None or apikey is None:
            config = self._get_config()
            if config[u'userid'] is None or len(config[u'userid'])==0 or config[u'apikey'] is None or len(config[u'apikey'])==0:
                raise CommandError(u'Please fill credentials first')

            userid = config[u'userid']
            apikey = config[u'apikey']    

        params = urllib.urlencode({
            u'user': userid,
            u'pass': apikey,
            u'msg': u'Hello this is Cleep'
        })
        self.logger.debug(u'Request params: %s' % params)

        error = None
        try:
            #launch request
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            req = urllib2.urlopen(u'%s?%s' % (self.FREEMOBILESMS_API_URL, params), context=context)
            res = req.read()
            status = req.getcode()
            self.logger.debug(u'Test response: %s [%s]' % (res, status))
            req.close()

            #parse request result
            if status!=200:
                self.logger.error(u'Unable to test: %s [%s]' % (self.FREEMOBILESMS_RESPONSE[status], status))
                error = self.FREEMOBILESMS_RESPONSE[status]

        except:
            self.logger.exception(u'Unable to test:')
            error = u'Internal error'

        if error is not None:
            raise CommandError(error)

        return True

    def _render(self, profile):
        """
        Render profile

        Params:
            profile (SmsProfile): SmsProfile instance

        Returns:
            bool: True if render succeed, False otherwise
        """
        config = self._get_config()
        params = urllib.urlencode({
            u'user': config[u'userid'],
            u'pass': config[u'apikey'],
            u'msg': profile.message
        })

        error = False
        try:
            #launch request
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            req = urllib2.urlopen(u'%s?%s' % (self.FREEMOBILESMS_API_URL, params), context=context)
            res = req.read()
            status = req.getcode()
            self.logger.debug(u'Send sms response: %s [%s]' % (res, status))
            req.close()

            #parse request result
            if status!=200:
                self.logger.error(u'Unable to send sms: %s [%s]' % (self.FREEMOBILESMS_RESPONSE[status], status))
                error = True

        except:
            self.logger.exception(u'Unable to send sms:')
            error = True

        return error

