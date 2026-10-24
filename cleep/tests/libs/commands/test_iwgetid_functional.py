#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Iwgetid ↔ /sbin/iwgetid (real binary)."""

import unittest
import logging
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.iwgetid import Iwgetid
from cleep.libs.tests.functional_helpers import setup_functional


@pytest.mark.functional
class IwgetidFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/sbin/iwgetid")
        self.i = Iwgetid()

    def test_get_connections_contract(self):
        connections = self.i.get_connections()
        logging.info(connections)
        self.assertIsInstance(connections, dict)
        for entry in connections.values():
            self.assertIn("network", entry)
