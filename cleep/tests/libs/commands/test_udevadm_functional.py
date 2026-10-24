#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Udevadm ↔ /bin/udevadm (real binary)."""

import unittest
import logging
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.udevadm import Udevadm
from cleep.libs.commands.lsblk import Lsblk
from cleep.libs.tests.functional_helpers import setup_functional

UDEVADM_TYPES = (
    Udevadm.TYPE_UNKNOWN,
    Udevadm.TYPE_ATA,
    Udevadm.TYPE_USB,
    Udevadm.TYPE_SDCARD,
    Udevadm.TYPE_MMC,
)


@pytest.mark.functional
class UdevadmFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/bin/udevadm")
        TestLib.require_binary("/bin/lsblk")
        self.u = Udevadm()
        self.l = Lsblk()

    def test_get_device_type_for_drive(self):
        drives = self.l.get_drives()
        self.assertTrue(len(drives) > 0, "no drive to query with udevadm")
        drive_name = next(iter(drives.keys()))
        dtype = self.u.get_device_type(drive_name)
        logging.info("device=%s type=%s", drive_name, dtype)
        self.assertIn(dtype, UDEVADM_TYPES)
