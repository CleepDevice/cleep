#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace("tests/", ""))
from blkid import Blkid
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.exception import MissingParameter, InvalidParameter, CommandError
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pformat
from cleep.libs.tests.common import get_log_level
from unittest.mock import Mock

LOG_LEVEL = get_log_level()
CONTENT = [
    "/dev/mmcblk0p1: LABEL_FATBOOT=\"boot\" LABEL=\"boot\" UUID=\"EBBA-157F\" TYPE=\"vfat\" PARTUUID=\"b294e190-01\"",
    "/dev/mmcblk0p2: LABEL=\"rootfs\" UUID=\"b3ce35cd-ade9-4755-a4bb-1571e37fc1b9\" TYPE=\"ext4\" PARTUUID=\"b294e190-02\"",
    "/dev/mmcblk0: PTUUID=\"b294e190\" PTTYPE=\"dos\"",
]

class BlkidTests(unittest.TestCase):
    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL, format=u"%(asctime)s %(name)s %(levelname)s : %(message)s"
        )
        self.b = Blkid()
        self.b.command = Mock(return_value={"killed": False, "error": False, "stdout": CONTENT})

    def tearDown(self):
        pass

    def test_get_devices(self):
        devices = self.b.get_devices()
        logging.debug("Devices: %s" % devices)
        self.assertEqual(len(devices), 2, "Blkid should find 2 mountpoints")
        for device, _ in devices.items():
            self.assertTrue(
                device.find("/dev") != -1, "Device should contains /dev/xxx"
            )

    def test_get_device_by_uuid(self):
        devices = self.b.get_devices()
        logging.debug("Devices: %s" % self.b.devices)
        device = devices[list(devices.keys())[0]]
        logging.debug("Device: %s" % device)
        result = self.b.get_device_by_uuid(device[u"uuid"])
        self.assertEqual(result["device"], device["device"])

    def test_get_device_by_uuid_invalid_uuid(self):
        self.assertEqual(self.b.get_device_by_uuid("uuid"), None)

    def test_get_device_by_partuuid(self):
        devices = self.b.get_devices()
        logging.debug("Devices: %s" % self.b.devices)
        device = devices[list(devices.keys())[0]]
        logging.debug("Device: %s" % device)
        result = self.b.get_device_by_partuuid(device[u"partuuid"])
        self.assertEqual(result["device"], device["device"])

    def test_get_device_by_partuuid_invalid_partuuid(self):
        self.assertEqual(self.b.get_device_by_partuuid("uuid"), None)

    def test_get_device(self):
        devices = self.b.get_devices()
        mountpoint = list(devices.keys())[0]
        uuid = devices[mountpoint]
        self.assertEqual(self.b.get_device(mountpoint), uuid)

    def test_get_device_invalid_device(self):
        self.assertEqual(self.b.get_device("mountpoint"), None)


if __name__ == "__main__":
    # coverage run --omit="*lib/python*/*","*test_*.py" --concurrency=thread test_blkid.py; coverage report -m -i
    unittest.main()
