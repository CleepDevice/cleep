#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('/root/cleep/raspiot/libs/commands')
from wpacli import Wpacli
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
import os
from shutil import copyfile

logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class WpacliTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        self.w = Wpacli()

    def tearDown(self):
        pass

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

    def test_get_configured_networks(self):
        logging.info('Unable to test get_configured_networks, need to know valid wifi network')
        #networks = self.w.get_configured_networks()
        #logging.debug('Networks: %s' % networks)
        #self.assertTrue(len(networks)>0, 'Networks list should contains data')
        #for network_name, network in networks:
        #    self.assertTrue('id' in network)
        #    self.assertTrue('ssid' in network)
        #    self.assertTrue('bssid' in network)
        #    self.assertTrue('status' in network)


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_iw.py
    #coverage report -m
    unittest.main()
