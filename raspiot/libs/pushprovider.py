#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import shutil
import logging
from raspiot.utils import InvalidParameter, MissingParameter
from raspiot.raspiot import RaspIotProvider

__all__ = ['PushProvider', 'PushData']


class PushData():
    """
    Structure to store push data
    """
    def __init__(self):
        self.version = 1

        self.title = None
        self.priority = None
        self.message = None
        self.devices = []
        self.attachment = None
        self.timestamp = None


class PushProvider(RaspIotProvider):
    """
    Base push provider class.
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
            self.register_provider('alert', 'push', self.PROVIDER_PROFILE)
    
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
        if not isinstance(data, PushData):
            raise InvalidParameter('Data must be a PushData instance')

        #call implementation
        return self._post(data)
