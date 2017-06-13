#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter
from raspiot.libs.dhcpcdconf import DhcpcdConf
import unittest
import os

class dhcpcdConfTests_validConf(unittest.TestCase):
    def setUp(self):
        #fake conf file
        fd = open('dhcpcd.fake.conf', 'w')
        fd.write("""# A sample configuration for dhcpcd.
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
static domain_name_servers=192.168.1.1""")
        fd.close()

        self.d = DhcpcdConf(backup=False)
        self.d.CONF = 'dhcpcd.fake.conf'

    def tearDown(self):
        os.remove('dhcpcd.fake.conf')

    def test_get_interfaces(self):
        interfaces = self.d.get_interfaces()
        self.assertEqual(len(interfaces), 1)
        self.assertTrue(interfaces.has_key('eth0'))
        self.assertEqual(interfaces['eth0']['interface'], 'eth0')
        self.assertEqual(interfaces['eth0']['ip_address'], '192.168.1.250')
        self.assertEqual(interfaces['eth0']['routers'], '192.168.1.1')
        self.assertEqual(interfaces['eth0']['domain_name_servers'], '192.168.1.1')

    def test_add_static_interface_missing_parameter(self):
        self.assertRaises(MissingParameter, self.d.add_static_interface, None, '192.168.1.123', '192.168.1.1', '192.168.1.1')
        self.assertRaises(MissingParameter, self.d.add_static_interface, '', '192.168.1.123', '192.168.1.1', '192.168.1.1')
        self.assertRaises(MissingParameter, self.d.add_static_interface, 'eth2', None, '192.168.1.1', '192.168.1.1')
        self.assertRaises(MissingParameter, self.d.add_static_interface, 'eth2', '', '192.168.1.1', '192.168.1.1')
        self.assertRaises(MissingParameter, self.d.add_static_interface, 'eth2', '192.168.1.123', None, '192.168.1.1')
        self.assertRaises(MissingParameter, self.d.add_static_interface, 'eth2', '192.168.1.123', '', '192.168.1.1')
        self.assertRaises(MissingParameter, self.d.add_static_interface, 'eth2', '192.168.1.123', '192.168.1.1', None)
        self.assertRaises(MissingParameter, self.d.add_static_interface, 'eth2', '192.168.1.123', '192.168.1.1', '')

    def test_add_static_interface_invalid_parameter(self):
        self.assertRaises(InvalidParameter, self.d.add_static_interface, 'eth0', '192.168.1.123', '192.168.1.1', '192.168.1.1')

    def test_add_interface(self):
        self.assertTrue(self.d.add_static_interface('eth1', '10.30.1.255', '10.30.1.1', '10.30.1.2'))
        interfaces = self.d.get_interfaces()
        self.assertEqual(len(interfaces), 2)
        interface = self.d.get_interface('eth1')
        self.assertIsNotNone(interface)
        self.assertEqual(interface['interface'], 'eth1')
        self.assertEqual(interface['ip_address'], '10.30.1.255')
        self.assertEqual(interface['routers'], '10.30.1.1')
        self.assertEqual(interface['domain_name_servers'], '10.30.1.2')

    def test_delete_interface_missing_parameter(self):
        self.assertRaises(MissingParameter, self.d.delete_static_interface, None)
        self.assertRaises(MissingParameter, self.d.delete_static_interface, '')

    def test_delete_interface_invalid_parameter(self):
        self.assertFalse(self.d.delete_static_interface('eth1'))
        
    def test_delete_interface(self):
        self.assertTrue(self.d.add_static_interface('eth1', '10.30.1.255', '10.30.1.1', '10.30.1.2'))
        self.assertEqual(len(self.d.get_interfaces()), 2)
        self.assertTrue(self.d.delete_static_interface('eth1'))
        self.assertEqual(len(self.d.get_interfaces()), 1)


class dhcpcdConfTests_profileConf(unittest.TestCase):
    def setUp(self):
        #fake conf file
        fd = open('dhcpcd.fake.conf', 'w')
        fd.write("""# A sample configuration for dhcpcd.
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
fallback fallback_eth1""")
        fd.close()

        self.d = DhcpcdConf(backup=False)
        self.d.CONF = 'dhcpcd.fake.conf'

    def tearDown(self):
        os.remove('dhcpcd.fake.conf')

    def test_get_interfaces(self):
        interfaces = self.d.get_interfaces()
        self.assertEqual(len(interfaces), 2)
        self.assertTrue(interfaces.has_key('eth0'))
        self.assertEqual(interfaces['eth0']['interface'], 'eth0')
        self.assertEqual(interfaces['eth0']['ip_address'], '192.168.0.10')
        self.assertEqual(interfaces['eth0']['routers'], '192.168.0.1')
        self.assertEqual(interfaces['eth0']['domain_name_servers'], '192.168.0.1 8.8.8.8')

    def test_add_static_interface_missing_parameter(self):
        self.assertRaises(MissingParameter, self.d.add_static_interface, None, '192.168.1.123', '192.168.1.1', '192.168.1.1')
        self.assertRaises(MissingParameter, self.d.add_static_interface, '', '192.168.1.123', '192.168.1.1', '192.168.1.1')
        self.assertRaises(MissingParameter, self.d.add_static_interface, 'eth2', None, '192.168.1.1', '192.168.1.1')
        self.assertRaises(MissingParameter, self.d.add_static_interface, 'eth2', '', '192.168.1.1', '192.168.1.1')
        self.assertRaises(MissingParameter, self.d.add_static_interface, 'eth2', '192.168.1.123', None, '192.168.1.1')
        self.assertRaises(MissingParameter, self.d.add_static_interface, 'eth2', '192.168.1.123', '', '192.168.1.1')
        self.assertRaises(MissingParameter, self.d.add_static_interface, 'eth2', '192.168.1.123', '192.168.1.1', None)
        self.assertRaises(MissingParameter, self.d.add_static_interface, 'eth2', '192.168.1.123', '192.168.1.1', '')

    def test_add_static_interface_invalid_parameter(self):
        self.assertRaises(InvalidParameter, self.d.add_static_interface, 'eth0', '192.168.1.123', '192.168.1.1', '192.168.1.1')

    def test_add_interface(self):
        self.assertTrue(self.d.add_static_interface('eth2', '10.30.1.255', '10.30.1.1', '10.30.1.2'))
        interfaces = self.d.get_interfaces()
        self.assertEqual(len(interfaces), 3)
        interface = self.d.get_interface('eth2')
        self.assertIsNotNone(interface)
        self.assertEqual(interface['interface'], 'eth2')
        self.assertEqual(interface['ip_address'], '10.30.1.255')
        self.assertEqual(interface['routers'], '10.30.1.1')
        self.assertEqual(interface['domain_name_servers'], '10.30.1.2')

    def test_delete_interface_missing_parameter(self):
        self.assertRaises(MissingParameter, self.d.delete_static_interface, None)
        self.assertRaises(MissingParameter, self.d.delete_static_interface, '')

    def test_delete_interface_invalid_parameter(self):
        self.assertFalse(self.d.delete_static_interface('eth4'))
        
    def test_delete_interface(self):
        self.assertTrue(self.d.add_static_interface('eth3', '10.30.1.255', '10.30.1.1', '10.30.1.2'))
        self.assertEqual(len(self.d.get_interfaces()), 3)
        self.assertTrue(self.d.delete_static_interface('eth3'))
        self.assertEqual(len(self.d.get_interfaces()), 2)

    def test_add_fallback_interface(self):
        self.assertTrue(self.d.add_fallback_interface('eth6', '12.12.12.12', '12.12.12.1', '12.12.12.20'))
        interfaces = self.d.get_interfaces()
        self.assertEqual(len(interfaces), 3)
        interface = self.d.get_interface('eth6')
        self.assertIsNotNone(interface)
        self.assertEqual(interface['interface'], 'eth6')
        self.assertEqual(interface['ip_address'], '12.12.12.12')
        self.assertEqual(interface['routers'], '12.12.12.1')
        self.assertEqual(interface['domain_name_servers'], '12.12.12.20')
        self.assertTrue(interface['fallback'])

    def test_delete_fallback_interface(self):
        self.assertTrue(self.d.add_fallback_interface('eth6', '12.12.12.12', '12.12.12.14', '12.12.12.16'))
        self.assertEqual(len(self.d.get_interfaces()), 3)
        self.assertTrue(self.d.delete_fallback_interface('eth6'))
        self.assertEqual(len(self.d.get_interfaces()), 2)

