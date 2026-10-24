#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Rfkill ↔ /usr/sbin/rfkill (real binary)."""

import unittest
import logging
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.rfkill import Rfkill
from cleep.libs.tests.functional_helpers import setup_functional

RFKILL_KEYS = ("device", "id", "desc", "blocked")


@pytest.mark.functional
class RfkillFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/usr/sbin/rfkill")
        self.r = Rfkill()

    def test_is_installed_and_infos_shape(self):
        self.assertTrue(self.r.is_installed())
        wifi = self.r.get_wifi_infos()
        bluetooth = self.r.get_bluetooth_infos()
        logging.info("wifi=%s bluetooth=%s", wifi, bluetooth)
        # Adapter may be absent; None is valid. Missing binary / parse crash is not.
        if wifi is not None:
            for key in RFKILL_KEYS:
                self.assertIn(key, wifi)
            self.assertIsInstance(wifi["blocked"], bool)
        if bluetooth is not None:
            for key in RFKILL_KEYS:
                self.assertIn(key, bluetooth)
            self.assertIsInstance(bluetooth["blocked"], bool)
