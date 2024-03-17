#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace("tests/", ""))
from iw import Iw
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from cleep.libs.tests.common import get_log_level
from unittest.mock import Mock

LOG_LEVEL = get_log_level()
OUTPUT = [
    "phy#0",
    "        Unnamed/non-netdev interface",
    "                wdev 0x2",
    "                addr ba:27:eb:37:71:4d",
    "                type P2P-device",
    "                txpower 31.00 dBm",
    "        Interface wlan0",
    "                ifindex 3",
    "                wdev 0x1",
    "                addr b8:27:eb:37:71:4d",
    "                type managed",
    "                channel 1 (2412 MHz), width: 20 MHz, center1: 2412 MHz",
    "                txpower 31.00 dBm",
]


class IwTests(unittest.TestCase):
    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL, format=u"%(asctime)s %(name)s %(levelname)s : %(message)s"
        )
        self.i = Iw()

    def tearDown(self):
        pass

    def test_is_installed(self):
        self.assertTrue(self.i.is_installed())

    def test_get_adapters(self):
        self.i.command = Mock(return_value={ "stdout":OUTPUT, "returncode":0 })

        adapters = self.i.get_adapters()
        logging.debug("Adapters: %s" % adapters)

        self.assertGreaterEqual(len(adapters), 1)
        for adapter, values in adapters.items():
            self.assertTrue("interface" in values)
            self.assertTrue("network" in values)


if __name__ == "__main__":
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_iw.py; coverage report -m -i
    unittest.main()
