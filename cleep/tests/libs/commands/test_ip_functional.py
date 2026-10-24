#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Ip ↔ /sbin/ip (real binary)."""

import unittest
import logging
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.ip import Ip
from cleep.libs.tests.functional_helpers import setup_functional

IP_STATUS_KEYS = (
    "interface",
    "ipv4",
    "netmask",
    "ipv6",
    "prefixlen",
    "mac",
)


@pytest.mark.functional
class IpFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/sbin/ip")
        self.i = Ip()

    def test_is_installed_and_get_status(self):
        self.assertTrue(self.i.is_installed())
        status = self.i.get_status()
        logging.info(status)
        self.assertTrue(len(status) > 0, "ip addr returned no interfaces")
        entry = next(iter(status.values()))
        for key in IP_STATUS_KEYS:
            self.assertIn(key, entry)
