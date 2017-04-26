#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
import unittest
import os
import re
from shutil import copy2

class DhcpcdConf():
    """
    Helper class to update and read /etc/dhcpcd.conf file
    """

    #CONF = '/etc/dhcpcd.conf'
    CONF = 'dhcpcd.conf'
    BACKUP = '/etc/dhcpcd.conf.backup'

    MODE_WRITE = 'w'
    MODE_READ = 'r'
    MODE_APPEND = 'a'

    def __init__(self):
        self.__fd = None
        #make copy of original file if not exists
        if not os.path.exists(self.BACKUP):
            copy2(self.CONF, self.BACKUP)

    def __del__(self):
        self.__close()

    def __open(self, mode='r'):
        """
        Open config file
        @return file descriptor as returned by open() function
        @raise Exception if file doesn't exist
        """
        if not os.path.exists(self.CONF):
            raise Exception('dhcpcd.conf file does not exist')

        self.__fd = open(self.CONF, mode)
        return self.__fd

    def __close(self):
        """
        Close file descriptor if still opened
        """
        if self.__fd:
            self.__fd.close()
            self.__fd = None

    def __get_interface_config(self, interface):
        """
        Return interface configuration from config file
        @param interface: interface name
        @return interface configuration (dict)
        """
        #get file content
        fd = self.__open()
        lines = fd.readlines()
        content = '\n'.join(lines)
        self.__close()

        #get interface declaration line content
        interface_line = re.findall('^(\s*interface\s*%s\s*)$' % interface, content, re.MULTILINE)
        if len(interface_line)==0:
            raise Exception('No configuration found for interface %s' % interface)
        elif len(interface_line)!=1:
            raise Exception('Duplicate configuration found for interface %s' % interface)
        interface_line = interface_line[0].strip()

        #parse lines
        start = False
        line_number = 0
        ip_address = None
        routers = None
        domain_name_servers = None
        for line in lines:
            line_number += 1
            if line.startswith(interface_line):
                #start of interface config found
                start = True
            elif start and not line.strip().startswith('static'):
                #end of current interface config
                break
            elif start:
                #readline current interface config line
                items = re.findall('^static\s*(.*?)\s*=\s*(.*?)$', line)
                if len(items)!=1:
                    raise Exception('Malformed line in dhcpcd.conf at %d' % line_number)
                items = items[0]
                if len(items)==2:
                    if items[0]=='ip_address':
                        ip_address = items[1].replace('/24', '')
                    elif items[0]=='routers':
                        routers = items[1]
                    elif items[0]=='domain_name_servers':
                        domain_name_servers = items[1]
                    else:
                        #Unknown interface field
                else:
                    raise Exception('Dhcpcd.conf seems to be malformed at line %d (%s)' % (line_number, items))

        return {
            'interface': interface,
            'ip_address': ip_address,
            'routers': routers,
            'domain_name_servers': domain_name_servers
        };

    def restore_default(self):
        """
        Restore original file (at least file backuped at first class startup)
        @return True if file restoration succeed, False otherwise
        """
        if os.path.exists(self.BACKUP):
            copy2(self.BACKUP, self.CONF)
            return True

        return False
    
    def get_interfaces(self):
        """
        Get configured interfaces
        """
        interfaces = []
        fd = self.__open()
        lines = fd.readlines()
        content = '\n'.join(lines)
        self.__close()
        groups = re.findall('^(interface(.*))$', content, re.MULTILINE)
        for group in groups:
            interface = group[1].strip()
            interfaces.append(self.__get_interface_config(interface))

        return interfaces

    def get_interface(self, interface):
        """
        Return specified interface config
        @param interface: interface name
        @return interface config (dict) or None if interface is not configured
        @raise MissingParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter('Interface parameter is missing')

        interfaces = self.get_interfaces()
        for interface_ in interfaces:
            if interface_['interface']==interface:
                return interface_

        return None

    def add_static_interface(self, interface, ip_address, routers, domain_name_servers):
        """
        Add new static interface
        @param ip_address: static ip address
        @param routers: routers address
        @param domain_name_servers: domain name servers
        @return True if interface added successfully
        @raise MissingParameter, InvalidParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter('Interface parameter is missing')
        if ip_address is None or len(ip_address)==0:
            raise MissingParameter('Ip_address parameter is missing')
        if routers is None or len(routers)==0:
            raise MissingParameter('Routers parameter is missing')
        if domain_name_servers is None or len(domain_name_servers)==0:
            raise MissingParameter('Domain_name_servers parameter is missing')

        #check if interface is not already configured
        if self.get_interface(interface) is not None:
            raise InvalidParameter('Interface %s is already configured' % interface)

        #prepare configuration content
        output = '\ninterface %s\n' % interface
        output += 'static ip_address=%s/24\n' % ip_address
        output += 'static routers=%s\n' % routers
        output += 'static domain_name_servers=%s\n' % domain_name_servers

        #write configuration
        fd = self.__open(self.MODE_APPEND)
        fd.write(output)
        self.__close()

        return True

    def delete_static_interface(self, interface):
        """
        Delete new static interface
        @param interface: interface name
        @return True if interface is deleted
        @raise MissingParameter, InvalidParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter('Interface parameter is missing')

        #check if interface is not already configured
        interface = self.get_interface(interface)
        if interface is None:
            raise InvalidParameter('Interface %s is already configured' % interface)

        #read file and search lines to delete
        fd = self.__open()
        lines = fd.readlines()
        self.__close()
        start = False
        indexes = []
        index = 0
        for line in lines:
            if re.match('^\s*interface\s*%s\s*$' % interface['interface'], line):
                indexes.append(index)
                start = True
            elif start and not line.strip().startswith('static'):
                break
            elif start:
                indexes.append(index)
            index += 1

        #delete interface configuration lines
        indexes.reverse()
        for index in indexes:
            lines.pop(index)

        #write config file
        fd = self.__open(self.MODE_WRITE)
        fd.write(''.join(lines))
        self.__close()

        return True


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

        self.d = DhcpcdConf()
        self.d.CONF = 'dhcpcd.fake.conf'

    def tearDown(self):
        os.remove('dhcpcd.fake.conf')
        os.remove(self.d.BACKUP)

    def test_get_interfaces(self):
        interfaces = self.d.get_interfaces()
        self.assertEqual(len(interfaces), 1)
        self.assertEqual(interfaces[0]['interface'], 'eth0')
        self.assertEqual(interfaces[0]['ip_address'], '192.168.1.250')
        self.assertEqual(interfaces[0]['routers'], '192.168.1.1')
        self.assertEqual(interfaces[0]['domain_name_servers'], '192.168.1.1')

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
        self.assertRaises(InvalidParameter, self.d.delete_static_interface, 'eth1')
        
    def test_delete_interface(self):
        self.assertTrue(self.d.add_static_interface('eth1', '10.30.1.255', '10.30.1.1', '10.30.1.2'))
        self.assertEqual(len(self.d.get_interfaces()), 2)
        self.assertTrue(self.d.delete_static_interface('eth1'))
        self.assertEqual(len(self.d.get_interfaces()), 1)
        


