#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
from console import Console
import os
import re

class WpaSupplicantConf():
    """
    Helper class to update and read /etc/wpa_supplicant/wpa_supplicant.conf file
    """

    CONF = u'/etc/wpa_supplicant/wpa_supplicant.conf'

    MODE_WRITE = u'w'
    MODE_READ = u'r'
    MODE_APPEND = u'a'

    ENCRYPTION_TYPE_WPA = u'wpa'
    ENCRYPTION_TYPE_WPA2 = u'wpa2'
    ENCRYPTION_TYPE_WEP = u'wep'
    ENCRYPTION_TYPE_UNSECURED = u'unsecured'
    ENCRYPTION_TYPE_UNKNOWN = u'unknown'
    ENCRYPTION_TYPES = [ENCRYPTION_TYPE_WPA, ENCRYPTION_TYPE_WPA2, ENCRYPTION_TYPE_WEP, ENCRYPTION_TYPE_UNSECURED, ENCRYPTION_TYPE_UNKNOWN]

    def __init__(self):
        """
        Constructor
        """
        self.__fd = None

    def __del__(self):
        """
        Destructor
        """
        self.__close()

    def __open(self, mode='r'):
        """
        Open config file

        Returns:
            file: file descriptor as returned by open() function

        Raises:
            Exception if file doesn't exist
        """
        if not os.path.exists(self.CONF):
            raise Exception(u'wpa_supplicant.conf file does not exist')

        self.__fd = open(self.CONF, mode)
        return self.__fd

    def __close(self):
        """
        Close file descriptor is still opened
        """
        if self.__fd:
            self.__fd.close()
            self.__fd = None
    
    def get_networks(self):
        """
        Return networks found in conf file
        """
        networks = []
        fd = self.__open()
        content = fd.read()
        self.__close()
        groups = re.findall(u'network\s*=\s*\{\s*(.*?)\s*\}', content, re.S)
        for group in groups:
            ssid = None
            scan_ssid = None
            key_mgmt = None
            hidden = False
            encryption = self.ENCRYPTION_TYPE_UNSECURED
            res = re.search(u'ssid="(.*?)"\s', group+'\n')
            if res:
                ssid = res.group(1).strip()
            res = re.search(u'scan_ssid="(.*?)"\s', group+'\n')
            if res:
                scan_ssid = res.group(1).strip()
                if scan_ssid is not None and scan_ssid.isdigit() and scan_ssid=='1':
                    hidden = True
            res = re.search(u'key_mgmt="(.*?)"\s', group+'\n')
            if res:
                key_mgmt = res.group(1).strip()
                if key_mgmt==u'WPA-PSK':
                    encryption = self.ENCRYPTION_TYPE_WPA2
                elif key_mgmt==u'NONE':
                    encryption = self.ENCRYPTION_TYPE_WEP

            networks.append({
                u'network': ssid,
                u'hidden': hidden,
                u'encryption': encryption
            })

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
        for network_ in networks:
            if network_[u'network']==network:
                return network_

        return None

    def delete_network(self, network):
        """
        Delete network from config

        Args:
            network (string): network name

        Returns:
            bool: True if network deleted, False otherwise
        """
        fd = self.__open()
        content = fd.read()
        self.__close()
        groups = re.findall('(network\s*=\s*\{\s*(.*?)\s*\})', content, re.S)
        found = False
        for group in groups:
            res = re.search('ssid="(.*?)"\s', group[1]+'\n')
            if res:
                ssid = res.group(1).strip()
                if ssid==network:
                    #network found, remove it
                    found = True
                    content = content.replace(group[0], '').strip()
                    break

        if found:
            #save new content
            fd = self.__open(self.MODE_WRITE)
            fd.write(content)
            self.__close()
        else:
            return False

        return True

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
            output = [line for line in res[u'stdout'] if not line.startswith(u'\t#psk=')]

            #inject hidden param if necessary
            if hidden:
                output.insert(2, u'\tscan_ssid=1')

            #inject network type
            if encryption in [self.ENCRYPTION_TYPE_WPA, self.ENCRYPTION_TYPE_WPA2]:
                output.insert(2, u'\tkey_mgmt=WPA-PSK')
            elif encryption==self.ENCRYPTION_TYPE_WEP:
                output.insert(2, u'\tkey_mgmt=NONE')

        else:
            #handle unsecured network
            output = [
                u'network={',
                u'\tssid="%s"' % network,
                u'}'
            ]

        #write new network config
        fd = self.__open(self.MODE_APPEND)
        fd.write(u'\n%s\n' % '\n'.join(output))
        self.__close()

        return True

    

