#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import CommandError, MissingParameter, InvalidParameter
from raspiot.libs.wpasupplicantconf import WpaSupplicantConf
import unittest
import os

class WpaSupplicantConfTests_validConf(unittest.TestCase):
    def setUp(self):
        #fake conf file
        fd = file('wpasupplicant.fake.conf', 'w')
        #fd.write('country=GB\nctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\n\nnetwork = {\n\tssid="mynetwork1"\n\tpsk="mypassword1"\n}\nnetwork={\n\tssid="mynetwork2"\n\tscan_ssid=1\n\t#psk="helloworld"\n\tpsk="mypassword2"\n}\n')
        fd.write("""country=GB
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network = {
    ssid="mynetwork1"
    psk="mypassword1"
}
network={
    ssid="mynetwork2"
    scan_ssid=1
    #psk="helloworld"
    psk="mypassword2"
}""")
        fd.close()
        self.w = WpaSupplicantConf()
        self.w.CONF = 'wpasupplicant.fake.conf'

    def tearDown(self):
        os.remove('wpasupplicant.fake.conf')

    def test_get_networks(self):
        networks = self.w.get_networks()
        self.assertEqual(len(networks), 2)
        self.assertEqual(networks['mynetwork1']['network'], 'mynetwork1')
        self.assertEqual(networks['mynetwork2']['network'], 'mynetwork2')

    def test_add_network(self):
        self.assertTrue(self.w.add_network('mynetwork3', 'wpa', 'mypassword3'))
        networks = self.w.get_networks()
        self.assertEqual(len(networks), 3)
        self.assertEqual(networks['mynetwork3']['network'], 'mynetwork3')

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
        self.assertFalse(self.w.delete_network('network666'))
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
        self.assertEqual(networks['mynetwork3']['network'], 'mynetwork3')

