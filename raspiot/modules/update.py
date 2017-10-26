#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.raspiot import RaspIotModule
import time
from raspiot.libs.download import Download

__all__ = [u'Update']


class Update(RaspIotModule):

    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Keep your device up-to-date'
    MODULE_LOCKED = False
    MODULE_URL = None
    MODULE_TAGS = [u'update', u'raspiot']
    MODULE_COUNTRY = u'any'

    def __init__(self, bus, debug_enabled, join_event):
        """
        Constructor

        Args:
            bus (MessageBus): MessageBus instance
            debug_enabled (bool): flag to set debug level to logger
        """
        RaspIotModule.__init__(self, bus, debug_enabled, join_event)

        #members
        self.__updates = None
        self.last_check = None

    def _custom_process(self):
        """
        Custom process
        """
        if self.__updates:
            #download file
            pass

    def check_updates(self):
        """
        Check for available updates

        Return:
            dict: update informations
        """
        self.last_check = int(time.time())

    def event_received(self, event):
        """
        Event received
        """
        if event[u'event']==u'system.time.now' and event[u'params'][u'hour']==12 and event[u'params'][u'minute']==0:
            #check updates at noon
            self.__updates = self.check_updates()

