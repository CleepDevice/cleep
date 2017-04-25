#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
from raspiot.utils import InvalidParameter
from raspiot.raspiot import RaspIotMod

__all__ = ['NEtwork']

#https://www.raspberrypi.org/documentation/configuration/

class Network(RaspIotMod):

    #MODULE_CONFIG_FILE = 'sounds.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = 'Network configuration helper'
    MODULE_LOCKED = True
    MODULE_URL = None
    MODULE_TAGS = []

    def __init__(self, bus, debug_enabled):
        """
        Constructor
        @param bus: bus instance
        @param debug_enabled: debug status
        """
        #init
        RaspIotMod.__init__(self, bus, debug_enabled)

    def set_configuration(self):
        """
        """
        pass

    def scan_wireless_networks(self):
        """
        Scan wireless networks
        """
        


