#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.exception import InvalidParameter, MissingParameter, CommandError
from raspiot.libs.configs.config import Config
import os
import re
import time
from shutil import copy2
import logging

class EtcNetworkInterfaces(Config):
    """
    Helper class to update and read /etc/network/interfaces file.

    Notes:
        http://elinux.org/Configuring_a_Static_IP_address_on_your_Raspberry_Pi
        https://help.ubuntu.com/lts/serverguide/network-configuration.html#ip-addressing
        https://unix.stackexchange.com/a/128662
        infos about inet default: https://wiki.debian.org/fr/WPA
    """

    CONF = u'/etc/network/interfaces'

    CACHE_DURATION = 5.0

    #using bitmask: OPTION_AUTO + OPTION_HOTPLUG
    OPTION_NONE = 0
    OPTION_AUTO = 1
    OPTION_HOTPLUG = 2

    MODE_STATIC = u'static'
    MODE_MANUAL = u'manual'
    MODE_LOOPBACK = u'loopback'
    MODE_DHCP = u'dhcp'

    def __init__(self, cleep_filesystem, backup=True):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            backup (bool): True to enable backup
        """
        Config.__init__(self, cleep_filesystem, self.CONF, None, backup)

        #members
        self.__last_update = None
        self.__cache = None
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

    def __append_option(self, option, lines, interface):
        """
        Append option line to specified list

        Args:
            option (string): interface option (none=0|auto=1|hotplug=2)
            lines (list): list of lines
            interface (string): interface name
        """
        if option==0:
            lines.append(u'\n')
        if option & self.OPTION_AUTO == self.OPTION_AUTO:
            lines.append(u'auto %s\n' % interface)
        if option & self.OPTION_HOTPLUG == self.OPTION_HOTPLUG:
            lines.append(u'allow-hotplug %s\n' % interface)

    def get_configurations(self):
        """
        Return interfaces configurations

        Returns:
            dict: dict of configurated interfaces::

                {
                    interface name (string): {
                        interface (string): interface name,
                        mode (string): iface mode,
                        address (string): ip address,
                        netmask (string): netmask address,
                        broadcast (string): broadcast address,
                        gateway (string): gateway address,
                        dns_nameservers (string): dns nameservers address,
                        dns_domain (string): dns domain address,
                        hotplug (bool): True if hotplug interface,
                        auto (bool): True if auto option enabled,
                        wpa_conf (string): wpa profile name
                    },
                    ...
                }

        """
        #check cache
        if self.__last_update is not None and (time.time()-self.__last_update)<self.CACHE_DURATION:
            return self.__cache

        entries = {}
        results = self.find(r'^\s*(?:iface\s*(\S+)\s*inet\s*(\S+))\s*$|^\s*(?:(\S+)\s(\S+))\s*$', re.UNICODE | re.MULTILINE)
        current_entry = None
        for group, groups in results:
            #init variables
            new_entry = None
            hotplug = False
            auto = False
            mode = None

            #filter none values
            groups = list(filter(None, groups))

            if group.startswith(u'allow-hotplug'):
                if groups[1] not in entries:
                    hotplug = True
                    new_entry = groups[1]
                else:
                    current_entry[u'hotplug'] = True

            elif group.startswith(u'allow-auto') or group.startswith(u'auto'):
                if groups[1] not in entries:
                    auto = True
                    new_entry = groups[1]
                else: # pragma: no cover
                    current_entry[u'auto'] = True

            elif group.startswith(u'iface'):
                if groups[0] not in entries:
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
                    current_entry[u'broadcast'] = groups[1]
                if group.startswith(u'gateway'):
                    #format: X.X.X.X
                    current_entry[u'gateway'] = groups[1]
                if group.startswith(u'dns-nameservers'):
                    #format: server1 <server2>...
                    current_entry[u'dns_nameservers'] = groups[1]
                if group.startswith(u'dns-domain'):
                    #format: server1 <server2>...
                    current_entry[u'dns_domain'] = groups[1]
                if group.startswith(u'wpa-conf') or group.startswith(u'wpa-roam'):
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
        self.logger.trace(entries)
        self.__cache = entries
        self.__last_update = time.time()

        return entries

    def get_configuration(self, interface):
        """
        Return specified interface configuration
        
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


    def __delete_interface(self, interface, mode):
        """
        Delete static or manual interface

        Args:
            interface (dict): interface data as returned by get_configuration
            mode (string): type of configuration (static|manual)
    
        Returns:
            bool: True if interface is deleted, False otherwise

        Raises:
            MissingParameter
        """
        #check params
        if mode is None or len(mode)==0: # pragma: no cover
            raise MissingParameter(u'Parameter "mode" is missing')
        if mode not in (self.MODE_STATIC, self.MODE_MANUAL): # pragma: no cover
            raise InvalidParameter(u'Mode value is invalid (possible values are %s)' % u''.join([self.MODE_STATIC, self.MODE_MANUAL]))

        #remove options
        if interface[u'auto']:
            count = self.remove_pattern(r'^\s*auto\s*%s\s*' % interface[u'interface'])
            self.logger.debug(u'Removed %d line with auto option' % count)
            if count==0: # pragma: no cover
                self.logger.error('Unable to delete option auto for interface %s' % interface[u'interface'])
                return False
        if interface[u'hotplug']:
            count = self.remove_pattern(r'^\s*allow-hotplug\s*%s\s*' % interface[u'interface'])
            self.logger.debug(u'Removed %d line with hotplug option' % count)
            if count==0: # pragma: no cover
                self.logger.error(u'Unable to delete option hotplug for interface %s' % interface[u'interface'])
                return False
        
        #remove static conf
        pattern = u''
        count = 0
        header = r'^\s*iface\s*%s\s*inet\s*%s\s*$' % (interface[u'interface'], mode)
        count += 1
        if interface[u'address'] is not None and len(interface[u'address'])>0:
            pattern += r'^\s*address\s%s\s*$|' % interface[u'address']
            count += 1
        if interface[u'netmask'] is not None and len(interface[u'netmask'])>0:
            pattern += r'^\s*netmask\s%s\s*$|' % interface[u'netmask']
            count += 1
        if interface[u'gateway'] is not None and len(interface[u'gateway'])>0:
            pattern += r'^\s*gateway\s%s\s*$|' % interface[u'gateway']
            count += 1
        if interface[u'dns_domain'] is not None and len(interface[u'dns_domain'])>0: # pragma: no cover
            pattern += r'^\s*dns-domain\s%s\s*$|' % interface[u'dns_domain']
            count += 1
        if interface[u'dns_nameservers'] is not None and len(interface[u'dns_nameservers'])>0:
            pattern += r'^\s*dns-nameservers\s%s\s*$|' % interface[u'dns_nameservers']
            count += 1
        if interface[u'broadcast'] is not None and len(interface[u'broadcast'])>0:
            pattern += r'^\s*broadcast\s%s\s*$|' % interface[u'broadcast']
            count += 1
        if interface[u'wpa_conf'] is not None and len(interface[u'wpa_conf'])>0:
            pattern += r'^\s*wpa-conf\s%s\s*$|' % interface[u'wpa_conf']
            pattern += r'^\s*wpa-roam\s%s\s*$|' % interface[u'wpa_conf']
            count += 1

        self.logger.debug('Pattern: %s' % pattern)
        res = self.remove_after(header, r'%s' % pattern[:len(pattern)-1], count)
        self.logger.debug('Remove_after=%s count=%s' % (res, count))
        if res!=count: # pragma: no cover
            self.logger.debug(u'It seems all interface "%s" configuration lines were not removed. File "%s" may be corrupted!' % (interface[u'interface'], self.CONF))
            return False

        #handle cache
        self.__last_update = 0

        return True

    def __delete_dhcp_interface(self, interface):
        """
        Delete dhcp interface

        Args:
            interface (dict): interface data as returned by get_configuration

        Returns:
            bool: True if interface deleted
        """
        #remove options
        if interface[u'auto']:
            count = self.remove_pattern(r'^\s*auto\s*%s\s*' % interface[u'interface'])
            if count==1:
                self.logger.debug('Removed %d line with auto option' % count)
                
        if interface[u'hotplug']:
            count = self.remove_pattern(r'^\s*allow-hotplug\s*%s\s*' % interface[u'interface'])
            self.logger.debug('Removed %d line with hotplug option' % count)
            if count==0: # pragma: no cover
                self.logger.error('Unable to delete option hotplug for interface %s' % interface[u'interface'])
                return False

        #remove dhcp conf
        pattern = r'^\s*iface\s*%s\s*inet dhcp\s*$' % interface[u'interface']
        self.logger.trace('Pattern: %s' % pattern)
        count = self.remove_pattern(pattern)
        self.logger.debug('Removed %d line' % count)
        if count==0: # pragma: no cover
            self.logger.error('Unable to delete dhcp for interface %s' % interface[u'interface'])
            return False

        #handle cache
        self.__last_update = 0

        return True

    def delete_interface(self, interface_name):
        """
        Delete specified interface

        Args:
            interface_name (string): interface name
        
        Returns:
            bool: True if interface deleted
        """
        #get interface
        interface = self.get_configuration(interface_name)
        if interface is None:
            #interface not found
            return False

        #find interface mode
        if interface[u'mode']==self.MODE_DHCP:
            return self.__delete_dhcp_interface(interface)
        elif interface[u'mode'] in (self.MODE_STATIC, self.MODE_MANUAL):
            return self.__delete_interface(interface, interface[u'mode'])
        else:
            #undeleteable interface (loopback) or unknown interface
            self.logger.warning(u'Unable to delete specified interface "%s", interface is loopback or has invalid mode (%s).' % (interface_name, interface[u'mode']))
            return False

    def add_default_interface(self):
        """
        Add default interface

        Returns
            bool: True if interface added successfully
        """
        #check if interface is not already configured (in that case delete it first)
        if self.get_configuration(u'default') is not None:
            raise InvalidParameter(u'Interface "default" is already configured')

        lines = []
        lines.append(u'\n')
        lines.append(u'iface default inet dhcp\n')

        #handle cache
        self.__last_update = 0

        return self.add_lines(lines)

    def add_static_interface(self, interface, option, address, gateway, netmask, dns_nameservers=None, dns_domain=None, broadcast=None, wpa_conf=None):
        """
        Add new static or manual interface
        
        Args:
            interface (string): interface name
            option (int): interface option mask (none=0|hotplug=1|auto=2)
            address (string): ip address
            gateway (string): router ip address
            netmask (string): netmask
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
            raise MissingParameter(u'Parameter "interface" is missing')
        if address is None or len(address)==0:
            raise MissingParameter(u'Parameter "address" is missing')
        if gateway is None or len(gateway)==0:
            raise MissingParameter(u'Parameter "gateway" is missing')
        if netmask is None or len(netmask)==0:
            raise MissingParameter(u'Parameter "netmask" is missing')
        if option is None:
            raise MissingParameter(u'Parameter "option" is missing')
        if option not in range(0, self.OPTION_NONE + self.OPTION_AUTO + self.OPTION_HOTPLUG + 1):
            raise InvalidParameter(u'Parameter "option" is invalid')

        #check if interface is not already configured
        if self.get_configuration(interface) is not None:
            raise InvalidParameter(u'Interface "%s" is already configured' % interface)

        #add new configuration
        lines = []
        lines.append(u'\n')
        self.__append_option(option, lines, interface)
        lines.append(u'iface %s inet %s\n' % (interface, self.MODE_STATIC))
        lines.append(u'  address %s\n' % address)
        lines.append(u'  netmask %s\n' % netmask)
        lines.append(u'  gateway %s\n' % gateway)
        if dns_domain is not None and len(dns_domain)>0: # pragma: no cover
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

    def add_dhcp_interface(self, interface, option):
        """
        Add dhcp interface

        Args:
            interface (string): interface name
            option (int): interface option mask (none=0|hotplug=1|auto=2)

        Returns:
            bool: True if interface added
        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter(u'Parameter "interface" is missing')
        if option is None:
            raise MissingParameter(u'Parameter "option" is missing')
        if option not in range(0, self.OPTION_NONE + self.OPTION_AUTO + self.OPTION_HOTPLUG + 1):
            raise InvalidParameter(u'Parameter "option" is invalid')

        #check if interface is not already configured
        if self.get_configuration(interface) is not None:
            raise InvalidParameter(u'Interface "%s" is already configured' % interface)

        #add new configuration
        lines = []
        lines.append(u'\n')
        self.__append_option(option, lines, interface)
        lines.append(u'iface %s inet dhcp\n' % interface)

        return self.add_lines(lines)
