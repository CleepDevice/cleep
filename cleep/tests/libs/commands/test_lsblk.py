#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.commands.lsblk import Lsblk
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import Mock
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()

# Realistic /bin/lsblk --list --bytes --output NAME,MAJ:MIN,TYPE,RM,SIZE,RO,MOUNTPOINT,RA,MODEL
LSBLK_STDOUT = [
    "mmcblk0 179:0 disk 0 15931539456 0  128 SC16G",
    "mmcblk0p1 179:1 part 0 268435456 0 /boot 128 ",
    "mmcblk0p2 179:2 part 0 15663054848 0 / 128 ",
]

PARTITION_KEYS = (
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


class LsblkTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL,
            format="%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
        )
        self.l = Lsblk()
        self.l.command = Mock(
            return_value={
                "killed": False,
                "error": False,
                "returncode": 0,
                "stdout": LSBLK_STDOUT,
                "stderr": [],
            }
        )

    def tearDown(self):
        pass

    def test_get_devices_infos(self):
        infos = self.l.get_devices_infos()
        logging.info(infos)
        self.assertTrue(len(infos) > 0)
        self.assertTrue("mmcblk0" in infos)
        self.assertTrue("mmcblk0p1" in infos["mmcblk0"])
        self.assertTrue("mmcblk0p2" in infos["mmcblk0"])

        for key in PARTITION_KEYS:
            self.assertTrue(key in infos["mmcblk0"]["mmcblk0p1"])

    def test_get_drives(self):
        infos = self.l.get_drives()
        logging.info(infos)
        self.assertTrue(len(infos) > 0)
        self.assertTrue("mmcblk0" in infos)

        for key in PARTITION_KEYS:
            self.assertTrue(key in infos["mmcblk0"])

    def test_get_partitions(self):
        infos = self.l.get_partitions()
        logging.info(infos)
        self.assertTrue(len(infos) > 0)
        self.assertFalse("mmcblk0" in infos)
        self.assertTrue("mmcblk0p1" in infos)
        self.assertTrue("mmcblk0p2" in infos)

        for key in PARTITION_KEYS:
            self.assertTrue(key in infos["mmcblk0p1"])

    def test_get_device_infos(self):
        self.assertIsNotNone(self.l.get_device_infos("mmcblk0"))
        self.assertIsNotNone(self.l.get_device_infos("mmcblk0p1"))
        self.assertIsNotNone(self.l.get_device_infos("mmcblk0p2"))
        self.assertIsNone(self.l.get_device_infos("mmcblk0p3"))

    def test_use_cache(self):
        self.l.get_devices_infos()
        self.l.get_devices_infos()
        self.assertEqual(self.l.command.call_count, 1, "Cache seems to not be used")
