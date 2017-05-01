#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
import unittest
from console import Console
import os
import re

class WpaSupplicantConf():
    """
    Helper class to update and read /etc/wpa_supplicant/wpa_supplicant.conf file
    """

    CONF = '/etc/wpa_supplicant/wpa_supplicant.conf'

    MODE_WRITE = 'w'
    MODE_READ = 'r'
    MODE_APPEND = 'a'

    NETWORK_TYPE_WPA = 'wpa'
    NETWORK_TYPE_WPA2 = 'wpa2'
    NETWORK_TYPE_WEP = 'wep'
    NETWORK_TYPE_UNSECURED = 'unsecured'
    NETWORK_TYPE_UNKNOWN = 'unknown'
    NETWORK_TYPES = [NETWORK_TYPE_WPA, NETWORK_TYPE_WPA2, NETWORK_TYPE_WEP, NETWORK_TYPE_UNSECURED, NETWORK_TYPE_UNKNOWN]

    def __init__(self):
        self.__fd = None

    def __del__(self):
        self.__close()

    def __open(self, mode='r'):
        """
        Open config file
        @return file descriptor as returned by open() function
        @raise Exception if file doesn't exist
        """
        if not os.path.exists(self.CONF):
            raise Exception('wpa_supplicant.conf file does not exist')

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
        groups = re.findall('network\s*=\s*\{\s*(.*?)\s*\}', content, re.S)
        for group in groups:
            ssid = None
            scan_ssid = None
            key_mgmt = None
            hidden = False
            network_type = self.NETWORK_TYPE_UNSECURED
            res = re.search('ssid="(.*?)"\s', group+'\n')
            if res:
                ssid = res.group(1).strip()
            res = re.search('scan_ssid="(.*?)"\s', group+'\n')
            if res:
                scan_ssid = res.group(1).strip()
                if scan_ssid is not None and scan_ssid.isdigit() and scan_ssid=='1':
                    hidden = True
            res = re.search('key_mgmt="(.*?)"\s', group+'\n')
            if res:
                key_mgmt = res.group(1).strip()
                if key_mgmt=='WPA-PSK':
                    network_type = self.NETWORK_TYPE_WPA2
                elif key_mgmt=='NONE':
                    network_type = self.NETWORK_TYPE_WEP

            networks.append({
                'network': ssid,
                'hidden': hidden,
                'network_type': network_type
            })

        return networks

    def get_network(self, network):
        """
        Get network config
        @param network: network name
        @return network config (dict) or None if network is not found
        """
        networks = self.get_networks()
        for network_ in networks:
            if network_['network']==network:
                return network_

        return None

    def delete_network(self, network):
        """
        Delete network from config
        @param network: network name (ssid)
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
            raise CommandError('Network %s does not exist' % network)

        return True

    def add_network(self, network, network_type, password, hidden=False):
        """
        Add new network in config file
        Password is automatically encrypted using wpa_passphrase
        @param network: network name (ssid)
        @param network_type: type of network (wpa, wpa, wep, unsecured)
        @param password: network password (string)
        @param hidden: hiddent network flag (bool)
        """
        #check params
        if network is None or len(network)==0:
            raise MissingParameter('Network parameter is missing')
        if network_type is None or len(network_type)==0:
            raise MissingParameter('Network_type parameter is missing')
        if network_type not in self.NETWORK_TYPES:
            raise InvalidParameter('Network_type "%s" does not exist (available: %s)' % (network_type, ','.join(self.NETWORK_TYPES)))
        if network_type!=self.NETWORK_TYPE_UNSECURED and password is None or len(password)==0:
            raise MissingParameter('Password parameter is missing')

        #check if network doesn't already exist
        if self.get_network(network) is not None:
            raise InvalidParameter('Network "%s" is already configured')
    
        #get config to write with encrypted password and clear password removed
        if network_type!=self.NETWORK_TYPE_UNSECURED:
            c = Console()
            res = c.command('/usr/bin/wpa_passphrase "%s" "%s"' % (network, password))
            if res['error'] or res['killed']:
                self.logger.error('Error with password: %s' % ''.join(res['stderr']))
                raise Exception('Error with password: unable to encrypt it')
            if not ''.join(res['stdout']).startswith('network'):
                self.logger.error('Error with password: %s' % stdout)
                raise Exception('Error with password: %s' % stdout)
            password = None
            output = [line for line in res['stdout'] if not line.startswith('\t#psk=')]

            #inject hidden param if necessary
            if hidden:
                output.insert(2, '\tscan_ssid=1')

            #inject network type
            if network_type in [self.NETWORK_TYPE_WPA, self.NETWORK_TYPE_WPA2]:
                output.insert(2, '\tkey_mgmt=WPA-PSK')
            elif network_type==self.NETWORK_TYPE_WEP:
                output.insert(2, '\tkey_mgmt=NONE')

        else:
            #handle unsecured network
            output = [
                'network={',
                '\tssid="%s"' % network,
                '}'
            ]

        #write new network config
        fd = self.__open(self.MODE_APPEND)
        fd.write('\n%s\n' % '\n'.join(output))
        self.__close()

        return True

    

class WpaSupplicantConfTests_validConf(unittest.TestCase):
    def setUp(self):
        #fake conf file
        fd = file('wpasupplicant.fake.conf', 'w')
        fd.write('country=GB\nctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\n\nnetwork = {\n\tssid="mynetwork1"\n\tpsk="mypassword1"\n}\nnetwork={\n\tssid="mynetwork2"\n\tscan_ssid=1\n\t#psk="helloworld"\n\tpsk="mypassword2"\n}\n')
        fd.close()
        self.w = WpaSupplicantConf()
        self.w.CONF = 'wpasupplicant.fake.conf'

    def tearDown(self):
        os.remove('wpasupplicant.fake.conf')

    def test_get_networks(self):
        networks = self.w.get_networks()
        self.assertEqual(len(networks), 2)
        self.assertEqual(networks[0]['network'], 'mynetwork1')
        self.assertEqual(networks[1]['network'], 'mynetwork2')

    def test_add_network(self):
        self.assertTrue(self.w.add_network('mynetwork3', 'wpa', 'mypassword3'))
        networks = self.w.get_networks()
        self.assertEqual(len(networks), 3)
        self.assertEqual(networks[2]['network'], 'mynetwork3')

    def test_add_existing_network(self):
        self.assertRaises(Exception, self.w.add_network, 'mynetwork2', 'wpa', 'mypassword2')

    def test_add_missing_params(self):
        self.assertRaises(MissingParameter, self.w.add_network, None, 'wpa', 'mypassword2')
        self.assertRaises(MissingParameter, self.w.add_network, '', 'wpa', 'mypassword2')
        self.assertRaises(MissingParameter, self.w.add_network, 'mynetwork3', None, 'mypassword2')
        self.assertRaises(MissingParameter, self.w.add_network, 'mynetwork3', '', 'mypassword2')
        self.assertRaises(MissingParameter, self.w.add_network, 'mynetwork3', 'wpa', None)
        self.assertRaises(MissingParameter, self.w.add_network, 'mynetwork3', 'wpa', '')

    def test_add_invalid_params(self):
        self.assertRaises(InvalidParameter, self.w.add_network, 'mynetwork3', 'wpa6', 'mypassword2')
        self.assertRaises(InvalidParameter, self.w.add_network, 'mynetwork2', 'wpa2', 'mypassword2')

    def test_delete_existing_network(self):
        self.assertTrue(self.w.delete_network('mynetwork2'))
        self.assertEqual(len(self.w.get_networks()), 1)
        self.assertTrue(self.w.delete_network('mynetwork1'))
        self.assertEqual(len(self.w.get_networks()), 0)

    def test_delete_unknown_network(self):
        self.assertRaises(CommandError, self.w.delete_network, 'network666')
        self.assertEqual(len(self.w.get_networks()), 2)


class WpaSupplicantConfTests_emptyConf(unittest.TestCase):
    def setUp(self):
        #fake conf file
        fd = file('wpasupplicant.fake.conf', 'w')
        fd.write('country=GB\nctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1')
        fd.close()
        self.w = WpaSupplicantConf()
        self.w.CONF = 'wpasupplicant.fake.conf'

    def tearDown(self):
        os.remove('wpasupplicant.fake.conf')

    def test_get_networks(self):
        networks = self.w.get_networks()
        self.assertEqual(len(networks), 0)

    def test_add_network(self):
        self.assertTrue(self.w.add_network('mynetwork3', 'wpa', 'mypassword3'))
        networks = self.w.get_networks()
        self.assertEqual(len(networks), 1)
        self.assertEqual(networks[0]['network'], 'mynetwork3')

