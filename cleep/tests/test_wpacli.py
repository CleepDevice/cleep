#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.commands.wpacli import Wpacli
import unittest
import logging

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class WpacliTests(unittest.TestCase):

    def setUp(self):
        self.w = Wpacli()

    def tearDown(self):
        pass

    def test_get_configured_networks(self):
        networks = self.w.get_configured_networks()
        self.assertNotEqual(0, len(networks))
        network_name = networks.keys()[0]
        self.assertTrue('id' in networks[network_name].keys())
        self.assertTrue('ssid' in networks[network_name].keys())
        self.assertTrue('bssid' in networks[network_name].keys())
        self.assertTrue('status' in networks[network_name].keys())

    def test_scan_networks(self):
        networks = self.w.scan_networks(interface='wlan0')
        logging.debug(networks)
        self.assertNotEqual(0, len(networks))
        interface = networks.keys()[0]
        network_name = networks[interface].keys()[0]
        self.assertTrue('interface' in networks[interface][network_name].keys())
        self.assertTrue('network' in networks[interface][network_name].keys())
        self.assertTrue('encryption' in networks[interface][network_name].keys())
        self.assertTrue('signallevel' in networks[interface][network_name].keys())

    def test_get_status(self):
        status = self.w.get_status(u'wlan0')
        self.assertNotEqual(status, self.w.STATE_UNKNOWN)
        
