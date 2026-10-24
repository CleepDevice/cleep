#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Ifupdown ↔ /sbin/ifup, ifdown, ip (safe negative call)."""

import unittest
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.ifupdown import Ifupdown
from cleep.libs.tests.functional_helpers import setup_functional


@pytest.mark.functional
class IfupdownFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/sbin/ifup")
        TestLib.require_binary("/sbin/ifdown")
        TestLib.require_binary("/sbin/ip")
        self.i = Ifupdown()

    def test_stop_nonexistent_interface_fails(self):
        # Exercises real ifdown without touching a live interface.
        self.assertFalse(self.i.stop_interface("cleep_nonexistent_iface_xyz"))

    def test_start_nonexistent_interface_fails(self):
        self.assertFalse(self.i.start_interface("cleep_nonexistent_iface_xyz"))
