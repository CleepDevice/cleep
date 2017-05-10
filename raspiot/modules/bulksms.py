#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
from raspiot.utils import InvalidParameter, CommandError, MissingParameter
from raspiot.libs.smsprovider import SmsProvider, SmsData
import urllib

__all__ = ['Bulksms']


class Bulksms(SmsProvider):
    """
    BulkSms module
    @see http://developer.bulksms.com/eapi/submission/send_sms/
    """

    MODULE_CONFIG_FILE = 'bulksms.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = 'Sends you SMS alerts using BulkSms gateway.'
    MODULE_LOCKED = False
    MODULE_URL = 'https://github.com/tangb/Cleep/wiki/BulkSms'
    MODULE_TAGS = ['sms', 'alert']

    DEFAULT_CONFIG = {
        'username': None,
        'password': None,
        'phone_numbers': [],
        'credits': 0
    }

    PROVIDER_PROFILE = {}

    BULKSMS_API_URL = 'https://bulksms.vsms.net/eapi/submission/send_sms/2/2.0'
    BULKSMS_CREDITS_URL = 'https://bulksms.vsms.net/eapi/user/get_credits/1/1.1'
    BULKSMS_RESPONSE = {
        '0': 'In progress',
        '1': 'Scheduled',
        '10': 'Delivered upstream',
        '11': 'Delivered to mobile',
        '12': 'Delivered upstream unacknowledged',
        '22': 'Internal fatal error',
        '23': 'Authentication failure',
        '24': 'Data validation failed',
        '25': 'You do not have sufficient credits',
        '26': 'Upstream credits not available',
        '27': 'You have exceeded your daily quota',
        '28': 'Upstream quota exceeded',
        '29': 'Message sending cancelled',
        '31': 'Unroutable',
        '32': 'Blocked',
        '33': 'Failed: censored',
        '40': 'Temporarily unavailable',
        '50': 'Delivery failed - generic failure',
        '51': 'Delivery to phone failed',
        '52': 'Delivery to network failed',
        '53': 'Message expired',
        '54': 'Failed on remote network',
        '55': 'Failed: remotely blocked',
        '56': 'Failed: remotely censored',
        '57': 'Failed due to fault on handset',
        '60': 'Transient upstream failure',
        '61': 'Upstream status update',
        '62': 'Upstream cancel failed',
        '63': 'Queued for retry after temporary failure delivering',
        '64': 'Queued for retry after temporary failure delivering, due to fault on handset',
        '70': 'Unknown upstream status',
        '201': 'Maximum batch size exceeded'
    }

    def __init__(self, bus, debug_enabled):
        """
        Constructor
        @param bus: bus instance
        @param debug_enabled: debug status
        """
        #init
        SmsProvider.__init__(self, bus, debug_enabled)

    def set_credentials(self, username, password, phone_numbers):
        """
        Set BulkSms credentials
        @param username: username (string)
        @param password: password (string)
        @param phone_numbers: phone numbers (coma separated if many) (string)
        @return True if credentials saved successfully
        """
        if username is None or len(username)==0:
            raise MissingParameter('Username parameter is missing')
        if password is None or len(password)==0:
            raise MissingParameter('Password parameter is missing')
        if phone_numbers is None or len(phone_numbers)==0:
            raise MissingParameter('Phone_numbers parameter is missing')
        if phone_numbers.strip().find(' ')!=-1 or phone_numbers.strip().find(';')!=-1:
            raise InvalidParameter('Phone numbers must be separated by coma (,)')

        #try to get credits
        credits = self.get_credits(username, password)

        config = self._get_config()
        config['username'] = username
        config['password'] = password
        config['phone_numbers'] = phone_numbers
        config['credits'] = credits

        return self._save_config(config)

    def get_credits(self, username=None, password=None):
        """
        Return user credits
        @param username: username. If not specified use username from config
        @param password: password. If not specified use password from config
        @return remaining credits
        """
        if username is None or password is None:
            config = self._get_config()
            if config['username'] is None or len(config['username'])==0 or config['password'] is None or len(config['password'])==0:
                raise CommandError('Please fill credentials first')

            username = config['username']
            password = config['password']    

        params = urllib.urlencode({
            'username': username,
            'password': password
        })

        error = None
        credits = 0.0
        try:
            #launch request
            req = urllib.urlopen(self.BULKSMS_CREDITS_URL, params)
            res = req.read()
            self.logger.debug('Credit response: %s' % res)
            req.close()

            #parse request result
            splits = res.split('|')
            if splits[0]!='0':
                self.logger.error('Unable to retrieve credits: %s - %s' % (self.BULKSMS_RESPONSE[splits[0]], splits[1]))
                error = self.BULKSMS_RESPONSE[splits[0]]
            else:
                #get credits
                credits = float(splits[1].strip())

        except:
            self.logger.exception('Unable to retrieve credits:')
            error = 'Internal error'

        if error is not None:
            raise CommandError(error)

        return credits

    def _post(self, data):
        """
        Post data
        @param data: SmsData instance
        @return True if post succeed, False otherwise
        """
        config = self._get_config()
        params = urllib.urlencode({
            'username': config['username'],
            'password': config['password'],
            'message': data.message,
            'msisdn' : config['phone_numbers']
        })

        error = False
        try:
            #launch request
            req = urllib.urlopen(self.BULKSMS_API_URL, params)
            res = req.read()
            self.logger.debug('Send sms response: %s' % res)
            req.close()

            #parse request result
            (status_code, status_description, batch_id) = res.split('|')
            if status_code!='0':
                self.logger.error('Unable to send sms: %s - %s' % (self.BULKSMS_RESPONSE[status_code], status_description))
                error = True

        except:
            self.logger.exception('Unable to send sms:')
            error = True

        return error

