#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.exception import InvalidParameter, MissingParameter, CommandError
from cleep.libs.configs.config import Config
from cleep.libs.internals.console import Console
from cleep.libs.internals.tools import netmask_to_cidr, cidr_to_netmask
import os
import re
import copy
from shutil import copy2

class DhcpcdConf(Config):
    """
    Helper class to update and read /etc/dhcpcd.conf file.

    Note:
        see https://wiki.archlinux.org/index.php/dhcpcd
    """

    CONF = u'/etc/dhcpcd.conf'

    def __init__(self, cleep_filesystem, backup=True):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            backup (bool): True if backup enabled
        """
        Config.__init__(self, cleep_filesystem, self.CONF, u'#', backup)

    def is_installed(self):
        """
        Check if config file exists and dhcpcd daemon is running

        Returns:
            bool: True if all is fine
        """
        if os.path.exists(self.CONF):
            c = Console()
            res = c.command(u'/usr/bin/pgrep dhcpcd | /usr/bin/wc -l')
            if not res[u'error'] and not res[u'killed'] and res[u'stdout'][0]=='1':
                return True

        return False

    def get_configurations(self):
        """
        Return network interfaces

        Returns:
            dict: interface configurations::

                {
                    interface (string): {
                        group (string): regexp group
                        interface (string): interface name
                        netmask (string): netmask
                        fallback (string): fallback configuration name if any, None otherwise
                        ip_address (string): configured ip address
                        gateway (string): gateway ip address
                        dns_address (string): dns ip address
                    },
                    ...
                }

        """
        entries = {}
        results = self.find(r'^(?:interface\s(.*?))$|^(?:static (.*?)=(.*?))$|^(?:fallback\s(\w+_\w+))$|^(?:profile\s(\w+_\w+))$', re.UNICODE | re.MULTILINE)
        current_entry = None
        for group, groups in results:
            #init variables
            new_entry = None

            #filter none values
            groups = list(filter(None, groups))

            if group.startswith(u'interface'):
                new_entry = groups[0]
            elif group.startswith(u'profile'):
                new_entry = groups[0]
            elif current_entry is not None:
                if group.startswith(u'static ip_address'):
                    #format: X.X.X.X[/X]
                    splits = groups[1].split('/')
                    current_entry[u'ip_address'] = splits[0]
                    try:
                        netmask = cidr_to_netmask(int(splits[1]))
                        current_entry[u'netmask'] = netmask
                    except: # pragma: no cover
                        current_entry[u'netmask'] = '255.255.255.0'
                if group.startswith(u'static routers'):
                    #format: X.X.X.X
                    current_entry[u'gateway'] = groups[1]
                if group.startswith(u'static domain_name_servers'):
                    #format: X.X.X.X [X.X.X.X]...
                    current_entry[u'dns_address'] = groups[1]
                if group.startswith(u'fallback'):
                    #format: <interface id>
                    current_entry[u'fallback'] = groups[0]

            if new_entry is not None:
                # add new entry
                current_entry = {
                    u'group': group,
                    u'interface': new_entry,
                    u'netmask': None,
                    u'fallback': None,
                    u'ip_address': None,
                    u'gateway': None,
                    u'dns_address': None,
                }
                entries[new_entry] = current_entry

        return entries

    def get_configuration(self, interface):
        """
        Return specified interface config
        
        Args:
            interface (string): interface name

        Returns:
            dict: interface config (dict)
            None: if interface is not configured

        Raises:
            MissingParameter: if parameter is missing
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter(u'Parameter "interface" is missing')

        interfaces = self.get_configurations()
        if interface in interfaces:
            return interfaces[interface]

        return None

    def add_static_interface(self, interface, ip_address, gateway, netmask, dns_address=None):
        """
        Add new static interface
        
        Args:
            interface (string): interface to configure
            ip_address (string): static ip address
            gateway (string): gateway address
            netmask (string): netmask
            dns_address (string): dns address
        
        Returns
            bool: True if interface added successfully
                
        Raises:
            MissingParameter, InvalidParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter(u'Parameter "interface" is missing')
        if ip_address is None or len(ip_address)==0:
            raise MissingParameter(u'Parameter "ip_address" is missing')
        if gateway is None or len(gateway)==0:
            raise MissingParameter(u'Parameter "gatewa"y is missing')
        if netmask is None or len(netmask)==0:
            raise MissingParameter(u'Parameter "netmask" is missing')

        #check if interface is not already configured
        if self.get_configuration(interface) is not None:
            raise InvalidParameter(u'Interface %s is already configured' % interface)

        #get CIDR value
        cidr = netmask_to_cidr(netmask)

        #fix dns
        if dns_address is None:
            dns_address = gateway

        #add new configuration
        lines = []
        lines.append(u'\ninterface %s\n' % interface)
        lines.append(u'static ip_address=%s/%s\n' % (ip_address, cidr))
        lines.append(u'static routers=%s\n' % gateway)
        lines.append(u'static domain_name_servers=%s\n' % dns_address)

        return self.add_lines(lines)

    def __delete_static_interface(self, interface):
        """
        Delete new static interface

        Args:
            interface (dict): interface data as returned by get_interface
    
        Returns:
            bool: True if interface is deleted, False otherwise

        Raises:
            MissingParameter
        """
        #delete interface configuration lines
        count = self.remove_after(r'^\s*interface\s*%s\s*$' % interface[u'interface'], r'^\s*static.*$', 4)
        if count!=4: # pragma: no cover
            return False

        return True

    def add_fallback_interface(self, interface, ip_address, gateway, netmask, dns_address=None):
        """
        Configure fallback static interface

        Args:
            interface (string): interface name
            ip_address (string): static ip address
            gateway (string): gateway ip address
            netmask (string): netmask
            dns_address (string): dns address
        
        Returns:
            bool: True if interface added successfully

        Raises:
            MissingParameter, InvalidParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter(u'Parameter "interface" is missing')
        if ip_address is None or len(ip_address)==0:
            raise MissingParameter(u'Parameter "ip_address" is missing')
        if gateway is None or len(gateway)==0:
            raise MissingParameter(u'Parameter "gateway" is missing')
        if netmask is None or len(netmask)==0:
            raise MissingParameter(u'Parameter "netmask" is missing')

        #check if interface is not already configured
        if self.get_configuration(interface) is not None:
            raise InvalidParameter(u'Interface %s is already configured' % interface)

        #fix dns
        if dns_address is None or len(dns_address)==0:
            dns_address = gateway

        #prepare configuration content
        lines = []
        lines.append(u'\nprofile fallback_%s\n' % interface)
        lines.append(u'static ip_address=%s/%s\n' % (ip_address, netmask_to_cidr(netmask)))
        lines.append(u'static routers=%s\n' % gateway)
        lines.append(u'static domain_name_servers=%s\n' % dns_address)
        lines.append(u'\ninterface %s\n' % interface)
        lines.append(u'fallback fallback_%s\n' % interface)

        return self.add_lines(lines)

    def __delete_fallback_interface(self, interface):
        """
        Delete fallback configuration for specified interface

        Args:
            interface (dict): interface data as returned by get_configuration

        Returns:
            bool: True if interface is deleted, False otherwise

        Raises:
            MissingParameter
        """
        #delete interface data and find profile name
        count = self.remove_after(r'^\s*interface\s*%s\s*$' % interface[u'interface'], r'^\s*fallback\s*(.*?)\s*$', 2)
        if count!=2: # pragma: no cover
            return False

        #delete profile data
        if interface[u'fallback'] is not None:
            count = self.remove_after(r'^\s*profile\s*%s\s*$' % interface[u'fallback'], r'^\s*static.*$', 6)
            if count!=4: # pragma: no cover
                return False

        return True

    def delete_interface(self, interface_name):
        """
        Delete specified interface

        Args:
            interface_name (string): interface name

        Returns:
            bool: True if interface deleted, False otherwise
        """
        #check params
        if interface_name is None or len(interface_name)==0:
            raise MissingParameter(u'Parameter "interface_name" is missing')

        #get interface
        interface = self.get_configuration(interface_name)
        if interface is None:
            #interface not found
            return False

        if interface[u'fallback'] is not None:
            return self.__delete_fallback_interface(interface)
        else:
            return self.__delete_static_interface(interface)



