#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.commands.iwconfig import Iwconfig
import unittest
import logging

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

"""
Command output: need to fake it

enxb827eb729ebf  no wireless extensions.

wlan0     IEEE 802.11  ESSID:"TangWifi"  
          Mode:Managed  Frequency:5.18 GHz  Access Point: B0:39:56:76:D7:9F   
          Bit Rate=40.5 Mb/s   Tx-Power=31 dBm   
          Retry short limit:7   RTS thr:off   Fragment thr:off
          Encryption key:off
          Power Management:on
          Link Quality=45/70  Signal level=-65 dBm  
          Rx invalid nwid:0  Rx invalid crypt:0  Rx invalid frag:0
          Tx excessive retries:0  Invalid misc:0   Missed beacon:0

lo        no wireless extensions.

wlx086a0a97728f  IEEE 802.11  ESSID:off/any  
          Mode:Managed  Access Point: Not-Associated   Tx-Power=31 dBm   
          Retry short limit:7   RTS thr:off   Fragment thr:off
          Encryption key:off
          Power Management:on
"""

class IwconfigTests(unittest.TestCase):

    def setUp(self):
        self.i = Iwconfig()

    def tearDown(self):
        pass

    def test_get_interfaces(self):
        interfaces = self.i.get_interfaces()
        logging.debug(interfaces)
        self.assertFalse('lo' in interfaces.keys())
        self.assertGreaterEqual(len(interfaces), 1)
        if len(interfaces)>0:
            interface = interfaces[interfaces.keys()[0]]
            self.assertTrue('network' in interface.keys())

