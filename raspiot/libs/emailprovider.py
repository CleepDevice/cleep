#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import shutil
import logging
from raspiot.utils import InvalidParameter, MissingParameter
from raspiot.raspiot import RaspIotProvider

__all__ = ['EmailProvider', 'EmailData']


class EmailData():
    """
    Structure to store email data
    """
    def __init__(self):
        self.subject = None
        self.message = None
        self.recipients = []
        self.attachment = None


class EmailProvider(RaspIotProvider):
    """
    Base email provider class.
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
            self.register_provider('alert', 'email', self.PROVIDER_PROFILE)
    
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
        if not isinstance(data, EmailData):
            raise InvalidParameter('Data must be a EmailData instance')

        #call implementation
        return self._post(data)

