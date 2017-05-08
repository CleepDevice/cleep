#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
from raspiot.utils import CommandError, MissingParameter
from raspiot.libs.smsprovider import SmsProvider, SmsData
import urllib
import urllib2
import ssl

__all__ = ['Freemobilesms']


class Freemobilesms(SmsProvider):
    """
    FreemobileSms module
    @see http://developer.bulksms.com/eapi/submission/send_sms/
    """

    MODULE_CONFIG_FILE = 'freemobilesms.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = 'Sends you SMS alerts using french Freemobile provider.'
    MODULE_LOCKED = False
    MODULE_URL = 'https://github.com/tangb/Cleep/wiki/FreemobileSms'
    MODULE_TAGS = []

    DEFAULT_CONFIG = {
        'userid': None,
        'apikey': None
    }

    PROVIDER_CAPABILITIES = {}

    FREEMOBILESMS_API_URL = 'https://smsapi.free-mobile.fr/sendmsg'
    FREEMOBILESMS_RESPONSE = {
        200: 'Message sent',
        400: 'Missing parameter',
        402: 'Limit reached',
        403: 'Service not enabled',
        500: 'Server error'
    }

    def __init__(self, bus, debug_enabled):
        """
        Constructor
        @param bus: bus instance
        @param debug_enabled: debug status
        """
        #init
        SmsProvider.__init__(self, bus, debug_enabled)

    def set_credentials(self, userid, apikey):
        """
        Set FreemobileSms credentials
        @param userid: userid (string)
        @param apikey: apikey (string)
        @return True if credentials saved successfully
        """
        if userid is None or len(userid)==0:
            raise MissingParameter('Userid parameter is missing')
        if apikey is None or len(apikey)==0:
            raise MissingParameter('Apikey parameter is missing')

        #test credentials
        if not self.test(userid, apikey):
            raise CommandError('Unable to send test')

        #save config
        config = self._get_config()
        config['userid'] = userid
        config['apikey'] = apikey

        return self._save_config(config)

    def test(self, userid=None, apikey=None):
        """
        Send test sms
        @param userid: userid. If not specified use userid from config
        @param apikey: apikey. If not specified use apikey from config
        @return True if test succeed
        """
        if userid is None or apikey is None:
            config = self._get_config()
            if config['userid'] is None or len(config['userid'])==0 or config['apikey'] is None or len(config['apikey'])==0:
                raise CommandError('Please fill credentials first')

            userid = config['userid']
            apikey = config['apikey']    

        params = urllib.urlencode({
            'user': userid,
            'pass': apikey,
            'msg': 'Hello this is Cleep'
        })
        self.logger.debug('Request params: %s' % params)

        error = None
        try:
            #launch request
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            req = urllib2.urlopen('%s?%s' % (self.FREEMOBILESMS_API_URL, params), context=context)
            res = req.read()
            status = req.getcode()
            self.logger.debug('Test response: %s [%s]' % (res, status))
            req.close()

            #parse request result
            if status!=200:
                self.logger.error('Unable to test: %s [%s]' % (self.FREEMOBILESMS_RESPONSE[status], status))
                error = self.FREEMOBILESMS_RESPONSE[status]

        except:
            self.logger.exception('Unable to test:')
            error = 'Internal error'

        if error is not None:
            raise CommandError(error)

        return True

    def _post(self, data):
        """
        Post data
        @param data: SmsData instance
        @return True if post succeed, False otherwise
        """
        config = self._get_config()
        params = urllib.urlencode({
            'user': config['userid'],
            'pass': config['apikey'],
            'msg': data.message
        })

        error = False
        try:
            #launch request
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            req = urllib2.urlopen('%s?%s' % (self.FREEMOBILESMS_API_URL, params), context=context)
            res = req.read()
            status = req.getcode()
            self.logger.debug('Send sms response: %s [%s]' % (res, status))
            req.close()

            #parse request result
            if status!=200:
                self.logger.error('Unable to send sms: %s [%s]' % (self.FREEMOBILESMS_RESPONSE[status], status))
                error = True

        except:
            self.logger.exception('Unable to send sms:')
            error = True

        return error

