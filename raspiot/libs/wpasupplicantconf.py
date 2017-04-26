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
    NETWORK_TYPE_UNSECURE = 'unsecure'
    NETWORK_TYPES = [NETWORK_TYPE_WPA, NETWORK_TYPE_WPA2, NETWORK_TYPE_WEP, NETWORK_TYPE_UNSECURE]

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
            raise Exception('wap_supplicant.conf file does not exist')

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
            res = re.search('ssid="(.*?)"\s', group+'\n')
            if res:
                ssid = res.group(1).strip()
                networks.append(ssid)

        return networks

    def remove_network(self, network):
        """
        Remove network from config
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
            raise CommandError('Network "%s" does not exist')

        return True

    def add_network(self, network, network_type, password, hidden=False):
        """
        Add new network in config file
        Password is automatically encrypted using wpa_passphrase
        @param network: network name (ssid)
        @param network_type: type of network (WPA, WPA2, WEP, unsecure)
        @param password: network password (string)
        @param hidden: hiddent network flag (bool)
        """
        #check params
        if network is None or len(network)==0:
            raise MissingParameter('Network parameter is missing')
        if password is None or len(password)==0:
            raise MissingParameter('Password parameter is missing')
        if network_type is None or len(network_type)==0:
            raise MissingParameter('Network_type parameter is missing')
        if network_type not in self.NETWORK_TYPES:
            raise InvalidParameter('Network_type "%s" does not exist (available: %s)' % (network_type, ','.join(self.NETWORK_TYPES)))

        #check if network doesn't already exist
        networks = self.get_networks()
        if network in networks:
            raise InvalidParameter('Network "%s" is already configured')
    
        #get config to write with encrypted password and clear password removed
        c = Console()
        res = c.command('/usr/bin/wpa_passphrase "%s" "%s"' % (network, password))
        if res['error'] or res['killed']:
            raise Exception('Unable to encrypt password')
        password = None
        output = [line for line in res['output'] if not line.startswith('\t#psk=')]

        #inject hidden param if necessary
        if hidden:
            output.insert('\tscan_ssid=1', 2)

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
        self.assertEqual(networks[0], 'mynetwork1')
        self.assertEqual(networks[1], 'mynetwork2')

    def test_add_network(self):
        self.assertTrue(self.w.add_network('mynetwork3', 'wpa', 'mypassword3'))
        networks = self.w.get_networks()
        self.assertEqual(len(networks), 3)
        self.assertEqual(networks[2], 'mynetwork3')

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

    def test_remove_existing_network(self):
        self.assertTrue(self.w.remove_network('mynetwork2'))
        self.assertEqual(len(self.w.get_networks()), 1)
        self.assertTrue(self.w.remove_network('mynetwork1'))
        self.assertEqual(len(self.w.get_networks()), 0)

    def test_remove_unknown_network(self):
        self.assertRaises(CommandError, self.w.remove_network, 'network666')
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
        self.assertEqual(networks[0], 'mynetwork3')

