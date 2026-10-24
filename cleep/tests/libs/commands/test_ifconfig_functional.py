#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Ifconfig ↔ netifaces (replaces /sbin/ifconfig parsing)."""

import unittest
import logging
import pytest

from cleep.libs.commands.ifconfig import Ifconfig
from cleep.libs.tests.functional_helpers import setup_functional

IFCONFIG_KEYS = (
    "mac",
    "interface",
    "ipv4",
    "gateway_ipv4",
    "netmask_ipv4",
    "ipv6",
    "gateway_ipv6",
    "netmask_ipv6",
)


@pytest.mark.functional
class IfconfigFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        self.i = Ifconfig()

    def test_get_configurations_contract(self):
        interfaces = self.i.get_configurations()
        logging.info(interfaces)
        self.assertNotIn("lo", interfaces)
        self.assertGreaterEqual(len(interfaces), 1, "netifaces returned no interfaces")
        iface = next(iter(interfaces.values()))
        for key in IFCONFIG_KEYS:
            self.assertIn(key, iface)
