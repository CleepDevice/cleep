#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Blkid ↔ /sbin/blkid (real binary)."""

import unittest
import logging
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.blkid import Blkid
from cleep.libs.tests.functional_helpers import setup_functional

BLKID_KEYS = ("device", "uuid", "type", "partuuid")


@pytest.mark.functional
class BlkidFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/sbin/blkid")
        self.b = Blkid()

    def test_get_devices_and_lookups(self):
        devices = self.b.get_devices()
        logging.info(devices)
        self.assertTrue(len(devices) > 0, "blkid returned no devices")
        device = next(iter(devices.values()))
        for key in BLKID_KEYS:
            self.assertIn(key, device)
        self.assertTrue(device["device"].startswith("/dev/"))
        self.assertEqual(self.b.get_device(device["device"]), device)
        self.assertEqual(self.b.get_device_by_uuid(device["uuid"]), device)
        self.assertEqual(self.b.get_device_by_partuuid(device["partuuid"]), device)
        self.assertIsNone(self.b.get_device_by_uuid("cleep-nonexistent-uuid"))
        self.assertIsNone(self.b.get_device("cleep_nonexistent_device"))
