#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
from raspiot.raspiot import RaspIotRenderer
from raspiot.utils import InvalidParameter, CommandError, MissingParameter
from raspiot.profiles import SmsProfile
import urllib

__all__ = ['Bulksms']


class Bulksms(RaspIotRenderer):
    """
    BulkSms module

    Note:
        see http://developer.bulksms.com/eapi/submission/send_sms/
    """
    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'1.0.0'
    MODULE_PRICE = 0
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Sends you SMS alerts using BulkSms gateway.'
    MODULE_LOCKED = False
    MODULE_TAGS = [u'sms', u'alert']
    MODULE_COUNTRY = None
    MODULE_URLINFO = u'https://github.com/tangb/Raspiot/wiki/Bulksms'
    MODULE_URLHELP = None
    MODULE_URLSITE = None
    MODULE_URLBUGS = None

    MODULE_CONFIG_FILE = u'bulksms.conf'
    DEFAULT_CONFIG = {
        u'username': None,
        u'password': None,
        u'phone_numbers': [],
        u'credits': 0
    }

    RENDERER_PROFILES = [SmsProfile]
    RENDERER_TYPE = u'alert.sms'

    BULKSMS_API_URL = u'https://bulksms.vsms.net/eapi/submission/send_sms/2/2.0'
    BULKSMS_CREDITS_URL = u'https://bulksms.vsms.net/eapi/user/get_credits/1/1.1'
    BULKSMS_RESPONSE = {
        u'0': u'In progress',
        u'1': u'Scheduled',
        u'10': u'Delivered upstream',
        u'11': u'Delivered to mobile',
        u'12': u'Delivered upstream unacknowledged',
        u'22': u'Internal fatal error',
        u'23': u'Authentication failure',
        u'24': u'Data validation failed',
        u'25': u'You do not have sufficient credits',
        u'26': u'Upstream credits not available',
        u'27': u'You have exceeded your daily quota',
        u'28': u'Upstream quota exceeded',
        u'29': u'Message sending cancelled',
        u'31': u'Unroutable',
        u'32': u'Blocked',
        u'33': u'Failed: censored',
        u'40': u'Temporarily unavailable',
        u'50': u'Delivery failed - generic failure',
        u'51': u'Delivery to phone failed',
        u'52': u'Delivery to network failed',
        u'53': u'Message expired',
        u'54': u'Failed on remote network',
        u'55': u'Failed: remotely blocked',
        u'56': u'Failed: remotely censored',
        u'57': u'Failed due to fault on handset',
        u'60': u'Transient upstream failure',
        u'61': u'Upstream status update',
        u'62': u'Upstream cancel failed',
        u'63': u'Queued for retry after temporary failure delivering',
        u'64': u'Queued for retry after temporary failure delivering, due to fault on handset',
        u'70': u'Unknown upstream status',
        u'201': u'Maximum batch size exceeded'
    }

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotRenderer.__init__(self, bootstrap, debug_enabled)

    def set_credentials(self, username, password, phone_numbers):
        """
        Set BulkSms credentials

        Args:
            username (string): username
            password (string): password
            phone_numbers (string): phone numbers (coma separated if many)

        Returns:
            bool: True if credentials saved successfully
        """
        if username is None or len(username)==0:
            raise MissingParameter(u'Username parameter is missing')
        if password is None or len(password)==0:
            raise MissingParameter(u'Password parameter is missing')
        if phone_numbers is None or len(phone_numbers)==0:
            raise MissingParameter(u'Phone_numbers parameter is missing')
        if phone_numbers.strip().find(u' ')!=-1 or phone_numbers.strip().find(u';')!=-1:
            raise InvalidParameter(u'Phone numbers must be separated by coma (,)')

        #try to get credits
        credits = self.get_credits(username, password)

        return self._update_config({
            u'username': username,
            u'password': password,
            u'phone_numbers': phone_numbers,
            u'credits': credits
        })

    def get_credits(self, username=None, password=None):
        """
        Return user credits

        Args:
            username (string): username. If not specified use username from config
            password (string): password. If not specified use password from config
        
        Returns:
            int: remaining credits
        """
        if username is None or password is None:
            config = self._get_config()
            if config[u'username'] is None or len(config[u'username'])==0 or config[u'password'] is None or len(config[u'password'])==0:
                raise CommandError(u'Please fill credentials first')

            username = config[u'username']
            password = config[u'password']    

        params = urllib.urlencode({
            u'username': username,
            u'password': password
        })

        error = None
        credits = 0.0
        try:
            #launch request
            req = urllib.urlopen(self.BULKSMS_CREDITS_URL, params)
            res = req.read()
            self.logger.debug(u'Credit response: %s' % res)
            req.close()

            #parse request result
            splits = res.split(u'|')
            if splits[0]!=u'0':
                self.logger.error(u'Unable to retrieve credits: %s - %s' % (self.BULKSMS_RESPONSE[splits[0]], splits[1]))
                error = self.BULKSMS_RESPONSE[splits[0]]
            else:
                #get credits
                credits = float(splits[1].strip())

        except:
            self.logger.exception(u'Unable to retrieve credits:')
            error = u'Internal error'

        if error is not None:
            raise CommandError(error)

        return credits

    def _render(self, profile):
        """
        Render profile

        Args:
            profile (SmsProfile): SmsProfile instance

        Returns:
            bool: True if post succeed, False otherwise
        """
        config = self._get_config()
        params = urllib.urlencode({
            u'username': config[u'username'],
            u'password': config[u'password'],
            u'message': profile.message,
            u'msisdn' : config[u'phone_numbers']
        })

        error = False
        try:
            #launch request
            req = urllib.urlopen(self.BULKSMS_API_URL, params)
            res = req.read()
            self.logger.debug(u'Send sms response: %s' % res)
            req.close()

            #parse request result
            (status_code, status_description, batch_id) = res.split('|')
            if status_code!=u'0':
                self.logger.error(u'Unable to send sms: %s - %s' % (self.BULKSMS_RESPONSE[status_code], status_description))
                error = True

        except:
            self.logger.exception(u'Unable to send sms:')
            error = True

        return error

