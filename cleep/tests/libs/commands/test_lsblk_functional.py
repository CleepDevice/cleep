#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Lsblk ↔ /bin/lsblk (real binary)."""

import unittest
import logging
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.lsblk import Lsblk
from cleep.libs.tests.functional_helpers import setup_functional

LSBLK_KEYS = (
    "name",
    "major",
    "minor",
    "size",
    "totalsize",
    "percent",
    "readonly",
    "mountpoint",
    "partition",
    "removable",
    "drivemodel",
)


@pytest.mark.functional
class LsblkFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/bin/lsblk")
        self.l = Lsblk()

    def test_get_devices_infos_contract(self):
        infos = self.l.get_devices_infos()
        logging.info(infos)
        self.assertTrue(len(infos) > 0, "lsblk returned no drives")
        drive = next(iter(infos.values()))
        part = next(iter(drive.values()))
        for key in LSBLK_KEYS:
            self.assertIn(key, part)

    def test_get_drives_partitions_and_lookup(self):
        drives = self.l.get_drives()
        partitions = self.l.get_partitions()
        self.assertTrue(len(drives) > 0)
        self.assertTrue(len(partitions) > 0)
        drive_name = next(iter(drives.keys()))
        part_name = next(iter(partitions.keys()))
        for key in LSBLK_KEYS:
            self.assertIn(key, drives[drive_name])
            self.assertIn(key, partitions[part_name])
        self.assertIsNotNone(self.l.get_device_infos(drive_name))
        self.assertIsNotNone(self.l.get_device_infos(part_name))
        self.assertIsNone(self.l.get_device_infos("cleep_nonexistent_disk_xyz"))
