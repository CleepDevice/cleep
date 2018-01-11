#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
import time
from raspiot.libs.console import AdvancedConsole, Console

class Iwconfig(AdvancedConsole):
    """
    Command /sbin/iwlist helper
    """

    CACHE_DURATION = 2.0
    NOT_CONNECTED = u'off/any'
    UNASSOCIATED = u'unassociated'
    INVALID_INTERFACE = u'no wireless extensions'

    def __init__(self):
        """
        Constructor
        """
        AdvancedConsole.__init__(self)

        #members
        self._command = u'/sbin/iwconfig'
        self.timestamp = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        self.interfaces = {}

    def __refresh(self):
        """
        Refresh all data
        """
        #check if refresh is needed
        if self.timestamp is not None and time.time()-self.timestamp<=self.CACHE_DURATION:
            self.logger.debug('Don\'t refresh')
            return

        results = self.find(u'%s 2>&1' % self._command, r'^\s*(.*?)\s+(:?(?:(unassociated))(.*)|(?:.*ESSID:)(.*)|(no wireless extensions)).*$', timeout=5.0)
        self.logger.debug(results)

        current_entry = None
        entries = {}
        for group, groups in results:
            #filter None values
            groups = filter(None, groups)

            #get useful values
            interface = groups[0]
            value = groups[2]
            self.logger.debug('interface=%s value=%s' % (interface, value))

            #drop lo interface
            if interface==u'lo':
                continue

            #parse values
            network = None
            if value==self.INVALID_INTERFACE:
                #drop non wifi interfaces
                continue
            elif value==self.NOT_CONNECTED or self.UNASSOCIATED:
                network = None
            else:
                wifi_interface = True
                network = value.replace('"', '').replace('\'', '').strip()

            entries[interface] = {
                u'network': network
            }

        #save data
        self.interfaces = entries

        #update timestamp
        self.timestamp = time.time()

    def get_interfaces(self):
        """
        Return all interfaces with wireless informations

        Returns:
            dict: dictionnary of found wifi networks::
                {
                    interface: {
                        network (string): connected network name
                    },
                    ...
                }
        """
        self.__refresh()

        return self.interfaces

    def set_network_to_connect_to(self, interface, network):
        """
        Connect interface to specified network

        Args:
            interface (string): interface name
            network (string): network name

        Return:
            bool: True if command succeed (not connection!)
        """
        res = self.command('%s "%s" essid "%s"' % (self._command, interface, network))
        self.logger.debug('Command output: %s' % res[u'stdout'])
        if res[u'error'] or res[u'killed']:
            self.logger.error(u'Unable to start interface %s' % interface)
            return False
        
        return True

