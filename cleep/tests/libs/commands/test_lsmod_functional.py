#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Lsmod ↔ /bin/lsmod (real binary)."""

import unittest
import logging
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.lsmod import Lsmod
from cleep.libs.tests.functional_helpers import setup_functional


@pytest.mark.functional
class LsmodFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/bin/lsmod")
        self.l = Lsmod()

    def test_get_loaded_modules_and_lookup(self):
        mods = self.l.get_loaded_modules()
        logging.info(mods)
        self.assertTrue(len(mods) > 0, "lsmod returned no modules")
        self.assertTrue(self.l.is_module_loaded(mods[0]))
        self.assertFalse(self.l.is_module_loaded("cleep_nonexistent_module_xyz"))
