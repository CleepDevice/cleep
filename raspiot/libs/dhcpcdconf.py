#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
from raspiot.libs.config import Config
import os
import re
from shutil import copy2

class DhcpcdConf(Config):
    """
    Helper class to update and read /etc/dhcpcd.conf file.

    Note:
        see https://wiki.archlinux.org/index.php/dhcpcd
    """

    CONF = u'/etc/dhcpcd.conf'

    def __init__(self, backup=True):
        """
        Constructor
        """
        Config.__init__(self, self.CONF, u'#', backup)

    def get_interfaces(self):
        """
        Return network interfaces
        """
        entries = {}
        results = self.find(r'^(?:interface\s(.*?))$|^(?:static (.*?)=(.*?))$|^(?:fallback\s(\w+_\w+))$|^(?:profile\s(\w+_\w+))$', re.UNICODE | re.MULTILINE)
        current_entry = None
        for group, groups in results:
            #init variables
            new_entry = None

            #filter none values
            groups = filter(None, groups)

            if group.startswith(u'interface'):
                new_entry = groups[0]
            elif group.startswith(u'profile'):
                new_entry = groups[0]
            elif current_entry is not None:
                if group.startswith(u'static ip_address'):
                    #format: X.X.X.X[/X]
                    splits = groups[1].split('/')
                    current_entry['ip_address'] = splits[0]
                if group.startswith(u'static routers'):
                    #format: X.X.X.X
                    current_entry['routers'] = groups[1]
                if group.startswith(u'static domain_name_servers'):
                    #format: X.X.X.X [X.X.X.X]...
                    current_entry['domain_name_servers'] = groups[1]
                if group.startswith(u'fallback'):
                    #format: <interface id>
                    current_entry['fallback'] = groups[0]

            if new_entry is not None:
                #add new entry
                current_entry = {
                    u'group': group,
                    u'interface': new_entry,
                    u'fallback': None,
                    u'ip_address': None,
                    u'routers': None,
                    u'domain_name_servers': None,
                }
                entries[new_entry] = current_entry


        #fill interfaces with profiles
        to_del = []
        for (name, entry) in entries.iteritems():
            if entry[u'fallback'] is not None:
                if entries.has_key(entry[u'fallback']):
                    profile = entries[entry[u'fallback']]
                    entry[u'routers'] = profile[u'routers']
                    entry[u'ip_address'] = profile[u'ip_address']
                    entry[u'domain_name_servers'] = profile[u'domain_name_servers']
                    to_del.append(entry[u'fallback'])
                else:
                    #invalid file, specified profile does not exist
                    pass

        #remove profiles, keep only interfaces
        for name in to_del:
            del entries[name]
        
        return entries

    def get_interface(self, interface):
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
            raise MissingParameter(u'Interface parameter is missing')

        interfaces = self.get_interfaces()
        if interfaces.has_key(interface):
            return interfaces[interface]

        return None

    def add_static_interface(self, interface, ip_address, routers, domain_name_servers):
        """
        Add new static interface
        
        Args:
            ip_address (string): static ip address
            routers (string): routers
            domain_name_servers (string): domain name servers
        
        Returns
            bool: True if interface added successfully
                
        Raises:
            MissingParameter, InvalidParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter(u'Interface parameter is missing')
        if ip_address is None or len(ip_address)==0:
            raise MissingParameter(u'Ip_address parameter is missing')
        if routers is None or len(routers)==0:
            raise MissingParameter(u'Routers parameter is missing')
        if domain_name_servers is None or len(domain_name_servers)==0:
            raise MissingParameter(u'Domain_name_servers parameter is missing')

        #check if interface is not already configured
        if self.get_interface(interface) is not None:
            raise InvalidParameter(u'Interface %s is already configured' % interface)

        #add new configuration
        lines = []
        lines.append(u'\ninterface %s\n' % interface)
        lines.append(u'static ip_address=%s/24\n' % ip_address)
        lines.append(u'static routers=%s\n' % routers)
        lines.append(u'static domain_name_servers=%s\n' % domain_name_servers)

        return self.add_lines(lines)

    def delete_static_interface(self, interface):
        """
        Delete new static interface

        Args:
            interface (string): interface name
    
        Returns:
            bool: True if interface is deleted, False otherwise

        Raises:
            MissingParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter(u'Interface parameter is missing')

        #check if interface is configured
        if self.get_interface(interface) is None:
            return False

        #delete interface configuration lines
        count = self.remove_after(r'^\s*interface\s*%s\s*$' % interface, r'^\s*static.*$', 4)
        if count!=4:
            return False

        return True

    def add_fallback_interface(self, interface, ip_address, routers, domain_name_servers):
        """
        Configure fallback static interface

        Args:
            ip_address (string): static ip address
            routers (string): router address
            domain_name_servers (string): name server
        
        Returns:
            bool: True if interface added successfully

        Raises:
            MissingParameter, InvalidParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter(u'Interface parameter is missing')
        if ip_address is None or len(ip_address)==0:
            raise MissingParameter(u'Ip_address parameter is missing')
        if routers is None or len(routers)==0:
            raise MissingParameter(u'Routers parameter is missing')
        if domain_name_servers is None or len(domain_name_servers)==0:
            raise MissingParameter(u'Domain_name_servers parameter is missing')

        #check if interface is not already configured
        if self.get_interface(interface) is not None:
            raise InvalidParameter(u'Interface %s is already configured' % interface)

        #prepare configuration content
        lines = []
        lines.append(u'\nprofile fallback_%s\n' % interface)
        lines.append(u'static ip_address=%s/24\n' % ip_address)
        lines.append(u'static routers=%s\n' % routers)
        lines.append(u'static domain_name_servers=%s\n' % domain_name_servers)
        lines.append(u'\ninterface %s\n' % interface)
        lines.append(u'fallback fallback_%s\n' % interface)

        return self.add_lines(lines)

    def delete_fallback_interface(self, interface):
        """
        Delete fallback configuration for specified interface

        Args:
            interface (string): interface name

        Returns:
            bool: True if interface is deleted, False otherwise

        Raises:
            MissingParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter(u'Interface parameter is missing')

        #check if interface is configured
        interface_ = self.get_interface(interface)
        if interface_ is None:
            return False

        #delete interface data and find profile name
        count = self.remove_after(r'^\s*interface\s*%s\s*$' % interface, r'^\s*fallback\s*(.*?)\s*$', 2)
        if count!=2:
            return False

        #delete profile data
        if interface_[u'fallback'] is not None:
            count = self.remove_after(r'^\s*profile\s*%s\s*$' % interface_[u'fallback'], r'^\s*static.*$', 6)
            if count!=4:
                return False

        return True



