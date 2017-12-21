#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
from libs.console import AdvancedConsole, Console
import time

class IwList(AdvancedConsole):
    """
    Command /sbin/iwlist helper
    """

    CACHE_DURATION = 2.0

    def __init__(self):
        """
        Constructor
        """
        AdvancedConsole.__init__(self)

        #members
        self._command = u'/sbin/iwlist %s scan'
        self.timestamp = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.networks = {}
        self.error = False

    def __refresh(self, interface):
        """
        Refresh all data

        Args:
            interface (string): interface to scan
        """
        #check if refresh is needed
        if self.timestamp is not None and time.time()-self.timestamp<=self.CACHE_DURATION:
            self.logger.debug('Don\'t refresh')
            return

        entries = {}
        results, error = self.find(self._command % interface, r'ESSID:\"(.*?)\"|IE:\s*(.*)|Encryption key:(.*)|Signal level=(\d{1,3})/100', timeout=15.0)

        #handle invalid interface for wifi scanning
        if error:
            self.networks = {}
            self.error = True
            return

        current_entry = None
        for group, groups in results:
            #filter None values
            groups = filter(None, groups)

            if group.startswith(u'ESSID'):
                current_entry = {
                    u'interface': interface,
                    u'network': groups[0],
                    u'encryption': None,
                    u'signal_level': 0,
                    u'wpa2': False,
                    u'wpa': False,
                    u'encryption_key': None
                }
                entries[groups[0]] = current_entry
            elif group.startswith(u'IE') and current_entry is not None and groups[0].lower().find(u'wpa2'):
                current_entry[u'wpa2'] = True
            elif group.startswith(u'IE') and current_entry is not None and groups[0].lower().find(u'wpa'):
                current_entry[u'wpa'] = True
            elif group.startswith(u'Encryption key') and current_entry is not None:
                current_entry[u'encryption_key'] = groups[0]
            elif group.startswith(u'Signal level') and current_entry is not None:
                if groups[0].isdigit():
                    current_entry[u'signal_level'] = float(groups[0])
                else:
                    current_entry[u'signal_level'] = groups[0]

        #compute encryption value
        for network in entries:
            if entries[network][u'wpa2']:
                entries[network][u'encryption'] = WpaSupplicantConf.ENCRYPTION_TYPE_WPA2
            elif entries[network][u'wpa']:
                entries[network][u'encryption'] = WpaSupplicantConf.ENCRYPTION_TYPE_WPA
            elif entries[network][u'encryption_key'].lower()=='on':
                entries[network][u'encryption'] = WpaSupplicantConf.ENCRYPTION_TYPE_WEP
            elif entries[network][u'encryption_key'].lower()=='off':
                entries[network][u'encryption'] = WpaSupplicantConf.ENCRYPTION_TYPE_UNSECURED
            else:
                entries[network][u'encryption'] = WpaSupplicantConf.ENCRYPTION_TYPE_UNKNOWN
            del entries[network][u'wpa2']
            del entries[network][u'wpa']
            del entries[network][u'encryption_key']
        
        #save networks and error
        self.networks = entries
        self.error = False

        #update timestamp
        self.timestamp = time.time()

    def has_error(self):
        """
        Return True if error occured
        
        Return:
            bool: True if error, False otherwise
        """
        return self.error

    def get_networks(self, interface):
        """
        Return all wifi networks scanned

        Args:
            interface (string): interface name

        Returns:
            dict: dictionnary of found wifi networks::
                {
                    network: {
                        interface (string): interface scanned
                        network (string): wifi network name
                        encryption (string): encryption type (TODO)
                        signal_level (float): wifi signal level
                    },
                    ...
                }
            bool: True if interface is not able to scan wifi
        """
        self.__refresh(interface)

        return self.networks

