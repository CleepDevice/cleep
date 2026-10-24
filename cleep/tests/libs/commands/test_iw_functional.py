#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Iw ↔ /sbin/iw (real binary)."""

import unittest
import logging
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.iw import Iw
from cleep.libs.tests.functional_helpers import setup_functional


@pytest.mark.functional
class IwFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/sbin/iw")
        self.i = Iw()

    def test_is_installed_and_get_adapters(self):
        self.assertTrue(self.i.is_installed())
        adapters = self.i.get_adapters()
        logging.info(adapters)
        self.assertIsInstance(adapters, dict)
        for entry in adapters.values():
            self.assertIn("interface", entry)
            self.assertIn("network", entry)
