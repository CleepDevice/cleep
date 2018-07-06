#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys 
sys.path.append('/root/cleep/raspiot/libs/configs')
from dhcpcdconf import DhcpcdConf
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.utils import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.tests.lib import TestLib, TRACE
import unittest
import logging
from pprint import pformat
import io

logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class dhcpcdConfTests_validConf(unittest.TestCase):

    FILENAME = 'dhcpcd.conf'

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILENAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fake conf file
        with io.open(self.FILENAME, 'w') as fd:
            fd.write(u"""# A sample configuration for dhcpcd.
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

        D = DhcpcdConf
        D.CONF = self.FILENAME
        self.d = D(self.fs, backup=False)

    def tearDown(self):
        if os.path.exists(self.FILENAME):
            os.remove(self.FILENAME)

    def test_is_installed(self):
        self.assertTrue(self.d.is_installed())
        os.remove(self.FILENAME)
        self.assertFalse(self.d.is_installed())

    def test_get_configurations(self):
        interfaces = self.d.get_configurations()
        self.assertEqual(len(interfaces), 1)
        self.assertTrue(interfaces.has_key('eth0'))
        self.assertEqual(interfaces['eth0']['interface'], 'eth0')
        self.assertEqual(interfaces['eth0']['ip_address'], '192.168.1.250')
        self.assertEqual(interfaces['eth0']['gateway'], '192.168.1.1')
        self.assertEqual(interfaces['eth0']['dns_address'], '192.168.1.1')

    def test_get_configuration_invalid_params(self):
        with self.assertRaises(MissingParameter) as cm:
            self.d.get_configuration(None)
        self.assertEqual(cm.exception.message, 'Parameter "interface" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.d.get_configuration('')
        self.assertEqual(cm.exception.message, 'Parameter "interface" is missing')

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
        self.assertTrue(self.d.add_static_interface('eth1', '10.30.1.255', '10.30.1.1', '10.255.255.255', '10.30.1.2'))
        interfaces = self.d.get_configurations()
        logging.debug(interfaces)
        self.assertEqual(len(interfaces), 2)
        interface = self.d.get_configuration('eth1')
        logging.debug(interface)
        self.assertIsNotNone(interface)
        self.assertEqual(interface['interface'], 'eth1')
        self.assertEqual(interface['ip_address'], '10.30.1.255')
        self.assertEqual(interface['gateway'], '10.30.1.1')
        self.assertEqual(interface['dns_address'], '10.30.1.2')

    def test_delete_interface_missing_parameter(self):
        self.assertRaises(MissingParameter, self.d.delete_interface, None)
        self.assertRaises(MissingParameter, self.d.delete_interface, '')

    def test_delete_interface_invalid_parameter(self):
        self.assertFalse(self.d.delete_interface('eth1'))
        
    def test_delete_interface(self):
        self.assertTrue(self.d.add_static_interface('eth1', '10.30.1.255', '10.30.1.1', '10.30.1.2'))
        self.assertEqual(len(self.d.get_configurations()), 2)
        self.assertTrue(self.d.delete_interface('eth1'))
        self.assertEqual(len(self.d.get_configurations()), 1)

    def test_delete_interface_invalid_interface(self):
        self.assertFalse(self.d.delete_interface('eth666'))


class dhcpcdConfTests_profileConf(unittest.TestCase):

    FILENAME = 'dhcpcd.conf'

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILENAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fake conf file
        with io.open(self.FILENAME, 'w') as fd:
            fd.write(u"""# A sample configuration for dhcpcd.
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

        D = DhcpcdConf
        D.CONF = self.FILENAME
        self.d = D(self.fs, backup=False)

    def tearDown(self):
        if os.path.exists(self.FILENAME):
            os.remove(self.FILENAME)

    def test_get_configurations(self):
        interfaces = self.d.get_configurations()
        self.assertEqual(len(interfaces), 2)
        self.assertTrue(interfaces.has_key('eth0'))
        self.assertEqual(interfaces['eth0']['interface'], 'eth0')
        self.assertEqual(interfaces['eth0']['ip_address'], '192.168.0.10')
        self.assertEqual(interfaces['eth0']['gateway'], '192.168.0.1')
        self.assertEqual(interfaces['eth0']['dns_address'], '192.168.0.1 8.8.8.8')

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
        self.assertRaises(InvalidParameter, self.d.add_static_interface, 'eth0', '192.168.1.123', '192.168.1.1', '192.255.255.255', '192.168.1.1')

    def test_add_interface(self):
        self.assertTrue(self.d.add_static_interface('eth2', '10.30.1.255', '10.30.1.1', '10.255.255.255', '10.30.1.2'))
        interfaces = self.d.get_configurations()
        self.assertEqual(len(interfaces), 3)
        interface = self.d.get_configuration('eth2')
        self.assertIsNotNone(interface)
        self.assertEqual(interface['interface'], 'eth2')
        self.assertEqual(interface['ip_address'], '10.30.1.255')
        self.assertEqual(interface['gateway'], '10.30.1.1')
        self.assertEqual(interface['dns_address'], '10.30.1.2')

    def test_delete_interface_missing_parameter(self):
        self.assertRaises(MissingParameter, self.d.delete_interface, None)
        self.assertRaises(MissingParameter, self.d.delete_interface, '')

    def test_delete_interface_invalid_parameter(self):
        self.assertFalse(self.d.delete_interface('eth4'))
        
    def test_delete_interface(self):
        self.assertTrue(self.d.add_static_interface('eth3', '10.30.1.255', '10.30.1.1', '10.255.255.255', '10.30.1.2'))
        self.assertEqual(len(self.d.get_configurations()), 3)
        self.assertTrue(self.d.delete_interface('eth3'))
        self.assertEqual(len(self.d.get_configurations()), 2)

    def test_add_fallback_interface(self):
        self.assertTrue(self.d.add_fallback_interface('eth6', '12.12.12.12', '12.12.12.1', '12.255.255.255', '12.12.12.20'))
        interfaces = self.d.get_configurations()
        self.assertEqual(len(interfaces), 3)
        interface = self.d.get_configuration('eth6')
        self.assertIsNotNone(interface)
        self.assertEqual(interface['interface'], 'eth6')
        self.assertEqual(interface['ip_address'], '12.12.12.12')
        self.assertEqual(interface['gateway'], '12.12.12.1')
        self.assertEqual(interface['dns_address'], '12.12.12.20')
        self.assertTrue(interface['fallback'])

    def test_add_fallback_interface_already_configured(self):
        with self.assertRaises(InvalidParameter) as cm:
            self.d.add_fallback_interface('eth1', '12.12.12.12', '12.12.12.1', '12.255.255.255', '12.12.12.20')
        self.assertEqual(cm.exception.message, 'Interface eth1 is already configured')

    def test_add_fallback_interface_invalid_params(self):
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface(None, '12.12.12.12', '12.12.12.1', '12.255.255.255', '12.12.12.20')
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface('', '12.12.12.12', '12.12.12.1', '12.255.255.255', '12.12.12.20')
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface('eth1', None, '12.12.12.1', '12.255.255.255', '12.12.12.20')
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface('eth1', '', '12.12.12.1', '12.255.255.255', '12.12.12.20')
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface('eth1', '12.12.12.12', None, '12.255.255.255', '12.12.12.20')
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface('eth1', '12.12.12.12', '', '12.255.255.255', '12.12.12.20')
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface('eth1', '12.12.12.12', '12.12.12.1', None, '12.12.12.20')
        with self.assertRaises(MissingParameter) as cm:
            self.d.add_fallback_interface('eth1', '12.12.12.12', '12.12.12.1', '', '12.12.12.20')

    def test_delete_fallback_interface(self):
        self.assertTrue(self.d.add_fallback_interface('eth6', '12.12.12.12', '12.12.12.14', '12.12.12.16'))
        self.assertEqual(len(self.d.get_configurations()), 3)
        self.assertTrue(self.d.delete_interface('eth6'))
        self.assertEqual(len(self.d.get_configurations()), 2)

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_dhcpcdconf.py
    #coverage report -m
    unittest.main()

