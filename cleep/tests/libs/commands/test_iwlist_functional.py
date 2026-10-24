#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Iwlist ↔ /sbin/iwlist (real binary)."""

import unittest
import logging
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.iwlist import Iwlist
from cleep.libs.tests.functional_helpers import (
    setup_functional,
    first_wifi_interface,
)

IWLIST_NETWORK_KEYS = (
    "interface",
    "network",
    "encryption",
    "signallevel",
    "frequencies",
)


@pytest.mark.functional
class IwlistFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/sbin/iwlist")
        TestLib.require_binary("/sbin/iw")
        self.i = Iwlist()

    def test_get_networks_exercises_binary(self):
        iface = first_wifi_interface()
        if iface is None:
            # No wifi hardware: still invoke iwlist so a missing/broken binary fails.
            networks = self.i.get_networks("cleep_nonexistent_iface_xyz")
            logging.info("no wifi iface; networks=%s error=%s", networks, self.i.has_error())
            self.assertIsInstance(networks, dict)
            self.assertTrue(
                self.i.has_error(),
                "iwlist should report error on nonexistent interface",
            )
            return

        networks = self.i.get_networks(iface)
        logging.info("iface=%s networks=%s error=%s", iface, networks, self.i.has_error())
        self.assertIsInstance(networks, dict)
        self.assertFalse(
            self.i.has_error(),
            "iwlist scan failed on interface %s (wrapper/binary mismatch?)" % iface,
        )
        for entry in networks.values():
            for key in IWLIST_NETWORK_KEYS:
                self.assertIn(key, entry)
