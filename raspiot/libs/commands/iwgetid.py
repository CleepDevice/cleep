#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
import time
from raspiot.libs.internals.console import AdvancedConsole, Console

class Iwgetid(AdvancedConsole):
    """
    Command /sbin/iwgetid helper
    """

    CACHE_DURATION = 2.0

    def __init__(self):
        """
        Constructor
        """
        AdvancedConsole.__init__(self)

        #members
        self._command = u'/sbin/iwgetid'
        self.timestamp = None
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)
        self.connections = {}

    def __refresh(self):
        """
        Refresh all data
        """
        #check if refresh is needed
        if self.timestamp is not None and time.time()-self.timestamp<=self.CACHE_DURATION:
            self.logger.debug('Don\'t refresh')
            return

        results = self.find(u'%s' % self._command, r'^(.*?)\s+ESSID:\"(.*)\"$')
        self.logger.debug(results)

        current_entry = None
        entries = {}
        for group, groups in results:
            #filter None values
            groups = filter(None, groups)

            #get useful values
            interface = groups[0]
            network = groups[1]
            self.logger.debug('interface=%s network=%s' % (interface, network))

            entries[interface] = {
                u'network': network
            }

        #save data
        self.connections = entries

        #update timestamp
        self.timestamp = time.time()

    def get_connections(self):
        """
        Return all wifi connections

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

        return self.connections

