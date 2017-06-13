#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
from raspiot.utils import InvalidParameter, MissingParameter, CommandError, CommandInfo
from raspiot.raspiot import RaspIotModule
from raspiot.libs.wpasupplicantconf import WpaSupplicantConf
from raspiot.libs.dhcpcdconf import DhcpcdConf
from raspiot.libs.console import Console
import re
import time
import os
import uuid

__all__ = ['Network']


class Network(RaspIotModule):
    """
    Network module allows user to configure wired and wifi connection

    Note:
        https://donnutcompute.wordpress.com/2014/04/20/connect-to-wi-fi-via-command-line/ iw versus iwconfig (deprecated)
        https://www.raspberrypi.org/documentation/configuration/ official raspberry pi foundation configuration guide
        https://www.blackmoreops.com/2014/09/18/connect-to-wifi-network-from-command-line-in-linux/ another super guide ;)
    """

    MODULE_DEPS = []
    MODULE_DESCRIPTION = 'Network configuration helper'
    MODULE_LOCKED = True
    MODULE_URL = None
    MODULE_TAGS = []

    def __init__(self, bus, debug_enabled):
        """
        Constructor

        Params:
            bus (MessageBus): bus instance
            debug_enabled (bool): debug status
        """
        #init
        RaspIotModule.__init__(self, bus, debug_enabled)

        #members
        self.wifi_networks = {}
        self.interfaces = {}

    def _start(self):
        """
        Module start
        """
        self.wifi_networks = self.scan_wifi_networks()

    def get_module_config(self):
        """
        Return module configuration (wifi networks, ip address, ...)

        Returns:
            dict: module configuration
        """
        config = {}
        self.interfaces = self.get_interfaces_configurations()
        config[u'interfaces'] = self.interfaces
        config[u'wifi_networks'] = self.wifi_networks

        return config

    def __restart_interface(self, interface):
        """
        Restart network interface

        Params:
            interface (string): network interface name
        """
        c = Console()
        res = c.command(u'/bin/ip link set %s up' % interface)
        self.logger.debug(res)
        res = c.command(u'/sbin/ifdown %s' % interface)
        self.logger.debug(res)
        res = c.command(u'/sbin/ifup %s' % interface)
        self.logger.debug(res)

    def __get_interface_names(self):
        """
        Return interface names

        Returns:
            list: network interface names
        """
        c = Console()
        res = c.command(u'/bin/ls -1 /sys/class/net')

        if res[u'error'] or res[u'killed']:
            raise Exception(u'Unable to get interfaces names')

        output = [line.strip() for line in res[u'stdout']]
        output.remove(u'lo')
        self.logger.debug(u'Interface names=%s' % output)

        return output

    def __get_wired_config(self):
        """
        Return wired configuration

        Returns:
            list: wired interfaces list
        """
        #get interfaces from dhcpcd.conf file
        d = DhcpcdConf()
        interfaces = d.get_interfaces()
        self.logger.debug(u'Wired interfaces: %s' % interfaces)

        return interfaces

    def __get_wifi_interfaces(self):
        """
        Return list of wifi interfaces

        Returns:
            list: wifi interfaces list
        """
        interfaces = {}
        c = Console()
        res = c.command(u'/sbin/iw dev | grep Interface')

        if res[u'error'] or res[u'killed']:
            self.logger.info(u'Unable to get interfaces names (certainly iw bin not exists)')
            return interfaces

        output = [line.strip() for line in res[u'stdout']]
        names = [line.replace(u'Interface ', '') for line in output]
        self.logger.debug(u'Wifi interfaces: %s' % interfaces)

        #get connection status
        regex = r'(SSID):\s*(.*?)\s'
        for name in names:
            connected = False
            network = None
            res = c.command(u'/sbin/iw %s link' % name)
            if not res[u'error'] and not res[u'killed']:
                groups = re.findall(regex, ''.join(res[u'stdout']), re.DOTALL)
                for group in groups:
                    group = filter(None, group)
                    self.logger.debug(group)
                    if group[0] is not None and len(group[0])>0:
                        if group[0]==u'SSID':
                            connected = True
                            network = group[1]

            interfaces[name] = {
                u'name': name,
                u'connected': connected,
                u'network': network
            }

        return interfaces

    def get_interfaces_configurations(self):
        """
        Return interfaces configurations as returned by ifconfig command

        Returns:
            dict: dict of interfaces
        """
        interfaces = {}

        #get interface names
        names = self.__get_interface_names()

        #get wifi interfaces
        wifis = self.__get_wifi_interfaces()

        #get wired interfaces configurations
        wired_configs = self.__get_wired_config()
        
        regex = r'(HWaddr)\s*(.{2}:.{2}:.{2}:.{2}:.{2}:.{2})|(inet addr):(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})|(Bcast):(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})|(Mask):(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})|(inet6 addr):\s*(.{4}::.{4}:.{4}:.{4}:.{1,4}/\d{1,4})'
        for name in names:
            #get infos
            c = Console()
            res = c.command(u'/sbin/ifconfig %s' % name)
            if res[u'error'] or res[u'killed']:
                raise CommandError(u'Unable to get network configuration')
            self.logger.debug(u''.join(res[u'stdout']))

            #add wifi status
            wifi = False
            wifi_network = None
            wifi_encryption = None
            wifi_signal_level = 0
            if name in wifis:
                wifi = True
                if wifis[name][u'connected']:
                    wifi_network = wifis[name][u'network']
                    if wifi_network in self.wifi_networks:
                        wifi_encryption = self.wifi_networks[wifi_network][u'encryption']
                        wifi_signal_level = self.wifi_networks[wifi_network][u'signal_level']

            #add wired status
            dhcp = True
            fallback = False
            ip_address = None
            routers = None
            name_server = None
            if name in wired_configs:
                dhcp = False
                fallback = wired_configs[name][u'fallback']
                ip_address = wired_configs[name][u'ip_address']
                routers = wired_configs[name][u'routers']
                domain_name_servers = wired_configs[name][u'domain_name_servers']

            #extract useful data
            ipv4 = None
            ipv6 = None
            broadcast = None
            mac = None
            mask = None
            groups = re.findall(regex, ''.join(res[u'stdout']), re.DOTALL)
            for group in groups:
                group = filter(None, group)
                if group[0] is not None and len(group[0])>0:
                    if group[0]==u'HWaddr':
                        mac = group[1]
                    elif group[0]==u'inet addr':
                        ipv4 = group[1]
                    elif group[0]==u'Bcast':
                        broadcast = group[1]
                    elif group[0]==u'Mask':
                        mask = group[1]
                    elif group[0]==u'inet6 addr':
                        ipv6 = group[1]
            
            #save data
            interfaces[name] = {
                u'interface': name,
                u'ipv4': ipv4,
                u'ipv6': ipv6,
                u'mask': mask,
                u'broadcast': broadcast,
                u'mac': mac,
                u'wifi': wifi,
                u'wifi_network': wifi_network,
                u'wifi_encryption': wifi_encryption,
                u'wifi_signal_level': wifi_signal_level,
                u'dhcp': dhcp,
                u'fallback': fallback,
                u'ip_address': ip_address,
                u'routess': routers,
                u'domain_name_servers': domain_name_servers
            }

        return interfaces

    def __add_static_interface(self, interface, ip_address, routers, domain_name_servers):
        """
        Configure wired static interface

        Params:
            interface (string): interface name
            ip_address (string): ip address
            routers (string): router address
            domain_name_servers (string): domain name servers
        """
        conf = DhcpcdConf()
        return conf.add_static_interface(interface, ip_address, routers, domain_name_servers)

    def __add_fallback_interface(self, interface, ip_address, routers, domain_name_servers):
        """
        Configure wired fallback interface

        Params:
            interface (string): interface name
            ip_address (string): ip address
            routers (string): router address
            domain_name_servers (string): domain name servers
        """
        conf = DhcpcdConf()
        return conf.add_fallback_interface(interface, ip_address, routers, domain_name_servers)

    def __delete_static_interface(self, interface):
        """
        Unconfigure wired static interface

        Params:
            interface (string): interface name
        """
        conf = DhcpcdConf()
        return conf.delete_static_interface(interface)

    def __delete_fallback_interface(self, interface):
        """
        Unconfigure wired fallback interface

        Params:
            interface (string): interface name
        """
        conf = DhcpcdConf()
        return conf.delete_fallback_interface(interface)

    def __add_wifi_network(self, network, encryption, password, hidden):
        """
        Add new wifi network configuration
        Params:
            network (string): network name (ssid)
            encryption (wpa|wpa2|wep|unsecured): network encryption
            password (string): network password (it will be saved encrypted)
            hidden (bool): hidden network (bool)
        """
        conf = WpaSupplicantConf()
        return conf.add_network(network, encryption, password, hidden)

    def __delete_wifi_network(self, network):
        """
        Remove wifi network configuration
        Params:
            network (string): network name
        """
        conf = WpaSupplicantConf()
        return conf.delete_network(network)

    def save_wired_static_configuration(self, interface, ip_address, routers, domain_name_servers, fallback):
        """
        Save wired static configuration

        Params:
            interface (string): interface to configure
            ip_address (string): desired ip address
            routers (string): router address (usually gateway)
            domain_name_servers (string): domain name server (usually gateway)
            fallback (bool): is configuration used as fallback
        """
        res = False

        #delete interface first (if configured)
        self.__delete_static_interface(interface)

        #then add new one
        if not fallback:
            res = self.__add_static_interface(interface, ip_address, routers, domain_name_servers)
        else:
            res = self.__add_fallback_interface(interface, ip_address, routers, domain_name_servers)

        #restart interface
        #self.__restart_interface(interface)

        if not res:
            raise CommandError('Unable to configure interface')

        return True

    def save_wired_dhcp_configuration(self, interface):
        """
        Save wired dhcp configuration

        Params:
            interface (string): interface name
        """
        #get current interface configuration
        d = DhcpcdConf()
        config = d.get_interface(interface)
        self.logger.debug(u'Interface config: %s' % config)
        if config is None:
            raise CommandError(u'Interface %s is not configured' % interface)

        #delete configuration for specified interface
        if not config[u'fallback']:
            self.__delete_static_interface(interface)
        else:
            self.__delete_fallback_interface(interface)

        #restart interface
        #self.__restart_interface(interface)

        return True

    def scan_wifi_networks(self):
        """
        Scan wifi networks

        Note:
            https://ubuntuforums.org/showthread.php?t=1402284 for different iwlist samples
        """
        networks = {}

        #get interface names
        names = self.__get_interface_names()

        regex = r'(ESSID):\"(.*?)\"|(IE):\s*(.*)|(Encryption key):(.*)|(Signal level)=(\d{1,3})/100'
        for name in names:
            #get infos
            c = Console()
            res = c.command(u'/sbin/iwlist %s scan' % name, 15.0)
            if res[u'error'] or res[u'killed']:
                #error occured, but it's maybe because interface is not wifi
                continue
            self.logger.debug(''.join(res[u'stdout']))

            #extract interesting data
            essid = None
            security = None
            network_wpa = False
            network_wpa2 = False
            encryption = None
            signal_level = None
            groups = re.findall(regex, u'\n'.join(res[u'stdout']))
            self.logger.debug(groups)
            for group in groups:
                group = filter(None, group)
                self.logger.debug(group)
                if group[0] is not None and len(group[0])>0 and len(group)>=2:
                    if group[0]==u'ESSID':
                        essid = group[1]
                    elif group[0]==u'IE' and group[1].lower().find(u'wpa2'):
                        network_wpa2 = True
                    elif group[0]==u'IE' and group[1].lower().find(u'wpa'):
                        network_wpa = True
                    elif group[0]==u'Encryption key':
                        security = group[1]
                    elif group[0]==u'Signal level':
                        if group[1].isdigit():
                            signal_level = float(group[1])
                        else:
                            signal_level = group[1]

            #adjust network type
            if network_wpa2:
                encryption = WpaSupplicantConf.ENCRYPTION_TYPE_WPA2
            elif network_wpa:
                encryption = WpaSupplicantConf.ENCRYPTION_TYPE_WPA
            elif security==u'on':
                encryption = WpaSupplicantConf.ENCRYPTION_TYPE_WEP
            elif security==u'off':
                encryption = WpaSupplicantConf.ENCRYPTION_TYPE_UNSECURED
            else:
                encryption = WpaSupplicantConf.ENCRYPTION_TYPE_UNKNOWN
            
            #save data
            networks[essid] = {
                u'interface': name,
                u'network': essid,
                u'encryption': encryption,
                u'signal_level': signal_level
            }

        #save found networks
        self.wifi_networks = networks

        return networks

    def test_wifi_network(self, interface, network, encryption, password, hidden):
        """
        Try to connect to specified wifi network. Save anything or revert back to original state after test.

        Params:
            interface (string) interface name
            network (string): network name
            encryption (wpa|wpa2|wep|unsecured): network encryption
            password (string): password
            hidden (bool) hidden network

        Raises:
            CommandError, CommandInfo
        """
        c = Console()
        error = None
        try:
            #add network configuration
            self.__add_wifi_network(network, encryption, password, hidden)
            time.sleep(1.0)

            #stop wpa_supplicant daemon
            res = c.command(u'/usr/bin/pkill -f wpa_supplicant')
            self.logger.debug(res)
    
            #try to connect
            wpafile = u'/tmp/wpa_%s.log' % unicode(uuid.uuid4())
            res = c.command(u'/sbin/wpa_supplicant -i %s -c /etc/wpa_supplicant/wpa_supplicant.conf -f %s' % (interface, wpafile), 8.0)
            self.logger.debug(res)

            #wpa_supplicant command can only be killed by CTRL-C because it uses wpa_cli
            #so we need to kill it explicitely
            res = c.command(u'/usr/bin/pkill -f wpa_supplicant')
            self.logger.debug(res)

            #parse result
            with open(wpafile) as f:
                lines = f.readlines()
            os.remove(wpafile)
            self.logger.debug(lines)
            groups = re.findall(r'(CTRL-EVENT-SSID-TEMP-DISABLED).*reason=(.*?)\s|(CTRL-EVENT-CONNECTED)', '\n'.join(lines))
            for group in groups:
                group = filter(None, group)
                self.logger.debug(group)
                if group[0] is not None and len(group[0])>0:
                    if group[0]==u'CTRL-EVENT-SSID-TEMP-DISABLED' and group[1]==u'WRONG_KEY':
                        #invalid password detected
                        raise Exception(u'Invalid password')
                    elif group[0]==u'CTRL-EVENT-CONNECTED':
                        #connection successful
                        break

        except Exception as e:
            error = unicode(e)
    
        finally:
            #always delete wifi config
            self.logger.debug(u'Delete wifi config for %s' % interface)
            self.__delete_wifi_network(network)

            #and relaunch wpa_supplicant
            self.__restart_interface(interface)

        if error:
            raise CommandError(error)
        raise CommandInfo(u'Connection to %s successful' % network)

    def save_wifi_network(self, interface, network, encryption, password, hidden):
        """
        Save wifi network

        Params:
            interface (string) interface name
            network (string): network name
            encryption (wpa|wpa2|wep|unsecured): network encryption
            password (string): password
            hidden (bool) hidden network

        Raises:
            CommandError, CommandInfo
        """
        c = Console()
        error = None
        try:
            #add network configuration
            self.__add_wifi_network(network, encryption, password, hidden)
            time.sleep(1.0)

            #and relaunch wpa_supplicant that will connect automatically
            self.__restart_interface(interface)

        except Exception as e:
            error = unicode(e)

        #wait few seconds to make sure interface is refreshed
        time.sleep(4.0)
    
        if error:
            raise CommandError(error)
        raise CommandInfo(u'Connected to %s' % network)

    def disconnect_wifi(self, network):
        """
        Disconnect from specified wifi network

        Params:
            network (string): network name
        """
        c = Console()

        #get network interface
        interface = None
        for name in self.interfaces:
            if self.interfaces[name][u'wifi_network']==network:
                interface = name
                break
        self.logger.debug(u'Found interface to restart %s' % interface)
        if interface is None:
            raise CommandError(u'No network interface found for network %s' % network)

        #delete network from configuration
        self.__delete_wifi_network(network)

        #restart interface
        self.__restart_interface(interface)

        #wait few seconds to make sure interface is refreshed
        time.sleep(4.0)

        #reload configuration
        self.get_interfaces_configurations()

        raise CommandInfo(u'Disconnected from %s' % network)

