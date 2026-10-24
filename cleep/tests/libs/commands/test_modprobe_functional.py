#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Modprobe ↔ /sbin/modprobe (safe negative call only)."""

import unittest
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.modprobe import Modprobe
from cleep.libs.tests.functional_helpers import setup_functional


@pytest.mark.functional
class ModprobeFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/sbin/modprobe")
        self.m = Modprobe()

    def test_load_nonexistent_module_fails(self):
        # Exercises real modprobe without mutating the running system.
        self.assertFalse(self.m.load_module("cleep_nonexistent_module_xyz"))

    def test_unload_nonexistent_module_fails(self):
        self.assertFalse(self.m.unload_module("cleep_nonexistent_module_xyz"))
