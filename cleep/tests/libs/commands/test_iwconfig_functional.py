#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Iwconfig ↔ /sbin/iwconfig (real binary)."""

import unittest
import logging
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.iwconfig import Iwconfig
from cleep.libs.tests.functional_helpers import setup_functional


@pytest.mark.functional
class IwconfigFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/sbin/iwconfig")
        self.i = Iwconfig()

    def test_get_interfaces_contract(self):
        interfaces = self.i.get_interfaces()
        logging.info(interfaces)
        self.assertIsInstance(interfaces, dict)
        for entry in interfaces.values():
            self.assertIn("network", entry)
