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
    @see https://wiki.archlinux.org/index.php/dhcpcd
    """

    CONF = '/etc/dhcpcd.conf'
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
        interfaces = {}
        fd = self.__open()
        lines = fd.readlines()
        content = '\n'.join(lines)+'\n'
        self.__close()

        regex = r'(.*interface)\s*(\w+)\s|(.*static\s*ip_address)\s*=\s*(.*?)\s|(.*profile)\s*(\w+_\w+)\s|(.*static\s*routers)\s*=\s*(.*?)\s|(.*static\s*domain_name_servers)\s*=\s*(.*?)\s|(fallback)\s*(\w+_\w+)\s'
        groups = re.findall(regex, content)
        interfaces_ = {}
        profiles_ = {}
        current_item = None
        for group in groups:
            group = filter(None, group)
            if group[0] is not None and len(group[0])>0:
                if group[0]=='interface':
                    key = group[1]
                    interfaces_[key] = {
                        'ip_address': None,
                        'router_address': None,
                        'name_server': None,
                        'fallback': None
                    }
                    current_item = interfaces_[key]
                elif group[0]=='profile':
                    key = group[1]
                    profiles_[key] = {
                        'ip_address': None,
                        'router_address': None,
                        'name_server': None
                    }
                    current_item = profiles_[key]
                elif group[0].endswith('ip_address'):
                    current_item['ip_address'] = group[1].replace('/24', '')
                elif group[0].endswith('routers'):
                    current_item['router_address'] = group[1]
                elif group[0].endswith('domain_name_servers'):
                    current_item['name_server'] = group[1]
                elif group[0]=='fallback':
                    current_item['fallback'] = group[1]

        #join profiles and interfaces
        for interface in interfaces_:
            interfaces[interface] = {
                'interface': interface,
                'ip_address': None,
                'router_address': None,
                'name_server': None,
                'fallback': False
            }

            if interfaces_[interface]['fallback'] is not None and len(interfaces_[interface]['fallback'])>0:
                if profiles_.has_key(interfaces_[interface]['fallback']):
                    #get data from profile
                    interfaces[interface]['ip_address'] = profiles_[interfaces_[interface]['fallback']]['ip_address']
                    interfaces[interface]['router_address'] = profiles_[interfaces_[interface]['fallback']]['router_address']
                    interfaces[interface]['name_server'] = profiles_[interfaces_[interface]['fallback']]['name_server']
                    interfaces[interface]['fallback'] = True
                else:
                    #malformed file: interface profile not found
                    break
            else:
                #get data directly from interface
                interfaces[interface]['ip_address'] = interfaces_[interface]['ip_address']
                interfaces[interface]['router_address'] = interfaces_[interface]['router_address']
                interfaces[interface]['name_server'] = interfaces_[interface]['name_server']

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
        if interfaces.has_key(interface):
            return interfaces[interface]

        return None

    def add_static_interface(self, interface, ip_address, router_address, name_server):
        """
        Add new static interface
        @param ip_address: static ip address
        @param router_address: router address
        @param name_server: name server
        @return True if interface added successfully
        @raise MissingParameter, InvalidParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter('Interface parameter is missing')
        if ip_address is None or len(ip_address)==0:
            raise MissingParameter('Ip_address parameter is missing')
        if router_address is None or len(router_address)==0:
            raise MissingParameter('Router_address parameter is missing')
        if name_server is None or len(name_server)==0:
            raise MissingParameter('Name_server parameter is missing')

        #check if interface is not already configured
        if self.get_interface(interface) is not None:
            raise InvalidParameter('Interface %s is already configured' % interface)

        #prepare configuration content
        output = '\ninterface %s\n' % interface
        output += 'static ip_address=%s/24\n' % ip_address
        output += 'static routers=%s\n' % router_address
        output += 'static domain_name_servers=%s\n' % name_server

        #write configuration
        fd = self.__open(self.MODE_APPEND)
        fd.write(output)
        self.__close()

        return True

    def delete_static_interface(self, interface):
        """
        Delete new static interface
        @param interface: interface name
        @return True if interface is deleted, False otherwise
        @raise MissingParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter('Interface parameter is missing')

        #check if interface is configured
        if self.get_interface(interface) is None:
            return False

        #read file and search lines to delete
        fd = self.__open()
        lines = fd.readlines()
        self.__close()
        start = False
        indexes = []
        index = 0
        count = 0
        regex_header = r'^\s*interface\s*%s\s*$' % interface
        regex_line = r'^\s*static.*$'
        for line in lines:
            if re.match(regex_header, line):
                #header found, start
                indexes.append(index)
                start = True
                count += 1
            elif count==4:
                #number of line to delete reached, stop
                break
            elif start and line.strip().startswith('#'):
                #commented line
                continue
            #elif start and not line.strip().startswith('static'):
            elif start and re.match(regex_line, line):
                #save index of line to delete
                indexes.append(index)
                count += 1
            index += 1

        if len(indexes)!=4:
            #number of line to delete not found. Do nothing
            return False

        #delete interface configuration lines
        indexes.reverse()
        for index in indexes:
            lines.pop(index)

        #write config file
        fd = self.__open(self.MODE_WRITE)
        fd.write(''.join(lines))
        self.__close()

        return True

    def add_fallback_interface(self, interface, ip_address, router_address, name_server):
        """
        Configure fallback static interface
        @param ip_address: static ip address
        @param router_address: router address
        @param name_server: name server
        @return True if interface added successfully
        @raise MissingParameter, InvalidParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter('Interface parameter is missing')
        if ip_address is None or len(ip_address)==0:
            raise MissingParameter('Ip_address parameter is missing')
        if router_address is None or len(router_address)==0:
            raise MissingParameter('Router_address parameter is missing')
        if name_server is None or len(name_server)==0:
            raise MissingParameter('Name_server parameter is missing')

        #check if interface is not already configured
        if self.get_interface(interface) is not None:
            raise InvalidParameter('Interface %s is already configured' % interface)

        #prepare configuration content
        output = '\nprofile fallback_%s\n' % interface
        output += 'static ip_address=%s/24\n' % ip_address
        output += 'static routers=%s\n' % router_address
        output += 'static domain_name_servers=%s\n' % name_server
        output += '\ninterface %s\n' % interface
        output += 'fallback fallback_%s\n' % interface

        #write configuration
        fd = self.__open(self.MODE_APPEND)
        fd.write(output)
        self.__close()

        return True

    def delete_fallback_interface(self, interface):
        """
        Delete fallback configuration for specified interface
        @param interface: interface name
        @return True if interface is deleted, False otherwise
        @raise MissingParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter('Interface parameter is missing')

        #check if interface is configured
        if self.get_interface(interface) is None:
            return False

        #delete interface data and find profile name
        fd = self.__open()
        lines = fd.readlines()
        self.__close()
        profile = None
        start = False
        indexes = []
        index = 0
        count = 0
        regex_header = r'^\s*interface\s*%s\s*$' % interface
        regex_line = r'^\s*fallback\s*(.*?)\s*$'
        for line in lines:
            if re.match(regex_header, line):
                #header found, start
                indexes.append(index)
                start = True
                count += 1
            elif count==2:
                #number of line to delete reached, stop
                break
            elif start and line.strip().startswith('#'):
                #commented line
                continue
            elif start:
                matches = re.match(regex_line, line)
                if matches and len(matches.groups())==1:
                    #save profile name
                    profile = matches.groups()[0]
                    #save index of line to delete
                    indexes.append(index)
                    count += 1
            index += 1

        if len(indexes)!=2:
            #number of line to delete not found. Do nothing
            return False

        #delete profile data
        start = False
        index = 0
        count = 0
        regex_header = r'^\s*profile\s*%s\s*$' % profile
        regex_line = r'^\s*static.*$'
        for line in lines:
            if re.match(regex_header, line):
                #header found, start
                indexes.append(index)
                start = True
                count += 1
            elif count==4:
                #number of line to delete reached, stop
                break
            elif start and line.strip().startswith('#'):
                #commented line
                continue
            elif start and re.match(regex_line, line):
                #save index of line to delete
                indexes.append(index)
                count += 1
            index += 1

        if len(indexes)!=6:
            #number of line to delete not found. Do nothing
            return False

        #remove found lines
        indexes.sort()
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
        self.assertTrue(interfaces.has_key('eth0'))
        self.assertEqual(interfaces['eth0']['interface'], 'eth0')
        self.assertEqual(interfaces['eth0']['ip_address'], '192.168.1.250')
        self.assertEqual(interfaces['eth0']['router_address'], '192.168.1.1')
        self.assertEqual(interfaces['eth0']['name_server'], '192.168.1.1')

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
        self.assertEqual(interface['router_address'], '10.30.1.1')
        self.assertEqual(interface['name_server'], '10.30.1.2')

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

        self.d = DhcpcdConf()
        self.d.CONF = 'dhcpcd.fake.conf'

    def tearDown(self):
        os.remove('dhcpcd.fake.conf')
        os.remove(self.d.BACKUP)

    def test_get_interfaces(self):
        interfaces = self.d.get_interfaces()
        self.assertEqual(len(interfaces), 2)
        self.assertTrue(interfaces.has_key('eth0'))
        self.assertEqual(interfaces['eth0']['interface'], 'eth0')
        self.assertEqual(interfaces['eth0']['ip_address'], '192.168.0.10')
        self.assertEqual(interfaces['eth0']['router_address'], '192.168.0.1')
        self.assertEqual(interfaces['eth0']['name_server'], '192.168.0.1')

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
        self.assertEqual(interface['router_address'], '10.30.1.1')
        self.assertEqual(interface['name_server'], '10.30.1.2')

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
        self.assertEqual(interface['router_address'], '12.12.12.1')
        self.assertEqual(interface['name_server'], '12.12.12.20')
        self.assertTrue(interface['fallback'])

    def test_delete_fallback_interface(self):
        self.assertTrue(self.d.add_fallback_interface('eth6', '12.12.12.12', '12.12.12.14', '12.12.12.16'))
        self.assertEqual(len(self.d.get_interfaces()), 3)
        self.assertTrue(self.d.delete_fallback_interface('eth6'))
        self.assertEqual(len(self.d.get_interfaces()), 2)

