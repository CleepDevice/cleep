#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functional tests for libs/commands: real OS binaries, no stdout mocks.

Opt-in via CLEEP_FUNCTIONAL_TESTS / ``cleep-cli coretests --functional``.
Missing binaries fail hard (OS migration signal), they do not skip.
"""

import os
import unittest
import logging
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.tests.common import get_log_level
from cleep.libs.commands.lsblk import Lsblk
from cleep.libs.commands.lsmod import Lsmod
from cleep.libs.commands.blkid import Blkid
from cleep.libs.commands.udevadm import Udevadm
from cleep.libs.commands.ifconfig import Ifconfig
from cleep.libs.commands.ip import Ip
from cleep.libs.commands.rfkill import Rfkill
from cleep.libs.commands.systemctl import Systemctl
from cleep.libs.commands.alsa import Alsa
from cleep.libs.commands.iw import Iw
from cleep.libs.commands.iwconfig import Iwconfig
from cleep.libs.commands.iwlist import Iwlist
from cleep.libs.commands.iwgetid import Iwgetid
from cleep.libs.commands.wpacli import Wpacli
from unittest.mock import Mock

LOG_LEVEL = get_log_level()

LSBLK_PARTITION_KEYS = (
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

IFCONFIG_KEYS = (
    "mac",
    "interface",
    "ipv4",
    "gateway_ipv4",
    "netmask_ipv4",
    "ipv6",
    "gateway_ipv6",
    "netmask_ipv6",
)

IP_STATUS_KEYS = (
    "interface",
    "ipv4",
    "netmask",
    "ipv6",
    "prefixlen",
    "mac",
)


def _setup_functional(test_case):
    TestLib(test_case).set_functional_tests()
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
    )


@pytest.mark.functional
class LsblkFunctionalTests(unittest.TestCase):

    def setUp(self):
        _setup_functional(self)
        TestLib.require_binary("/bin/lsblk")
        self.l = Lsblk()

    def test_get_devices_infos_contract(self):
        infos = self.l.get_devices_infos()
        logging.info(infos)
        self.assertTrue(len(infos) > 0, "lsblk returned no drives")
        drive = next(iter(infos.values()))
        part = next(iter(drive.values()))
        for key in LSBLK_PARTITION_KEYS:
            self.assertIn(key, part)

    def test_get_drives_and_partitions(self):
        drives = self.l.get_drives()
        partitions = self.l.get_partitions()
        self.assertTrue(len(drives) > 0)
        self.assertTrue(len(partitions) > 0)
        drive_name = next(iter(drives.keys()))
        self.assertIsNotNone(self.l.get_device_infos(drive_name))


@pytest.mark.functional
class LsmodFunctionalTests(unittest.TestCase):

    def setUp(self):
        _setup_functional(self)
        TestLib.require_binary("/bin/lsmod")
        self.l = Lsmod()

    def test_get_loaded_modules(self):
        mods = self.l.get_loaded_modules()
        logging.info(mods)
        self.assertTrue(len(mods) > 0, "lsmod returned no modules")
        self.assertFalse(self.l.is_module_loaded("cleep_nonexistent_module_xyz"))


@pytest.mark.functional
class BlkidFunctionalTests(unittest.TestCase):

    def setUp(self):
        _setup_functional(self)
        TestLib.require_binary("/sbin/blkid")
        self.b = Blkid()

    def test_get_devices_contract(self):
        devices = self.b.get_devices()
        logging.info(devices)
        self.assertTrue(len(devices) > 0, "blkid returned no devices")
        device = next(iter(devices.values()))
        for key in ("device", "uuid", "type", "partuuid"):
            self.assertIn(key, device)
        self.assertTrue(device["device"].startswith("/dev/"))


@pytest.mark.functional
class UdevadmFunctionalTests(unittest.TestCase):

    def setUp(self):
        _setup_functional(self)
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
        self.assertIn(
            dtype,
            (
                Udevadm.TYPE_UNKNOWN,
                Udevadm.TYPE_ATA,
                Udevadm.TYPE_USB,
                Udevadm.TYPE_SDCARD,
                Udevadm.TYPE_MMC,
            ),
        )


@pytest.mark.functional
class IfconfigFunctionalTests(unittest.TestCase):

    def setUp(self):
        _setup_functional(self)
        self.i = Ifconfig()

    def test_get_configurations_contract(self):
        interfaces = self.i.get_configurations()
        logging.info(interfaces)
        self.assertFalse("lo" in interfaces)
        self.assertGreaterEqual(len(interfaces), 1, "netifaces returned no interfaces")
        iface = next(iter(interfaces.values()))
        for key in IFCONFIG_KEYS:
            self.assertIn(key, iface)


@pytest.mark.functional
class IpFunctionalTests(unittest.TestCase):

    def setUp(self):
        _setup_functional(self)
        TestLib.require_binary("/sbin/ip")
        self.i = Ip()

    def test_is_installed(self):
        self.assertTrue(self.i.is_installed())

    def test_get_status_contract(self):
        status = self.i.get_status()
        logging.info(status)
        self.assertTrue(len(status) > 0, "ip addr returned no interfaces")
        entry = next(iter(status.values()))
        for key in IP_STATUS_KEYS:
            self.assertIn(key, entry)


@pytest.mark.functional
class RfkillFunctionalTests(unittest.TestCase):

    def setUp(self):
        _setup_functional(self)
        TestLib.require_binary("/usr/sbin/rfkill")
        self.r = Rfkill()

    def test_is_installed(self):
        self.assertTrue(self.r.is_installed())

    def test_get_wifi_infos_shape(self):
        infos = self.r.get_wifi_infos()
        logging.info(infos)
        # No wifi adapter is possible on some boards; None is a valid result.
        # Failure mode is command/binary missing (require_binary) or parse error.
        if infos is not None:
            for key in ("device", "id", "desc", "blocked"):
                self.assertIn(key, infos)


@pytest.mark.functional
class SystemctlFunctionalTests(unittest.TestCase):

    def setUp(self):
        _setup_functional(self)
        TestLib.require_binary("/usr/bin/systemctl")
        self.s = Systemctl()

    def test_get_service_status_journald(self):
        status = self.s.get_service_status("systemd-journald")
        logging.info(status)
        self.assertIsNotNone(status, "systemctl show systemd-journald failed")
        for key in ("state", "substate", "pid", "path", "start", "stop", "restarts", "runtime", "command"):
            self.assertIn(key, status)
        self.assertIn(status["state"], ("active", "inactive", "failed", "activating", "deactivating", "maintenance", "reloading", "refreshing"))


@pytest.mark.functional
class AlsaFunctionalTests(unittest.TestCase):

    def setUp(self):
        _setup_functional(self)
        TestLib.require_binary("/usr/bin/aplay")
        TestLib.require_binary("/usr/bin/amixer")
        self.a = Alsa(Mock())

    def test_get_playback_devices(self):
        devices = self.a.get_playback_devices()
        logging.info(devices)
        # Empty cards possible on headless without audio; binary must exist.
        # If aplay fails internally, wrapper typically returns {}.
        self.assertIsInstance(devices, dict)


@pytest.mark.functional
class IwFunctionalTests(unittest.TestCase):

    def setUp(self):
        _setup_functional(self)
        TestLib.require_binary("/sbin/iw")
        self.i = Iw()

    def test_is_installed_and_get_adapters(self):
        self.assertTrue(self.i.is_installed())
        adapters = self.i.get_adapters()
        logging.info(adapters)
        self.assertIsInstance(adapters, dict)
        for entry in adapters.values():
            self.assertIn("interface", entry)
            self.assertIn("network", entry)


@pytest.mark.functional
class IwconfigFunctionalTests(unittest.TestCase):

    def setUp(self):
        _setup_functional(self)
        TestLib.require_binary("/sbin/iwconfig")
        self.i = Iwconfig()

    def test_get_interfaces(self):
        interfaces = self.i.get_interfaces()
        logging.info(interfaces)
        self.assertIsInstance(interfaces, dict)


@pytest.mark.functional
class IwlistFunctionalTests(unittest.TestCase):

    def setUp(self):
        _setup_functional(self)
        TestLib.require_binary("/sbin/iwlist")
        self.i = Iwlist()

    def test_binary_present(self):
        # Read-only smoke: binary must exist; scan needs a live interface and
        # may be empty — existence is the migration signal.
        self.assertTrue(os.path.exists("/sbin/iwlist"))


@pytest.mark.functional
class IwgetidFunctionalTests(unittest.TestCase):

    def setUp(self):
        _setup_functional(self)
        TestLib.require_binary("/sbin/iwgetid")
        self.i = Iwgetid()

    def test_get_connections(self):
        connections = self.i.get_connections()
        logging.info(connections)
        self.assertIsInstance(connections, dict)


@pytest.mark.functional
class WpacliFunctionalTests(unittest.TestCase):

    def setUp(self):
        _setup_functional(self)
        TestLib.require_binary("/sbin/wpa_cli")
        self.w = Wpacli()

    def test_get_configured_networks(self):
        networks = self.w.get_configured_networks()
        logging.info(networks)
        self.assertIsInstance(networks, dict)
        for entry in networks.values():
            for key in ("id", "ssid", "bssid", "status"):
                self.assertIn(key, entry)
