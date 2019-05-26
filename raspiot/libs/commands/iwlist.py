#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
import time
from raspiot.libs.internals.console import AdvancedConsole, Console
from raspiot.libs.configs.wpasupplicantconf import WpaSupplicantConf
import raspiot.libs.internals.tools as Tools

class Iwlist(AdvancedConsole):
    """
    Command /sbin/iwlist helper
    """

    CACHE_DURATION = 2.0

    FREQ_2_4GHZ = u'2.4GHz'
    FREQ_5GHZ = u'5GHz'

    def __init__(self):
        """
        Constructor
        """
        AdvancedConsole.__init__(self)

        #members
        self._command = u'/sbin/iwlist %s scan'
        self.timestamp = None
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)
        self.networks = {}
        self.error = False
        self.__last_scanned_interface = None

    def __refresh(self, interface):
        """
        Refresh all data

        Args:
            interface (string): interface to scan
        """
        #check if refresh is needed
        if self.timestamp is not None and time.time()-self.timestamp<=self.CACHE_DURATION:
            self.logger.trace(u'Don\'t refresh')
            return

        self.__last_scanned_interface = interface
        results = self.find(self._command % interface, r'Cell \d+|ESSID:\"(.*?)\"|IE:\s*(.*)|Encryption key:(.*)|Signal level=(\d{1,3})/100|Signal level=(-\d+) dBm|Frequency:(\d+\.\d+) GHz', timeout=15.0)
        #self.logger.trace(u'Results: %s' % results)

        #handle invalid interface for wifi scanning
        if len(results)==0 and self.get_last_return_code()!=0:
            self.networks = {}
            self.error = True
            return

        current_entry = None
        entries = {}
        #frequencies = {}
        frequency = None
        for group, groups in results:
            #filter None values
            groups = filter(lambda v: v is not None, groups)

            if group.startswith(u'Cell'):
                #create new empty entry
                current_entry = {
                    u'interface': interface,
                    u'network': None,
                    u'encryption': None,
                    u'signallevel': 0,
                    u'wpa2': False,
                    u'wpa': False,
                    u'encryption_key': None,
                    u'frequencies': []
                }

            elif group.startswith(u'ESSID'):
                #network
                if len(groups[0])>0 and groups[0] not in entries:
                    #new network detected, store item in final entries list
                    current_entry[u'network'] = groups[0]
                    if frequency is not None:
                        current_entry[u'frequencies'].append(frequency)
                    entries[groups[0]] = current_entry

                elif len(groups[0])>0 and frequency is not None:
                    #append frequency on existing entry
                    if frequency not in entries[groups[0]][u'frequencies']:
                        entries[groups[0]][u'frequencies'].append(frequency)

                #reset frequency
                frequency = None

            elif group.startswith(u'IE') and current_entry is not None and groups[0].lower().find(u'wpa2')>=0:
                #wpa2
                current_entry[u'wpa2'] = True

            elif group.startswith(u'IE') and current_entry is not None and groups[0].lower().find(u'wpa')>=0:
                #wpa
                current_entry[u'wpa'] = True

            elif group.startswith(u'Encryption key') and current_entry is not None:
                #encryption key (wep or unsecured)
                current_entry[u'encryption_key'] = groups[0]

            elif group.startswith(u'Frequency'):
                #frequency
                if groups[0].startswith(u'2.'):
                    frequency = self.FREQ_2_4GHZ
                elif groups[0].startswith(u'5.'):
                    frequency = self.FREQ_5GHZ

            elif group.startswith(u'Signal level') and current_entry is not None:
                #signal level
                if groups[0].isdigit():
                    try:
                        current_entry[u'signallevel'] = float(groups[0])
                    except:
                        current_entry[u'signallevel'] = 0
                elif groups[0].startswith(u'-'):
                    try:
                        current_entry[u'signallevel'] = Tools.dbm_to_percent(int(groups[0]))
                    except:
                        current_entry[u'signallevel'] = 0
                else:
                    current_entry[u'signallevel'] = groups[0]

        #log entries
        self.logger.debug('entries: %s' % entries)

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
                        signallevel (float): wifi signal level
                    },
                    ...
                }
            bool: True if interface is not able to scan wifi
        """
        self.__refresh(interface)

        return self.networks

