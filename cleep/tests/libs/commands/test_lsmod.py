#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.commands.lsmod import Lsmod
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import Mock
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()

LSMOD_STDOUT = [
    "hci_uart",
    "bluetooth",
    "bnep",
]


class LsmodTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL,
            format="%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
        )
        self.l = Lsmod()
        self.l.command = Mock(
            return_value={
                "killed": False,
                "error": False,
                "returncode": 0,
                "stdout": LSMOD_STDOUT,
                "stderr": [],
            }
        )

    def tearDown(self):
        pass

    def test_get_loaded_modules(self):
        mods = self.l.get_loaded_modules()
        logging.info(mods)
        self.assertTrue(len(mods) > 0)
        self.assertIn("hci_uart", mods)

    def test_is_module_loaded(self):
        self.assertTrue(self.l.is_module_loaded("hci_uart"))
        self.assertFalse(self.l.is_module_loaded("dummy"))

    def test_use_cache(self):
        self.l.is_module_loaded("hci_uart")
        self.l.is_module_loaded("hci_uart")
        self.assertEqual(self.l.command.call_count, 1, "Cache seems to not be used")
