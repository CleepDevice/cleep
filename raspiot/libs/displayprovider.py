#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import shutil
import logging
from raspiot.utils import InvalidParameter, MissingParameter
from raspiot.raspiot import RaspIotProvider

__all__ = ['DisplayProvider', 'DisplayData']


class DisplayData():
    """
    Base display data class
    Handle base data to display a message on screen
    """
    def __init__(self):
        """
        Constructor
        """
        self.message = None


class DisplayProvider(RaspIotProvider):
    """
    Base display provider class.
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
            self.register_provider('display', self.__class__.__name__, self.PROVIDER_PROFILES)
    
    def post(self, data):
        """ 
        Data posted to provider

        Args:
            data (Data): data to post

        Raises:
            MissingParameter, InvalidParameter
        """
        #check params
        if data is None:
            raise MissingParameter('Data parameter is missing')
        if not isinstance(data, DisplayData):
            raise InvalidParameter('Data must be a DisplayData instance')

        #call implementation
        return self._post(data)

