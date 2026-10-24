#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.commands.ifconfig import Ifconfig
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import patch
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()

INTERFACE_KEYS = (
    "mac",
    "interface",
    "ipv4",
    "gateway_ipv4",
    "netmask_ipv4",
    "ipv6",
    "gateway_ipv6",
    "netmask_ipv6",
)


class IfconfigTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL, format="%(asctime)s %(name)s %(levelname)s : %(message)s"
        )
        self.i = Ifconfig()

    def tearDown(self):
        pass

    @patch("cleep.libs.commands.ifconfig.netifaces")
    def test_get_configurations(self, mock_netifaces):
        mock_netifaces.AF_LINK = 17
        mock_netifaces.AF_INET = 2
        mock_netifaces.AF_INET6 = 10
        mock_netifaces.interfaces.return_value = ["lo", "eth0"]
        mock_netifaces.ifaddresses.return_value = {
            17: [{"addr": "aa:bb:cc:dd:ee:ff"}],
            2: [{"addr": "192.168.1.10", "mask": "255.255.255.0"}],
            10: [{"addr": "fe80::1", "mask": "ffff:ffff:ffff:ffff::"}],
        }
        mock_netifaces.gateways.return_value = {
            2: [("192.168.1.1", "eth0", True)],
        }

        interfaces = self.i.get_configurations()
        self.assertFalse("lo" in interfaces.keys())
        self.assertGreaterEqual(len(interfaces), 1)
        self.assertIn("eth0", interfaces)
        for key in INTERFACE_KEYS:
            self.assertTrue(key in interfaces["eth0"].keys())
        self.assertEqual(interfaces["eth0"]["ipv4"], "192.168.1.10")
        self.assertEqual(interfaces["eth0"]["gateway_ipv4"], "192.168.1.1")
        self.assertEqual(interfaces["eth0"]["mac"], "aa:bb:cc:dd:ee:ff")
