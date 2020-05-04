#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
import time
from raspiot.libs.internals.console import AdvancedConsole, Console

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
        #self.logger.setLevel(logging.DEBUG)
        self.interfaces = {}

    def __refresh(self):
        """
        Refresh all data
        """
        #check if refresh is needed
        if self.timestamp is not None and time.time()-self.timestamp<=self.CACHE_DURATION: # pragma no cover
            self.logger.trace('Use cached data')
            return

        pattern = r'^(?:(\w+)\s+(?:IEEE 802\.11)\s+(?:ESSID:(?:(off/any)|\"(\w+)\"))).*|(?:(\w+)\s+(no wireless extensions).*)|(?:(\w+)\s+(unassociated).*)$'
        results = self.find(u'%s 2>&1' % self._command, pattern, timeout=5.0)
        self.logger.trace('Results: %s' % results)

        entries = {}
        for _, groups in results:
            #filter None values
            groups = list(filter(None, groups))
            self.logger.trace(groups)

            #get useful values
            interface = groups[0]
            value = groups[1]
            self.logger.trace('interface=%s value=%s' % (interface, value))

            #drop lo interface
            if interface==u'lo':
                continue

            #parse values
            network = None
            if value==self.INVALID_INTERFACE:
                #drop non wifi interfaces
                continue
            elif value==self.NOT_CONNECTED or value==self.UNASSOCIATED:
                network = None
            else:
                network = value

            entries[interface] = {
                u'network': network
            }

        #save data
        self.interfaces = entries
        self.logger.debug(u'Interfaces: %s' % entries)

        #update timestamp
        self.timestamp = time.time()

    def get_interfaces(self):
        """
        Return all interfaces with wireless informations

        Returns:
            dict: dictionnary of found wifi networks::

                {
                    interface (string): {
                        network (string): connected network name
                    },
                    ...
                }

        """
        self.__refresh()

        return self.interfaces

    def set_network_to_connect_to(self, interface, network): # pragma no cover
        """
        Connect interface to specified network
        /!\ May not work as expected

        Args:
            interface (string): interface name
            network (string): network name

        Returns:
            bool: True if command succeed (may not be connected!)
        """
        res = self.command('%s "%s" essid "%s"' % (self._command, interface, network))
        self.logger.debug('Command output: %s' % res[u'stdout'])
        if self.get_last_return_code()!=0:
            self.logger.error(u'Unable to start interface %s' % interface)
            return False
        
        return True
