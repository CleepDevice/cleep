#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace("tests/", ""))
from dhcpcdconf import DhcpcdConf
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.exception import MissingParameter, InvalidParameter, CommandError
from cleep.libs.tests.lib import TestLib, FileDescriptorMock
import unittest
import logging
from pprint import pformat
import io
from cleep.libs.tests.common import get_log_level
from mock import Mock, patch

LOG_LEVEL = get_log_level()
VALID_CONF = """# A sample configuration for dhcpcd.
# See dhcpcd.conf(5) for details.

# Allow users of this group to interact with dhcpcd via the control socket.
#controlgroup wheel

# Inform the DHCP server of our hostname for DDNS.
hostname

# Use the hardware address of the interface for the Client ID.
clientid
# or
# Use the same DUID + IAID as set in DHCPv6 for DHCPv4 ClientID as per RFC4361.
#duid

# Persist interface configuration when dhcpcd exits.
persistent

# Rapid commit support.
# Safe to enable by default because it requires the equivalent option set
# on the server to actually work.
option rapid_commit

# A list of options to request from the DHCP server.
option domain_name_servers, domain_name, domain_search, host_name
option classless_static_routes
# Most distributions have NTP support.
option ntp_servers
# Respect the network MTU.
# Some interface drivers reset when changing the MTU so disabled by default.
#option interface_mtu

# A ServerID is required by RFC2131.
require dhcp_server_identifier

# Generate Stable Private IPv6 Addresses instead of hardware based ones
slaac private

# A hook script is provided to lookup the hostname if not set by the DHCP
# server, but it should not be run by default.
nohook lookup-hostname

interface eth0
static ip_address=192.168.1.250/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1"""
PROFILE_CONF = """# A sample configuration for dhcpcd.
# See dhcpcd.conf(5) for details.

# Allow users of this group to interact with dhcpcd via the control socket.
#controlgroup wheel

# Inform the DHCP server of our hostname for DDNS.
hostname

# Use the hardware address of the interface for the Client ID.
clientid
# or
# Use the same DUID + IAID as set in DHCPv6 for DHCPv4 ClientID as per RFC4361.
#duid

# Persist interface configuration when dhcpcd exits.
persistent

# Rapid commit support.
# Safe to enable by default because it requires the equivalent option set
# on the server to actually work.
option rapid_commit

# A list of options to request from the DHCP server.
option domain_name_servers, domain_name, domain_search, host_name
option classless_static_routes
# Most distributions have NTP support.
option ntp_servers
# Respect the network MTU.
# Some interface drivers reset when changing the MTU so disabled by default.
#option interface_mtu

# A ServerID is required by RFC2131.
require dhcp_server_identifier

# Generate Stable Private IPv6 Addresses instead of hardware based ones
slaac private

# A hook script is provided to lookup the hostname if not set by the DHCP
# server, but it should not be run by default.
nohook lookup-hostname

# define static profile
profile fallback_eth1

static ip_address=192.168.1.23/24
static routers=192.168.1.1
#static routers=192.168.1.2
static domain_name_servers=192.168.1.1

interface eth0
static ip_address=192.168.0.10/24       
static routers=192.168.0.1
static domain_name_servers=192.168.0.1 8.8.8.8

# fallback to static profile on eth0
interface eth1
fallback fallback_eth1"""

class dhcpcdConfTests_validConf(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL, format=u"%(asctime)s %(name)s %(levelname)s : %(message)s"
        )

        self.fs = Mock()
        self.fs.open.return_value = FileDescriptorMock(content=VALID_CONF)
        self.d = DhcpcdConf(self.fs, backup=False)

    @patch("dhcpcdconf.os.path.exists")
    @patch("dhcpcdconf.Console")
    def test_is_installed(self, console_mock, os_path_exists_mock):
        os_path_exists_mock.return_value = True
        console_mock.return_value.command.return_value = {
            "error": False,
            "killed": False,
            "stdout": ["1"],
        }
        self.assertTrue(self.d.is_installed())

        os_path_exists_mock.return_value = True
        console_mock.return_value.command.return_value = {
            "error": False,
            "killed": False,
            "stdout": ["0"],
        }
        self.assertFalse(self.d.is_installed())

        os_path_exists_mock.return_value = True
        console_mock.return_value.command.return_value = {
            "error": True,
            "killed": False,
            "stdout": [],
        }
        self.assertFalse(self.d.is_installed())

        os_path_exists_mock.return_value = False
        self.assertFalse(self.d.is_installed())

    def test_get_configurations(self):
        interfaces = self.d.get_configurations()
        self.assertEqual(len(interfaces), 1)
        self.assertTrue("eth0" in interfaces)
        self.assertEqual(interfaces["eth0"]["interface"], "eth0")
        self.assertEqual(interfaces["eth0"]["ip_address"], "192.168.1.250")
        self.assertEqual(interfaces["eth0"]["gateway"], "192.168.1.1")
        self.assertEqual(interfaces["eth0"]["dns_address"], "192.168.1.1")

    def test_get_configuration_invalid_params(self):
        with self.assertRaises(MissingParameter) as cm:
            self.d.get_configuration(None)
        self.assertEqual(cm.exception.message, 'Parameter "interface" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.d.get_configuration("")
        self.assertEqual(cm.exception.message, 'Parameter "interface" is missing')

    def test_add_static_interface_missing_parameter(self):
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            None,
            "192.168.1.123",
            "192.168.1.1",
            "192.168.1.1",
        )
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            "",
            "192.168.1.123",
            "192.168.1.1",
            "192.168.1.1",
        )
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            "eth2",
            None,
            "192.168.1.1",
            "192.168.1.1",
        )
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            "eth2",
            "",
            "192.168.1.1",
            "192.168.1.1",
        )
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            "eth2",
            "192.168.1.123",
            None,
            "192.168.1.1",
        )
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            "eth2",
            "192.168.1.123",
            "",
            "192.168.1.1",
        )
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            "eth2",
            "192.168.1.123",
            "192.168.1.1",
            None,
        )
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            "eth2",
            "192.168.1.123",
            "192.168.1.1",
            "",
        )

    def test_add_static_interface_invalid_parameter(self):
        self.assertRaises(
            InvalidParameter,
            self.d.add_static_interface,
            "eth0",
            "192.168.1.123",
            "192.168.1.1",
            "192.168.1.1",
        )

    def test_add_static_interface(self):
        self.d.add_lines = Mock()

        result = self.d.add_static_interface(
            "eth1", "10.30.1.255", "10.30.1.1", "10.255.255.255", "10.30.1.2"
        )
        
        self.assertTrue(result)
        self.d.add_lines.assert_called_with([
            '\ninterface eth1\n',
            'static ip_address=10.30.1.255/26\n',
            'static routers=10.30.1.1\n',
            'static domain_name_servers=10.30.1.2\n'
        ])

    def test_add_static_interface_without_dns(self):
        self.d.add_lines = Mock()

        result = self.d.add_static_interface(
            "eth1", "10.30.1.255", "10.30.1.1", "10.255.255.255"
        )
        
        self.assertTrue(result)
        self.d.add_lines.assert_called_with([
            '\ninterface eth1\n',
            'static ip_address=10.30.1.255/26\n',
            'static routers=10.30.1.1\n',
            'static domain_name_servers=10.30.1.1\n'
        ])

    def test_delete_interface_missing_parameter(self):
        self.assertRaises(MissingParameter, self.d.delete_interface, None)
        self.assertRaises(MissingParameter, self.d.delete_interface, "")

    def test_delete_interface_invalid_parameter(self):
        self.assertFalse(self.d.delete_interface("eth1"))

    def test_delete_interface_static(self):
        self.d.remove_after = Mock()
        self.d.remove_after.return_value = 4

        result = self.d.delete_interface("eth0")

        self.assertTrue(result)
        self.d.remove_after.assert_called_with('^\\s*interface\\s*eth0\\s*$', '^\\s*static.*$', 4)

    def test_delete_interface_invalid_interface(self):
        self.assertFalse(self.d.delete_interface("eth666"))


class dhcpcdConfTests_profileConf(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL, format=u"%(asctime)s %(name)s %(levelname)s : %(message)s"
        )

        self.fs = Mock()
        self.fs.open.return_value = FileDescriptorMock(content=PROFILE_CONF)
        self.d = DhcpcdConf(self.fs, backup=False)

    def test_get_configurations(self):
        interfaces = self.d.get_configurations()
        logging.debug("interfaces=%s", interfaces)

        self.assertEqual(len(interfaces), 3)
        self.assertTrue("eth0" in interfaces)
        self.assertTrue("eth1" in interfaces)
        self.assertTrue("fallback_eth1" in interfaces)
        self.assertEqual(interfaces["eth0"]["interface"], "eth0")
        self.assertEqual(interfaces["eth0"]["ip_address"], "192.168.0.10")
        self.assertEqual(interfaces["eth0"]["gateway"], "192.168.0.1")
        self.assertEqual(interfaces["eth0"]["dns_address"], "192.168.0.1 8.8.8.8")

    def test_add_static_interface_missing_parameter(self):
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            None,
            "192.168.1.123",
            "192.168.1.1",
            "192.168.1.1",
        )
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            "",
            "192.168.1.123",
            "192.168.1.1",
            "192.168.1.1",
        )
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            "eth2",
            None,
            "192.168.1.1",
            "192.168.1.1",
        )
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            "eth2",
            "",
            "192.168.1.1",
            "192.168.1.1",
        )
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            "eth2",
            "192.168.1.123",
            None,
            "192.168.1.1",
        )
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            "eth2",
            "192.168.1.123",
            "",
            "192.168.1.1",
        )
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            "eth2",
            "192.168.1.123",
            "192.168.1.1",
            None,
        )
        self.assertRaises(
            MissingParameter,
            self.d.add_static_interface,
            "eth2",
            "192.168.1.123",
            "192.168.1.1",
            "",
        )

    def test_add_static_interface_invalid_parameter(self):
        self.assertRaises(
            InvalidParameter,
            self.d.add_static_interface,
            "eth0",
            "192.168.1.123",
            "192.168.1.1",
            "192.255.255.255",
            "192.168.1.1",
        )

    def test_add_static_interface(self):
        self.d.add_lines = Mock(return_value=True)

        result = self.d.add_static_interface(
            "eth2", "10.30.1.255", "10.30.1.1", "10.255.255.255", "10.30.1.2"
        )

        self.assertTrue(result)
        self.d.add_lines.assert_called_with([
            '\ninterface eth2\n',
            'static ip_address=10.30.1.255/26\n',
            'static routers=10.30.1.1\n',
            'static domain_name_servers=10.30.1.2\n'
        ])

    def test_delete_interface_missing_parameter(self):
        self.assertRaises(MissingParameter, self.d.delete_interface, None)
        self.assertRaises(MissingParameter, self.d.delete_interface, "")

    def test_delete_interface_invalid_parameter(self):
        self.assertFalse(self.d.delete_interface("eth4"))

    def test_delete_interface(self):
        self.d.remove_after = Mock(side_effect=[2,4])

        result = self.d.delete_interface("eth1")

        self.assertTrue(result)
        self.d.remove_after.assert_any_call(rf"^\s*interface\s*eth1\s*$", r"^\s*fallback\s*(.*?)\s*$", 2)
        self.d.remove_after.assert_any_call(rf"^\s*profile\s*fallback_eth1\s*$", r"^\s*static.*$", 6)

    def test_delete_interface_removeing_interface_failed(self):
        self.d.remove_after = Mock(side_effect=[4,4])

        result = self.d.delete_interface("eth1")

        self.assertFalse(result)

    def test_delete_interface_removeing_fallback_interface_failed(self):
        self.d.remove_after = Mock(side_effect=[2,6])

        result = self.d.delete_interface("eth1")

        self.assertFalse(result)

    def test_add_fallback_interface(self):
        self.d.add_lines = Mock(return_value=True)

        result = self.d.add_fallback_interface(
            "eth6", "12.12.12.12", "12.12.12.1", "12.255.255.255", "12.12.12.20"
        )

        self.assertTrue(result)
        self.d.add_lines.assert_called_with([
            '\nprofile fallback_eth6\n',
            'static ip_address=12.12.12.12/26\n',
            'static routers=12.12.12.1\n',
            'static domain_name_servers=12.12.12.20\n',
            '\ninterface eth6\n',
            'fallback fallback_eth6\n'
        ])

    def test_add_fallback_interface_without_dns(self):
        self.d.add_lines = Mock(return_value=True)

        result = self.d.add_fallback_interface(
            "eth6", "12.12.12.12", "12.12.12.1", "12.255.255.255"
        )

        self.assertTrue(result)
        self.d.add_lines.assert_called_with([
            '\nprofile fallback_eth6\n',
            'static ip_address=12.12.12.12/26\n',
            'static routers=12.12.12.1\n',
            'static domain_name_servers=12.12.12.1\n',
            '\ninterface eth6\n',
            'fallback fallback_eth6\n'
        ])

    def test_add_fallback_interface_already_configured(self):
        with self.assertRaises(InvalidParameter) as cm:
            self.d.add_fallback_interface(
                "eth1", "12.12.12.12", "12.12.12.1", "12.255.255.255", "12.12.12.20"
            )
        self.assertEqual(cm.exception.message, "Interface eth1 is already configured")

    def test_add_fallback_interface_invalid_params(self):
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface(
                None, "12.12.12.12", "12.12.12.1", "12.255.255.255", "12.12.12.20"
            )
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface(
                "", "12.12.12.12", "12.12.12.1", "12.255.255.255", "12.12.12.20"
            )
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface(
                "eth1", None, "12.12.12.1", "12.255.255.255", "12.12.12.20"
            )
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface(
                "eth1", "", "12.12.12.1", "12.255.255.255", "12.12.12.20"
            )
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface(
                "eth1", "12.12.12.12", None, "12.255.255.255", "12.12.12.20"
            )
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface(
                "eth1", "12.12.12.12", "", "12.255.255.255", "12.12.12.20"
            )
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface(
                "eth1", "12.12.12.12", "12.12.12.1", None, "12.12.12.20"
            )
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface(
                "eth1", "12.12.12.12", "12.12.12.1", "", "12.12.12.20"
            )

    #def test_delete_fallback_interface(self):
    #    configurations = self.d.get_configurations()
    #    logging.debug("Configurations: %s" % configurations)
    #    logging.debug("Interfaces: %s" % list(configurations.keys()))
    #    self.assertTrue(
    #        self.d.add_fallback_interface(
    #            "eth6", "12.12.12.12", "12.12.12.14", "12.12.12.16"
    #        )
    #    )
    #    configurations = self.d.get_configurations()
    #    logging.debug("Configurations: %s" % configurations)
    #    logging.debug("Interfaces: %s" % list(configurations.keys()))
    #    self.assertEqual(len(configurations), 5)
    #    self.assertTrue(self.d.delete_interface("eth6"))
    #    self.assertEqual(len(self.d.get_configurations()), 3)


if __name__ == "__main__":
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_dhcpcdconf.py; coverage report -m -i
    unittest.main()
