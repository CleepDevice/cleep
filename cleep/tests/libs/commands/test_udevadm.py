#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace("tests/", ""))
from udevadm import Udevadm
from cleep.libs.tests.lib import TestLib
import unittest
import logging
import time
from cleep.libs.tests.common import get_log_level
from unittest.mock import Mock

LOG_LEVEL = get_log_level()

UDEV_MMC = [
    "DEVPATH=/devices/platform/soc/3f202000.mmc/mmc_host/mmc0/mmc0:aaaa/block/mmcblk0",
    "DEVNAME=/dev/mmcblk0",
    "DEVTYPE=disk",
    "MAJOR=179",
    "MINOR=0",
    "SUBSYSTEM=block",
    "USEC_INITIALIZED=7279063",
    "ID_NAME=SC16G",
    "ID_SERIAL=0xa9cf4395",
    "ID_PATH=platform-3f202000.mmc",
    "ID_PATH_TAG=platform-3f202000_mmc",
    "ID_PART_TABLE_UUID=b294e190",
    "ID_PART_TABLE_TYPE=dos",
    "DEVLINKS=/dev/disk/by-id/mmc-SC16G_0xa9cf4395 /dev/disk/by-path/platform-3f202000.mmc",
    "TAGS=:systemd:",
]
UDEV_USB = [
    "DEVPATH=/devices/pci0000:00/0000:00:14.0/usb1/1-10/1-10:1.0/host6/target6:0:0/6:0:0:1/block/sdd",
    "DEVNAME=/dev/sdd",
    "DEVTYPE=disk",
    "DISKSEQ=25",
    "MAJOR=8",
    "MINOR=48",
    "SUBSYSTEM=block",
    "USEC_INITIALIZED=779625957662",
    "ID_BUS=usb",
    "ID_MODEL=MassStorageClass",
    "ID_MODEL_ENC=MassStorageClass",
    "ID_MODEL_ID=0749",
    "ID_SERIAL=Generic_MassStorageClass_000000001536-0:1",
    "ID_SERIAL_SHORT=000000001536",
    "ID_VENDOR=Generic",
    "ID_VENDOR_ENC=Generic\x20",
    "ID_VENDOR_ID=05e3",
    "ID_REVISION=1536",
    "ID_TYPE=disk",
    "ID_INSTANCE=0:1",
    "ID_USB_MODEL=MassStorageClass",
    "ID_USB_MODEL_ENC=MassStorageClass",
    "ID_USB_MODEL_ID=0749",
    "ID_USB_SERIAL=Generic_MassStorageClass_000000001536-0:1",
    "ID_USB_SERIAL_SHORT=000000001536",
    "ID_USB_VENDOR=Generic",
    "ID_USB_VENDOR_ENC=Generic\x20",
    "ID_USB_VENDOR_ID=05e3",
    "ID_USB_REVISION=1536",
    "ID_USB_TYPE=disk",
    "ID_USB_INSTANCE=0:1",
    "ID_USB_INTERFACES=:080650:",
    "ID_USB_INTERFACE_NUM=00",
    "ID_USB_DRIVER=usb-storage",
    "ID_PATH=pci-0000:00:14.0-usb-0:10:1.0-scsi-0:0:0:1",
    "ID_PATH_TAG=pci-0000_00_14_0-usb-0_10_1_0-scsi-0_0_0_1",
    "ID_PART_TABLE_UUID=11260904",
    "ID_PART_TABLE_TYPE=dos",
    "DEVLINKS=/dev/disk/by-path/pci-0000:00:14.0-usb-0:10:1.0-scsi-0:0:0:1 /dev/disk/by-diskseq/25 /dev/disk/by-id/usb-Generic_MassStorageClass_000000001536-0:1",
    "TAGS=:systemd:",
    "CURRENT_TAGS=:systemd:",
]
UDEV_SDCARD1 = [
    "DEVNAME=/dev/mmcblk0p1",
    "DEVTYPE=partition",
    "PARTN=1",
    "MAJOR=179",
    "MINOR=1",
    "SUBSYSTEM=block",
    "USEC_INITIALIZED=1040760689634",
    "ID_NAME=SU01G",
    "ID_SERIAL=0xb023b954",
    "ID_PATH=pci-0000:00:1a.0-usb-0:1.3:1.0-platform-rtsx_usb_sdmmc.2.auto",
    "ID_PATH_TAG=pci-0000_00_1a_0-usb-0_1_3_1_0-platform-rtsx_usb_sdmmc_2_auto",
    "ID_PART_TABLE_TYPE=atari",
    "ID_DRIVE_FLASH_SD=1",
    "ID_PART_ENTRY_SCHEME=atari",
    "ID_PART_ENTRY_TYPE=BGM",
    "ID_PART_ENTRY_NUMBER=1",
    "ID_PART_ENTRY_OFFSET=2",
    "ID_PART_ENTRY_SIZE=131072",
    "ID_PART_ENTRY_DISK=179:0",
    "DEVLINKS=/dev/disk/by-id/mmc-SU01G_0xb023b954-part1/dev/disk/by-path/pci-0000:00:1a.0-usb-0:1.3:1.0-platform-rtsx_usb_sdmmc.2.auto-part1",
    "TAGS=:systemd:",
]
UDEV_SDCARD2 = [
    "DEVNAME=/dev/mmcblk0p1",
    "DEVTYPE=partition",
    "PARTN=1",
    "MAJOR=179",
    "MINOR=1",
    "SUBSYSTEM=block",
    "USEC_INITIALIZED=1040760689634",
    "ID_NAME=SU01G",
    "ID_SERIAL=0xb023b954",
    "ID_PATH=pci-0000:00:1a.0-usb-0:1.3:1.0-platform-rtsx_usb_sdmmc.2.auto",
    "ID_PATH_TAG=pci-0000_00_1a_0-usb-0_1_3_1_0-platform-rtsx_usb_sdmmc_2_auto",
    "ID_PART_TABLE_TYPE=atari",
    "ID_DRIVE_MEDIA_FLASH_SD=1",
    "ID_PART_ENTRY_SCHEME=atari",
    "ID_PART_ENTRY_TYPE=BGM",
    "ID_PART_ENTRY_NUMBER=1",
    "ID_PART_ENTRY_OFFSET=2",
    "ID_PART_ENTRY_SIZE=131072",
    "ID_PART_ENTRY_DISK=179:0",
    "DEVLINKS=/dev/disk/by-id/mmc-SU01G_0xb023b954-part1/dev/disk/by-path/pci-0000:00:1a.0-usb-0:1.3:1.0-platform-rtsx_usb_sdmmc.2.auto-part1",
    "TAGS=:systemd:",
]
UDEV_SATA = [
    "DEVPATH=/devices/pci0000:00/0000:00:17.0/ata2/host1/target1:0:0/1:0:0:0/block/sda",
    "DEVNAME=/dev/sda",
    "DEVTYPE=disk",
    "DISKSEQ=2",
    "MAJOR=8",
    "MINOR=0",
    "SUBSYSTEM=block",
    "USEC_INITIALIZED=1771324",
    "ID_ATA=1",
    "ID_TYPE=disk",
    "ID_BUS=ata",
    "ID_MODEL=SanDisk_SDSSDH3_500G",
    "ID_MODEL_ENC=SanDisk\x20SDSSDH3\x20500G\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20",
    "ID_REVISION=415020RL",
    "ID_SERIAL=SanDisk_SDSSDH3_500G_22085H801878",
    "ID_SERIAL_SHORT=22085H801878",
    "ID_ATA_WRITE_CACHE=1",
    "ID_ATA_WRITE_CACHE_ENABLED=1",
    "ID_ATA_FEATURE_SET_PM=1",
    "ID_ATA_FEATURE_SET_PM_ENABLED=1",
    "ID_ATA_FEATURE_SET_SECURITY=1",
    "ID_ATA_FEATURE_SET_SECURITY_ENABLED=0",
    "ID_ATA_FEATURE_SET_SECURITY_ERASE_UNIT_MIN=2",
    "ID_ATA_FEATURE_SET_SECURITY_ENHANCED_ERASE_UNIT_MIN=2",
    "ID_ATA_FEATURE_SET_SECURITY_FROZEN=1",
    "ID_ATA_FEATURE_SET_SMART=1",
    "ID_ATA_FEATURE_SET_SMART_ENABLED=1",
    "ID_ATA_FEATURE_SET_APM=1",
    "ID_ATA_FEATURE_SET_APM_ENABLED=1",
    "ID_ATA_FEATURE_SET_APM_CURRENT_VALUE=254",
    "ID_ATA_DOWNLOAD_MICROCODE=1",
    "ID_ATA_SATA=1",
    "ID_ATA_SATA_SIGNAL_RATE_GEN2=1",
    "ID_ATA_SATA_SIGNAL_RATE_GEN1=1",
    "ID_ATA_ROTATION_RATE_RPM=0",
    "ID_WWN=0x5001b448b7cae3c0",
    "ID_WWN_WITH_EXTENSION=0x5001b448b7cae3c0",
    "ID_PATH=pci-0000:00:17.0-ata-2.0",
    "ID_PATH_TAG=pci-0000_00_17_0-ata-2_0",
    "ID_PATH_ATA_COMPAT=pci-0000:00:17.0-ata-2",
    "ID_PART_TABLE_UUID=faf746cd-98cf-405c-9778-24157b3a0037",
    "ID_PART_TABLE_TYPE=gpt",
    "DEVLINKS=/dev/disk/by-path/pci-0000:00:17.0-ata-2.0 /dev/disk/by-id/ata-SanDisk_SDSSDH3_500G_22085H801878 /dev/disk/by-path/pci-0000:00:17.0-ata-2 /dev/disk/by-diskseq/2 /dev/disk/by-id/wwn-0x5001b448b7cae3c0",
    "TAGS=:systemd:",
    "CURRENT_TAGS=:systemd:",
]

class LsblkTests(unittest.TestCase):
    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL,
            format=u"%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
        )
        self.u = Udevadm()

    def tearDown(self):
        pass

    def test_get_device_type_mmc(self):
        self.u.command = Mock(return_value={
            "killed": False,
            "error": False,
            "stdout": UDEV_MMC,
        })

        mmcblk0 = self.u.get_device_type("mmcblk0")
        logging.debug("Mmcblk0: %s" % mmcblk0)

        self.assertEqual(mmcblk0, self.u.TYPE_MMC)

    def test_get_device_type_usb(self):
        self.u.command = Mock(return_value={
            "killed": False,
            "error": False,
            "stdout": UDEV_USB,
        })

        mmcblk0 = self.u.get_device_type("mmcblk0")
        logging.debug("Mmcblk0: %s" % mmcblk0)

        self.assertEqual(mmcblk0, self.u.TYPE_USB)

    def test_get_device_type_sdcard1(self):
        self.u.command = Mock(return_value={
            "killed": False,
            "error": False,
            "stdout": UDEV_SDCARD1,
        })

        mmcblk0 = self.u.get_device_type("mmcblk0")
        logging.debug("Mmcblk0: %s" % mmcblk0)

        self.assertEqual(mmcblk0, self.u.TYPE_SDCARD)

    def test_get_device_type_sdcard2(self):
        self.u.command = Mock(return_value={
            "killed": False,
            "error": False,
            "stdout": UDEV_SDCARD2,
        })

        mmcblk0 = self.u.get_device_type("mmcblk0")
        logging.debug("Mmcblk0: %s" % mmcblk0)

        self.assertEqual(mmcblk0, self.u.TYPE_SDCARD)

    def test_get_device_type_sata1(self):
        self.u.command = Mock(return_value={
            "killed": False,
            "error": False,
            "stdout": UDEV_SATA,
        })

        mmcblk0 = self.u.get_device_type("mmcblk0")
        logging.debug("Mmcblk0: %s" % mmcblk0)

        self.assertEqual(mmcblk0, self.u.TYPE_ATA)

    def test_get_device_type_sata2(self):
        self.u.command = Mock(return_value={
            "killed": False,
            "error": False,
            "stdout": filter(lambda item: item.startswith('ID_BUS'), UDEV_SATA),
        })

        mmcblk0 = self.u.get_device_type("mmcblk0")
        logging.debug("Mmcblk0: %s" % mmcblk0)

        self.assertEqual(mmcblk0, self.u.TYPE_ATA)

    def test_use_cache(self):
        tick = time.time()
        self.u.get_device_type("mmcblk0")
        without_cache_duration = time.time() - tick
        tick = time.time()
        self.u.get_device_type("mmcblk0")
        with_cache_duration = time.time() - tick
        self.assertLess(
            with_cache_duration, without_cache_duration, "Cache seems to not be used"
        )


if __name__ == "__main__":
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_udevadm.py; coverage report -m -i
    unittest.main()
