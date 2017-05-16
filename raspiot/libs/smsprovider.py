#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import shutil
import logging
from raspiot.utils import InvalidParameter, MissingParameter
from raspiot.raspiot import RaspIotProvider

__all__ = ['SmsProvider', 'SmsData']


class SmsData():
    """
    Structure to store SMS data
    """
    def __init__(self):
        self.message = None


class SmsProvider(RaspIotProvider):
    """
    Base sms provider class.
    Register provider to inventory at startup
    """

    def __init__(self, bus, debug_enabled):
        """
        Constructor

        Args:
            bus (MessageBus): bus instance
            debug_enabled (bool): debug status
        """
        #init
        RaspIotProvider.__init__(self, bus, debug_enabled)

    def event_received(self, event):
        """ 
        Event received from bus

        Args:
            event (MessageRequest): received event
        """
        if event['event']=='system.application.ready':
            #application is ready, register provider
            self.register_provider('alert', 'sms', self.PROVIDER_CAPABILITIES)
    
    def post(self, data):
        """ 
        Data posted to provider

        Args:
            data (EmailData): data to post

        Raises:
            MissingParameter, InvalidParameter
        """
        #check params
        if data is None:
            raise MissingParameter('Data parameter is missing')
        if not isinstance(data, SmsData):
            raise InvalidParameter('Data must be a SmsData instance')

        #call implementation
        return self._post(data)

