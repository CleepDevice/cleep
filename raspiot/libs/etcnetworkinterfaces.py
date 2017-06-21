#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
from raspiot.libs.config import Config
import os
import re
import time
from shutil import copy2

class EtcNetworkInterfaces(Config):
    """
    Helper class to update and read /etc/network/interfaces file.

    Note:
        http://elinux.org/Configuring_a_Static_IP_address_on_your_Raspberry_Pi
        https://help.ubuntu.com/lts/serverguide/network-configuration.html#ip-addressing
        https://unix.stackexchange.com/a/128662
    """

    CONF = u'/etc/network/interfaces'

    CACHE_DURATION = 60.0

    OPTION_NONE = 0
    OPTION_AUTO = 1
    OPTION_HOTPLUG = 2

    MODE_STATIC = u'static'
    MODE_MANUAL = u'manual'
    MODE_LOOPBACK = u'loopback'
    MODE_DHCP = u'dhcp'

    def __init__(self, backup=True):
        """
        Constructor
        """
        Config.__init__(self, self.CONF, None, backup)

        #members
        self.__last_update = None
        self.__cache = None

    def __append_option(self, option, lines, interface):
        """
        Append option line to specified list

        Args:
            option (string): interface option (none=0|auto=1|hotplug=2)
            lines (list): list of lines
            interface (string): interface name
        """
        if option>0:
            lines.append(u'\n')
        if bool(option & self.OPTION_AUTO):
            lines.append(u'auto %s\n' % interface)
        if bool(option & self.OPTION_HOTPLUG):
            lines.append(u'allow-hotplug %s\n' % interface)

    def get_interfaces(self):
        """
        Return network interfaces
        """
        #check cache
        if self.__last_update is not None and (time.time()-self.__last_update)<self.CACHE_DURATION:
            return self.__cache

        entries = {}
        results = self.find(u'^\s*(?:iface\s*(\S+)\s*inet\s*(\S+))\s*$|^\s*(?:(\S+)\s(\S+))\s*$', re.UNICODE | re.MULTILINE)
        current_entry = None
        for group, groups in results:
            #init variables
            new_entry = None
            hotplug = False
            auto = False
            mode = None

            #filter none values
            groups = filter(None, groups)

            if group.startswith(u'allow-hotplug'):
                if not entries.has_key(groups[1]):
                    hotplug = True
                    new_entry = groups[1]
                else:
                    current_entry[u'hotplug'] = True

            elif group.startswith(u'allow-auto') or group.startswith(u'auto'):
                if not entries.has_key(groups[1]):
                    auto = True
                    new_entry = groups[1]
                else:
                    current_entry[u'auto'] = True

            elif group.startswith(u'iface'):
                if not entries.has_key(groups[0]):
                    new_entry = groups[0]
                    mode = groups[1]
                else:
                    current_entry[u'mode'] = groups[1]

            elif current_entry is not None:
                if group.startswith(u'address'):
                    #format: X.X.X.X
                    current_entry[u'address'] = groups[1]
                if group.startswith(u'netmask'):
                    #format: X.X.X.X
                    current_entry[u'netmask'] = groups[1]
                if group.startswith(u'broadcast'):
                    #format: X.X.X.X
                    current_entry[u'broadcast'] = group[1]
                if group.startswith(u'gateway'):
                    #format: X.X.X.X
                    current_entry[u'gateway'] = groups[1]
                if group.startswith(u'dns-nameservers'):
                    #format: server1 <server2>...
                    current_entry[u'dns-nameservers'] = groups[1]
                if group.startswith(u'dns-domain'):
                    #format: server1 <server2>...
                    current_entry[u'dns-domain'] = groups[1]
                if group.startswith(u'wpa-conf'):
                    #format: <wpa_supplicant.conf path>
                    current_entry[u'wpa_conf'] = groups[1]

            if new_entry is not None:
                #add new entry
                current_entry = {
                    u'interface': new_entry,
                    u'mode': mode,
                    u'address': None,
                    u'netmask': None,
                    u'broadcast': None,
                    u'gateway': None,
                    u'dns_nameservers': None,
                    u'dns_domain': None,
                    u'hotplug': hotplug,
                    u'auto': auto,
                    u'wpa_conf': None
                }
                entries[new_entry] = current_entry

        #handle cache
        self.__cache = entries
        self.__last_update = time.time()

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
        if not isinstance(interface, unicode):
            raise InvalidParameter(u'Interface parameter must be unicode not %s' % type(interface))

        interfaces = self.get_interfaces()
        if interfaces.has_key(interface):
            return interfaces[interface]

        return None

    def __add_interface(self, interface, mode, option, address, netmask, gateway, dns_nameservers=None, dns_domain=None, broadcast=None, wpa_conf=None):
        """
        Add new static or manual interface
        
        Args:
            interface (string): interface name
            mode (string): type of configuration (static|manual)
            option (string): interface option (none=0|auto=1|hotplug=2)
            address (string): ip address
            netmask (string): netmask
            gateway (string): router ip address
            dns_nameservers (string): domain name servers
            dns_domain (string): dns domain
            broadcast (string): broadcast ip address
            wpa_conf (string): wpa configuration (usually path to wpa_supplicant.conf file)
        
        Returns
            bool: True if interface added successfully
                
        Raises:
            MissingParameter, InvalidParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter(u'Interface parameter is missing')
        if option is None:
            raise MissingParameter(u'Option parameter is missing')
        if address is None or len(address)==0:
            raise MissingParameter(u'Address parameter is missing')
        if gateway is None or len(gateway)==0:
            raise MissingParameter(u'Gateway parameter is missing')
        if netmask is None or len(netmask)==0:
            raise MissingParameter(u'Netmask parameter is missing')
        if mode is None or len(mode)==0:
            raise MissingParameter(u'Mode parameter is missing')
        if mode not in (self.MODE_STATIC, self.MODE_MANUAL):
            raise InvalidParameter(u'Mode value is invalid (possible values are %s)' % u','.join([self.MODE_STATIC, self.MODE_MANUAL]))

        #check if interface is not already configured
        if self.get_interface(interface) is not None:
            raise InvalidParameter(u'Interface %s is already configured' % interface)

        #add new configuration
        lines = []
        self.__append_option(option, lines, interface)
        lines.append(u'iface %s inet %s\n' % (interface, mode))
        lines.append(u'  address %s\n' % address)
        lines.append(u'  netmask %s\n' % netmask)
        lines.append(u'  gateway %s\n' % gateway)
        if dns_domain is not None and len(dns_domain)>0:
            lines.append(u'  dns-domain %s\n' % dns_domain)
        if dns_nameservers is not None and len(dns_nameservers)>0:
            lines.append(u'  dns-nameservers %s\n' % dns_nameservers)
        if broadcast is not None and len(broadcast)>0:
            lines.append(u'  broadcast %s\n' % broadcast)
        if wpa_conf is not None and len(wpa_conf)>0:
            lines.append(u'  wpa-conf %s\n' % wpa_conf)

        #handle cache
        self.__last_update = 0

        return self.add_lines(lines)

    def __delete_interface(self, interface, mode):
        """
        Delete static or manual interface

        Args:
            interface (string): interface name
            mode (string): type of configuration (static|manual)
    
        Returns:
            bool: True if interface is deleted, False otherwise

        Raises:
            MissingParameter
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter(u'Interface parameter is missing')
        if mode is None or len(mode)==0:
            raise MissingParameter(u'Mode parameter is missing')
        if mode not in (self.MODE_STATIC, self.MODE_MANUAL):
            raise InvalidParameter(u'Mode value is invalid (possible values are %s)' % u''.join([self.MODE_STATIC, self.MODE_MANUAL]))

        #check if interface is configured
        interface_ = self.get_interface(interface)
        if interface_ is None:
            return False

        #build patterns
        pattern = u''
        count = 0
        if interface_[u'auto']:
            header = r'^\s*auto\s*%s\s*' % interface
            pattern = r'^\s*iface\s*%s\s*inet\s*%s\s*$|' % (interface, mode)
            count = 2
        elif interface_[u'hotplug']:
            header = r'^\s*allow-hotplug\s*%s\s*' % interface
            pattern = r'^\s*iface\s*%s\s*inet\s*%s\s*$|' % (interface, mode)
            count = 2
        else:
            header = r'^\s*iface\s*%s\s*inet\s*%s\s*$' % (interface, mode)
            count = 1

        if interface_[u'address'] is not None and len(interface_[u'address'])>0:
            pattern += u'^\s*address\s%s\s*$|' % interface_[u'address']
            count += 1
        if interface_[u'netmask'] is not None and len(interface_[u'netmask'])>0:
            pattern += u'^\s*netmask\s%s\s*$|' % interface_[u'netmask']
            count += 1
        if interface_[u'gateway'] is not None and len(interface_[u'gateway'])>0:
            pattern += u'^\s*gateway\s%s\s*$|' % interface_[u'gateway']
            count += 1
        if interface_[u'dns_domain'] is not None and len(interface_[u'dns_domain'])>0:
            pattern += u'^\s*dns-domain\s%s\s*$|' % interface_[u'dns_domain']
            count += 1
        if interface_[u'dns_nameservers'] is not None and len(interface_[u'dns_nameservers'])>0:
            pattern += u'^\s*?:dns-nameservers\s%s\s*$|' % interface_[u'dns_nameservers']
            count += 1
        if interface_[u'broadcast'] is not None and len(interface_[u'broadcast'])>0:
            pattern += u'^\s*broadcast\s%s\s*$|' % interface_[u'broadcast']
            count += 1
        if interface_[u'wpa_conf'] is not None and len(interface_[u'wpa_conf'])>0:
            pattern += u'^\s*wpa_conf\s%s\s*$|' % interface_[u'wpa_conf']
            count += 1

        res = self.remove_after(header, r'%s' % pattern[:len(pattern)-1], count)
        if res!=count:
            return False

        #handle cache
        self.__last_update = 0

        return True

    def __delete_dhcp_interface(self, interface):
        """
        Delete dhcp interface

        Args:
            interface (string) interface name

        Returns:
            bool: True if interface deleted
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter(u'Interface parameter is missing')

        #check if interface is configured
        interface_ = self.get_interface(interface)
        if interface_ is None:
            return False

        #build patterns
        if interface_[u'auto']:
            header = r'^\s*auto\s*%s\s*' % interface
            line = r'^\s*iface\s*%s\s*inet dhcp\s*$' % interface
            count = 2
        elif interface_[u'hotplug']:
            header = r'^\s*allow-hotplug\s*%s\s*' % interface
            line = r'^\s*iface\s*%s\s*inet dhcp\s*$' % interface
            count = 2
        else:
            header = r'^\s*iface\s*%s\s*inet dhcp\s*$' % interface
            line = r'dummy'
            count = 1
        res = self.remove_after(header, line, count)

        if res!=count:
            return False

        #handle cache
        self.__last_update = 0

        return True

    def add_static_interface(self, interface, address, netmask, gateway, option=1, dns_nameservers=None, dns_domain=None, broadcast=None, wpa_conf=None):
        """
        Add new static interface
        
        Args:
            interface (string): interface name
            address (string): static ip address
            gateway (string): gateway ip address
            netmask (string): netmask (default 255.255.255.0)
            option (string): interface option (none|auto|hotplug) (default auto)
            dns_nameservers (string): domain name servers
            dns_domain (string): dns domain
            broadcast (string): broadcast ip address
            wpa_conf (string): wpa configuration (usually path to wpa_supplicant.conf file)
        
        Returns
            bool: True if interface added successfully
                
        Raises:
            MissingParameter, InvalidParameter
        """
        return self.__add_interface(interface, self.MODE_STATIC, option, address, netmask, gateway, dns_nameservers, dns_domain, broadcast, wpa_conf)

    def add_manual_interface(self, interface, address, netmask, gateway, option=1, dns_nameservers=None, dns_domain=None, broadcast=None, wpa_conf=None):
        """
        Add new manual interface
        
        Args:
            interface (string): interface name
            option (string): interface option (none|auto|hotplug)
            address (string): static ip address
            netmask (string): netmask
            gateway (string): gateway ip address
            dns_nameservers (string): domain name servers
            dns_domain (string): dns domain
            broadcast (string): broadcast ip address
            wpa_conf (string): wpa configuration (usually path to wpa_supplicant.conf file)
        
        Returns
            bool: True if interface added successfully
                
        Raises:
            MissingParameter, InvalidParameter
        """
        return self.__add_interface(interface, self.MODE_MANUAL, option, address, netmask, gateway, dns_nameservers, dns_domain, broadcast, wpa_conf)


    def add_dhcp_interface(self, interface, option):
        """
        Add dhcp interface

        Args:
            interface (string): interface name
            option (string): interface option (none=0|hotplug=1|auto=2)

        Returns:
            bool: True if interface added
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter(u'Interface parameter is missing')
        if option is None:
            raise MissingParameter(u'Option parameter is missing')

        #check if interface is not already configured
        if self.get_interface(interface) is not None:
            return False

        #add new configuration
        lines = []
        self.__append_option(option, lines, interface)
        lines.append(u'iface %s inet dhcp\n' % interface)

        return self.add_lines(lines)

    def add_manual_interface(self, interface, option, wpa_conf):
        """
        Add manual interface

        Args:
            interface (string): interface name
            option (string): interface option (none=0|hotplug=1|auto=2)
            wpa_conf (string): wpa config

        Returns:
            bool: True if interface added
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter(u'Interface parameter is missing')
        if option is None:
            raise MissingParameter(u'Option parameter is missing')
        if wpa_conf is None or len(wpa_conf)==0:
            raise MissingParameter(u'Wpa_conf parameter is missing')

        #check if interface is not already configured
        if self.get_interface(interface) is not None:
            return False

        #add new configuration
        lines = []
        self.__append_option(option, lines, interface)
        lines.append(u'iface %s inet manual\n' % interface)
        lines.append(u'  wpa-conf')

        return self.add_lines(lines)

    def delete_interface(self, interface):
        """
        Delete specified interface

        Args:
            interface (string): interface name
        
        Returns:
            bool: Ture if interface deleted
        """
        #get interface
        interface_ = self.get_interface(interface)
        if interface_ is None:
            #interface not found
            return False

        #find interface mode
        if interface_[u'mode']==self.MODE_DHCP:
            return self.__delete_dhcp_interface(interface)
        elif interface_[u'mode'] in (self.MODE_STATIC, self.MODE_MANUAL):
            return self.__delete_interface(interface, interface_[u'mode'])
        else:
            #undeleteable interface (loopback) or unknown interface
            return False


