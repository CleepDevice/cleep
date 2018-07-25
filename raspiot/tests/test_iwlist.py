#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.commands.iwlist import Iwlist
from raspiot.libs.configs.wpasupplicantconf import WpaSupplicantConf
import unittest
import logging

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class IwlistTests(unittest.TestCase):

    def setUp(self):
        self.i = Iwlist()

    def tearDown(self):
        pass

    def test_get_interfaces(self):
        networks = self.i.get_networks('wlan0')
        self.assertGreaterEqual(len(networks), 1)
        for network in networks:
            net = networks[network]
            self.assertTrue('interface' in net)
            self.assertTrue('network' in net)
            self.assertTrue('encryption' in net)
            self.assertTrue('signallevel' in net)
            self.assertTrue('encryption' in net)
            self.assertTrue('frequencies' in net)

            self.assertTrue(len(net['interface'])>0)
            self.assertTrue(len(net['network'])>0)
            self.assertTrue(isinstance(net['signallevel'], int))
            self.assertTrue(net['encryption'] in (WpaSupplicantConf.ENCRYPTION_TYPE_WPA, WpaSupplicantConf.ENCRYPTION_TYPE_WPA2, WpaSupplicantConf.ENCRYPTION_TYPE_UNSECURED, WpaSupplicantConf.ENCRYPTION_TYPE_WEP, WpaSupplicantConf.ENCRYPTION_TYPE_UNKNOWN))
            self.assertTrue(all(x in (self.i.FREQ_2_4GHZ, self.i.FREQ_5GHZ) for x in net['frequencies']))
            self.assertGreaterEqual(len(net['frequencies']), 1)
