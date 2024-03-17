#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace("tests/", ""))
from wpacli import Wpacli
from cleep.libs.tests.lib import TestLib
import unittest
import logging
import os
from shutil import copyfile
from cleep.libs.tests.common import get_log_level
from unittest.mock import Mock, patch

LOG_LEVEL = get_log_level()
LIST_NETWORKS = [
    "Selected interface 'p2p-dev-wlan0'",
    "network id / ssid / bssid / flags",
    "0   MyWifi    any",
]
SCAN_NETWORKS = [
    "bssid / frequency / signal level / flags / ssid",
    "b6:39:56:76:d5:58   2472    -86 [WPA2-PSK-CCMP][WPS][ESS]   MyWifi",
]

class WpacliTests(unittest.TestCase):
    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL, format=u"%(asctime)s %(name)s %(levelname)s : %(message)s"
        )
        self.w = Wpacli()

    def tearDown(self):
        pass

    @patch("wpacli.time.sleep")
    def test_scan_networks(self, time_sleep_mock):
        self.w.command = Mock(return_value={"returncode": 0, "error": False, "killed": False, "stdout": SCAN_NETWORKS})

        networks = self.w.scan_networks(interface="wlan0", duration=2.0)
        logging.debug(networks)

        self.assertEqual(networks, {
            'wlan0': {
                'MyWifi': {
                    'interface': 'wlan0',
                    'network': 'MyWifi',
                    'encryption': 'wpa2',
                    'signallevel': 17
                }
            }
        })
        time_sleep_mock.assert_called_with(2.0)

    def test_get_configured_networks(self):
        self.w.command = Mock(return_value={"returncode": 0, "error": False, "killed": False, "stdout": LIST_NETWORKS})

        networks = self.w.get_configured_networks()
        logging.debug("networks=%s", networks)
        
        self.assertEqual(networks, {
            'MyWifi': {
                'id': '0',
                'ssid': 'MyWifi',
                'bssid': 'any',
                'status': 1
            }
        })
        

if __name__ == "__main__":
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_wpacli.py; coverage report -m -i
    unittest.main()
