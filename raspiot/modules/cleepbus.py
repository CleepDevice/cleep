#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.raspiot import RaspIotModule
import raspiot
import time

__all__ = [u'Cleepbus']


class Cleepbus(RaspIotModule):

    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Add your device to Cleep local network'
    MODULE_LOCKED = True
    MODULE_URL = None
    MODULE_TAGS = ['bus']
    MODULE_COUNTRY = 'any'

    def __init__(self, bus, debug_enabled):
        """
        Constructor

        Args:
            bus (MessageBus): MessageBus instance
            debug_enabled (bool): flag to set debug level to logger
        """
        RaspIotModule.__init__(self, bus, debug_enabled)

        #members
        self.bus = PyreBus(debug_enabled, None)

    def _start(self):
        """
        Start module
        """
        if self.bus:
            version = '0.0.0'
            hostname = 'hostname'
            port = 80
            ssl = False
            self.bus.start(version, hostname, port, ssl)

    def _stop(self):
        """
        Stop module
        """
        #stop bus
        if self.bus:
            self.bus.stop()

    def get_module_devices(self):
        """

        Returns:
            dict: devices
        """
        #TODO return list of online devices
        pass

    def event_received(self, event):
        """
        Watch for specific event

        Args:
            event (MessageRequest): event data
        """
        #handle received event and transfer it to external buf if necessary
        pass


