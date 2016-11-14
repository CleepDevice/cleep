#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('/root/cleep/raspiot/libs/commands')
from iwconfig import Iwconfig
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from mock import Mock

logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

FAKE_OUPUT = """enxb827eb729ebf  no wireless extensions.

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
          Power Management:on"""

class IwconfigTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        self.i = Iwconfig()

    def tearDown(self):
        pass

    def test_get_interfaces(self):
        self.i.command = Mock(return_value={
            'error': False,
            'killed': False,
            'stdout': FAKE_OUPUT.split('\n'),
            'stderr': None,
        })
        self.i.get_last_return_code = Mock(return_value=0)

        interfaces = self.i.get_interfaces()
        logging.debug(interfaces)
        self.assertFalse('lo' in interfaces.keys())
        self.assertGreaterEqual(len(interfaces), 1)
        if len(interfaces)>0:
            interface = interfaces[interfaces.keys()[0]]
            self.assertTrue('network' in interface.keys())

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_iwconfig.py
    #coverage report -m
    unittest.main()
