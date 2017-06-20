#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
from raspiot.libs.config import Config
from console import Console
import os
import re

class WpaSupplicantConf(Config):
    """
    Helper class to update and read /etc/wpa_supplicant/wpa_supplicant.conf file

    Infos:
        https://w1.fi/cgit/hostap/plain/wpa_supplicant/wpa_supplicant.conf
    """

    CONF = u'/etc/wpa_supplicant/wpa_supplicant.conf'

    ENCRYPTION_TYPE_WPA = u'wpa'
    ENCRYPTION_TYPE_WPA2 = u'wpa2'
    ENCRYPTION_TYPE_WEP = u'wep'
    ENCRYPTION_TYPE_UNSECURED = u'unsecured'
    ENCRYPTION_TYPE_UNKNOWN = u'unknown'
    ENCRYPTION_TYPES = [ENCRYPTION_TYPE_WPA, ENCRYPTION_TYPE_WPA2, ENCRYPTION_TYPE_WEP, ENCRYPTION_TYPE_UNSECURED, ENCRYPTION_TYPE_UNKNOWN]

    def __init__(self, backup=True):
        """
        Constructor
        """
        Config.__init__(self, self.CONF, None, backup)

    def get_networks(self):
        """
        Return networks found in conf file
        """
        networks = {}
        entries = []

        results = self.find(r'network\s*=\s*\{\s*(.*?)\s*\}', re.UNICODE | re.DOTALL)
        for group, groups in results:
            #prepare values
            ssid = None

            #filter none values
            groups = filter(None, groups)

            #create new entry
            current_entry = {
                u'group': group,
                u'network': None,
                u'hidden': False,
                u'encryption': None
            }
            entries.append(current_entry)

            #fill entry
            pattern = r'^\s*(\w+)=(.*?)\s*$'
            for content in groups:
                sub_results = self.find_in_string(pattern, content, re.UNICODE | re.MULTILINE)
                
                #filter none values
                for sub_group, sub_groups in sub_results:
                    if len(sub_groups)==2:
                        if sub_groups[0].startswith(u'ssid'):
                            current_entry[u'network'] = sub_groups[1].replace('"','').replace('\'', '')
                        if sub_groups[0].startswith(u'scan_ssid'):
                            if sub_groups[1] is not None and sub_groups[1].isdigit() and sub_groups[1]=='1':
                                current_entry[u'hidden'] = True
                        if sub_groups[0].startswith(u'key_mgmt'):
                            if sub_groups[1]==u'WPA-PSK':
                                current_entry[u'encryption'] = self.ENCRYPTION_TYPE_WPA2
                            elif sub_groups[1]==u'NONE':
                                current_entry[u'encryption'] = self.ENCRYPTION_TYPE_WEP

                    else:
                        #invalid content, drop this item
                        continue

        for entry in entries:
            networks[entry[u'network']] = entry

        return networks

    def get_network(self, network):
        """
        Get network config

        Args:
            network (string): network name

        Returns:
            dict: network config
            None: if network is not found
        """
        networks = self.get_networks()

        if networks.has_key(network):
            return networks[network]

        return None

    def delete_network(self, network):
        """
        Delete network from config

        Args:
            network (string): network name

        Returns:
            bool: True if network deleted, False otherwise
        """
        #check params
        if network is None or len(network)==0:
            raise MissingParameter(u'Network parameter is missing')

        #check if network exists
        network_ = self.get_network(network)
        if network_ is None:
            return False

        return self.remove(network_[u'group'])

    def add_network(self, network, encryption, password, hidden=False):
        """
        Add new network in config file
        Password is automatically encrypted using wpa_passphrase
        
        Args:
            network (string): network name (ssid)
            encryption (wpa|wpa2|wpe|unsecured): type of network
            password (string): network password
            hidden (bool): hidden network flag

        Raises:
            MissingParameter, InvalidParameter
        """
        #check params
        if network is None or len(network)==0:
            raise MissingParameter(u'Network parameter is missing')
        if encryption is None or len(encryption)==0:
            raise MissingParameter(u'Encryption parameter is missing')
        if encryption not in self.ENCRYPTION_TYPES:
            raise InvalidParameter(u'Encryption "%s" does not exist (available: %s)' % (encryption, u','.join(self.ENCRYPTION_TYPES)))
        if encryption!=self.ENCRYPTION_TYPE_UNSECURED and password is None or len(password)==0:
            raise MissingParameter(u'Password parameter is missing')

        #check if network doesn't already exist
        if self.get_network(network) is not None:
            raise InvalidParameter(u'Network "%s" is already configured')
    
        #get config to write with encrypted password and clear password removed
        if encryption!=self.ENCRYPTION_TYPE_UNSECURED:
            c = Console()
            res = c.command(u'/usr/bin/wpa_passphrase "%s" "%s"' % (network, password))
            if res[u'error'] or res[u'killed']:
                self.logger.error(u'Error with password: %s' % u''.join(res[u'stderr']))
                raise Exception(u'Error with password: unable to encrypt it')
            if not ''.join(res[u'stdout']).startswith(u'network'):
                self.logger.error(u'Error with password: %s' % stdout)
                raise Exception(u'Error with password: %s' % stdout)
            password = None
            output = [line+u'\n' for line in res[u'stdout'] if not line.startswith(u'\t#psk=')]

            #inject hidden param if necessary
            if hidden:
                output.insert(2, u'\tscan_ssid=1\n')

            #inject network type
            if encryption in [self.ENCRYPTION_TYPE_WPA, self.ENCRYPTION_TYPE_WPA2]:
                output.insert(2, u'\tkey_mgmt=WPA-PSK\n')
            elif encryption==self.ENCRYPTION_TYPE_WEP:
                output.insert(2, u'\tkey_mgmt=NONE\n')

        else:
            #handle unsecured network
            output = [
                u'\nnetwork={\n',
                u'\tssid="%s"\n' % network,
                u'}\n'
            ]

        #write new network config
        return self.add_lines(output)

    

