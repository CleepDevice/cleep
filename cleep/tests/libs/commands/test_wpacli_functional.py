#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Wpacli ↔ /sbin/wpa_cli (real binary)."""

import unittest
import logging
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.wpacli import Wpacli
from cleep.libs.tests.functional_helpers import (
    setup_functional,
    first_wifi_interface,
)

WPACLI_NETWORK_KEYS = ("id", "ssid", "bssid", "status")
WPACLI_STATUS_KEYS = ("network", "state", "ipaddress")


@pytest.mark.functional
class WpacliFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/sbin/wpa_cli")
        TestLib.require_binary("/sbin/iw")
        self.w = Wpacli()

    def test_get_configured_networks(self):
        networks = self.w.get_configured_networks()
        logging.info(networks)
        self.assertIsInstance(networks, dict)
        for entry in networks.values():
            for key in WPACLI_NETWORK_KEYS:
                self.assertIn(key, entry)

    def test_get_status_exercises_binary(self):
        iface = first_wifi_interface() or "wlan0"
        status = self.w.get_status(iface)
        logging.info("iface=%s status=%s", iface, status)
        # wpa_cli status always returns the contract dict (fields may be None/UNKNOWN)
        self.assertIsInstance(status, dict)
        for key in WPACLI_STATUS_KEYS:
            self.assertIn(key, status)
        self.assertIn(status["state"], Wpacli.STATES + [Wpacli.STATE_UNKNOWN])
