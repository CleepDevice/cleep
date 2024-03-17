#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace("tests/", ""))
from fstab import Fstab
from cleep.exception import MissingParameter
from cleep.libs.tests.lib import TestLib, FileDescriptorMock
import unittest
from unittest.mock import Mock
import logging
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class FstabTests(unittest.TestCase):

    FILE_NAME = "fstab"
    CONTENT_STR = """# /etc/fstab: static file system information.
#
# Use 'blkid' to print the universally unique identifier for a
# device; this may be used with UUID= as a more robust way to name devices
# that works even if disks are added and removed. See fstab(5).
#
# <file system> <mount point>   <type>  <options>       <dump>  <pass>
# / was on /dev/sda1 during installation
UUID=b8e3f3c7-6324-4f58-8009-eace60bda876 /               ext4    discard,noatime,commit=600,errors=remount-ro 0       1
# /home was on /dev/sda6 during installation
UUID=79b36e19-a291-4682-a153-545b956a0607 /home           ext4    discard,noatime,commit=600,defaults         0       2
# swap was on /dev/sda5 during installation
UUID=58337582-3a9e-4a15-b4ad-4a7f354d9af3 none            swap    sw              0       0
/dev/sdb1       /media/usb0     auto    rw,user,noauto  0       0
/dev/sdb2       /media/usb1     auto    rw,user,noauto  0       0

#invalid type
TEST=b8e3f3c7-6324-4f58-8009-eace60bda876 /               ext4    discard,noatime,commit=600,errors=remount-ro 0       1

#server
192.168.1.1:/data/test       /media/test       nfs     soft,rw,nfsvers=3,rsize=32768,wsize=32768,timeo=600,actimeo=0,intr 0   0
desktop:/data/stuff       /media/stuff       nfs     soft,rw,nfsvers=3,rsize=32768,wsize=32768,timeo=600,actimeo=0,intr   0   0
192.168.1.1:/data/toserver       /media/toserver       nfs    soft,rw,nfsvers=3,rsize=32768,wsize=32768,timeo=600,actimeo=0,intr  0   0

#media
#192.168.1.10:/media/backup /media/media    nfs rsize=8192,wsize=8192,timeo=14,intr,vers=3

#store
192.168.1.53:/media/raid    /media/store    nfs     soft,rw,nfsvers=3,rsize=32768,wsize=32768,timeo=600,actimeo=0,intr  0   0"""

    BLKID = {
        "/dev/mmcblk0p1": {
            "device": "/dev/mmcblk0p1",
            "uuid": "EBBA-157F",
            "type": "vfat",
            "partuuid": "b294e190-01",
        },
        "/dev/mmcblk0p2": {
            "device": "/dev/mmcblk0p2",
            "uuid": "b3ce35cd-ade9-4755-a4bb-1571e37fc1b9",
            "type": "ext4",
            "partuuid": "b294e190-02",
        },
    }

    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL, format="%(asctime)s %(name)s %(levelname)s : %(message)s"
        )

        self.fs = Mock()
        self.fs.open.return_value = FileDescriptorMock(content=self.CONTENT_STR)
        self.f = Fstab(self.fs, False)

        blkid = Mock()
        blkid.get_devices.return_value = self.BLKID
        self.f.blkid = blkid

    def test_get_mountpoints(self):
        mountpoints = self.f.get_mountpoints()
        self.assertEqual(len(mountpoints), 9)

        self.assertTrue("/media/usb1" in mountpoints)
        self.assertEqual(mountpoints["/media/usb1"]["local"], True)
        self.assertTrue("/media/toserver" in mountpoints)
        self.assertEqual(mountpoints["/media/toserver"]["local"], False)

    def test_get_all_devices(self):
        devices = self.f.get_all_devices()
        self.assertNotEqual(len(devices), 0)

    def test_add_mountpoint_invalid_parameters(self):
        self.assertRaises(
            MissingParameter,
            self.f.add_mountpoint,
            None,
            "/dev/sda1",
            "ext4",
            "discard,noatime",
        )
        self.assertRaises(
            MissingParameter,
            self.f.add_mountpoint,
            "/media/mount",
            None,
            "ext4",
            "discard,noatime",
        )
        self.assertRaises(
            MissingParameter,
            self.f.add_mountpoint,
            "/media/mount",
            "/dev/sda1",
            None,
            "discard,noatime",
        )
        self.assertRaises(
            MissingParameter,
            self.f.add_mountpoint,
            "/media/mount",
            "/dev/sda1",
            "ext4",
            None,
        )
        self.assertRaises(
            MissingParameter,
            self.f.add_mountpoint,
            "",
            "/dev/sda1",
            "ext4",
            "discard,noatime",
        )
        self.assertRaises(
            MissingParameter,
            self.f.add_mountpoint,
            "/media/mount",
            "",
            "ext4",
            "discard,noatime",
        )
        self.assertRaises(
            MissingParameter,
            self.f.add_mountpoint,
            "/media/mount",
            "/dev/sda1",
            "",
            "discard,noatime",
        )
        self.assertRaises(
            MissingParameter,
            self.f.add_mountpoint,
            "/media/mount",
            "/dev/sda1",
            "ext4",
            "",
        )

    def test_add_mountpoint(self):
        self.f.add = Mock()
        result = self.f.add_mountpoint("/dev/sda1", "/media/mount", "ext4", "discard,noatime")
        self.assertTrue(result)
        self.f.add.assert_called_with("\n/dev/sda1\t/media/mount\text4\tdiscard,noatime\t0\t0\n")

    def test_add_existing_mountpoint(self):
        result = self.f.add_mountpoint("/dev/sdb1", "/media/usb1", "ext4", "discard,noatime")

        self.assertFalse(result)

    def test_delete_unknown_mountpoint(self):
        result = self.f.delete_mountpoint("/dev/dummy")

        self.assertFalse(result)

    def test_delete_mountpoint(self):
        self.f.remove = Mock()

        result = self.f.delete_mountpoint("/media/store")
        
        self.assertTrue(result)
        self.f.remove.assert_called_with("192.168.1.53:/media/raid    /media/store    nfs     soft,rw,nfsvers=3,rsize=32768,wsize=32768,timeo=600,actimeo=0,intr  0   0")

    def test_delete_mountpoint_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.f.delete_mountpoint(None)
        self.assertEqual(cm.exception.message, 'Parameter "mountpoint" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.f.delete_mountpoint("")
        self.assertEqual(cm.exception.message, 'Parameter "mountpoint" is missing')

    def test_reload_fstab(self):
        self.f.console = Mock()
        self.f.console.command.return_value = {
            "returncode": 0
        }
        self.assertTrue(self.f.reload_fstab())

        self.f.console.command.return_value = {
            "returncode": 1,
        }
        self.assertFalse(self.f.reload_fstab())


if __name__ == "__main__":
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_fstab.py; coverage report -m -i
    unittest.main()
