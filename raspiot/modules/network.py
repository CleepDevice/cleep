#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
from raspiot.utils import InvalidParameter, MissingParameter, CommandError, CommandInfo
from raspiot.raspiot import RaspIotModule
from raspiot.libs.wpasupplicantconf import WpaSupplicantConf
from raspiot.libs.dhcpcdconf import DhcpcdConf
from raspiot.libs.etcnetworkinterfaces import EtcNetworkInterfaces
from raspiot.libs.console import AdvancedConsole, Console
from raspiot.libs.ifconfig import Ifconfig
from raspiot.libs.iw import Iw
from raspiot.libs.iwlist import Iwlist
from raspiot.libs.iwconfig import Iwconfig
from raspiot.libs.ifupdown import Ifupdown
from raspiot.libs.wpacli import Wpacli
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
    MODULE_TAGS = ['wireless', 'wifi', 'ethernet']
    MODULE_COUNTRY = 'any'
    MODULE_LINK = None

    def __init__(self, bus, debug_enabled):
        """
        Constructor

        Params:
            bus (MessageBus): bus instance
            debug_enabled (bool): debug status
        """
        #init
        RaspIotModule.__init__(self, bus, debug_enabled)

        #tools
        self.etcnetworkinterfaces = EtcNetworkInterfaces()
        self.dhcpcd = DhcpcdConf()
        self.wpasupplicant = WpaSupplicantConf()
        self.iw = Iw()
        self.iwlist = Iwlist()
        self.ifconfig = Ifconfig()
        self.iwconfig = Iwconfig()
        self.ifupdown = Ifupdown()
        self.wpacli = Wpacli()

        #members
        self.wifi_networks = {}
        self.wifi_network_names = []
        self.wifi_interfaces = {}
        self.last_wifi_networks_scan = 0

    def _configure(self):
        """
        Module start
        """
        #refresh list of wifi networks
        self.refresh_wifi_networks()

    def get_module_config(self):
        """
        Return module configuration (wifi networks, ip address, ...)

        Returns:
            dict: module configuration::
                {
                    status (dict): current network status by interface (ip, gateway, ...)
                    configurations (dict): interfaces configurations
                    wifinetworks (dict): list of wifi networks by interfaces
                }
        """
        output = {}

        #get data
        configured_interfaces = self.etcnetworkinterfaces.get_configurations()
        current_status = self.ifconfig.get_configurations()

        #remove lo interface from interfaces list
        if u'lo' in configured_interfaces.keys():
            del configured_interfaces[u'lo']

        #add more infos
        for interface in configured_interfaces.keys():
            #add wifi infos
            if interface in self.wifi_interfaces.keys():
                configured_interfaces[interface][u'wifi'] = True
                configured_interfaces[interface][u'wifi_network'] = self.wifi_interfaces[interface][u'network']
            else:
                configured_interfaces[interface][u'wifi'] = False
                configured_interfaces[interface][u'wifi_network'] = None

            #add connection status
            if interface in current_status.keys():
                configured_interfaces[interface][u'connected'] = True
            else:
                configured_interfaces[interface][u'connected'] = False

        #prepare networks list
        networks = []

        #add wired interface as network
        for interface in configured_interfaces.keys():
            #if not configured_interfaces[interface][u'wifi']:
            if not interface in self.wifi_interfaces.keys():
                #get interface status
                network_status = None
                connected = False
                if interface in current_status.keys():
                    network_status = current_status[interface]
                    connected = True

                #save entry
                networks.append({
                    u'network': interface,
                    u'interface': interface,
                    u'wifi': False,
                    u'connected': connected,
                    u'config': configured_interfaces[interface],
                    u'status': network_status
                })

        #add all wifi networks on range
        for interface in self.wifi_networks:
            for network_name in self.wifi_networks[interface]:
                #get interface configuration
                #interface_config = None
                #if interface in configured_interfaces.keys():
                #    interface_config = configured_interfaces[interface]

                #get wifi config
                wifi_config = None
                if interface in self.wifi_networks.keys():
                    if network_name in self.wifi_networks[interface].keys():
                        wifi_config = self.wifi_networks[interface][network_name]
                
                #get interface status
                network_status = None
                if interface in current_status.keys():
                    network_status = current_status[interface]

                #get wifi connection
                connected = False
                if interface in self.wifi_interfaces.keys() and network_name==self.wifi_interfaces[interface][u'network']:
                    connected = True

                #save entry
                networks.append({
                    u'network': network_name,
                    u'interface': interface,
                    u'wifi': True,
                    u'connected': connected,
                    u'config': wifi_config,
                    u'status': network_status
                })

        #prepare output
        output[u'networks'] = networks
        output[u'wifiinterfaces'] = self.wifi_interfaces.keys()
        output[u'lastwifiscan'] = self.last_wifi_networks_scan

        return output

    def __restart_interface(self, interface):
        """
        Restart network interface

        Params:
            interface (string): network interface name
        """
        self.ifupdown.restart_interface(interface)

    #----------
    #WIRED AREA
    #----------

    def save_wired_static_configuration(self, interface, ip_address, gateway, netmask, fallback):
        """
        Save wired static configuration

        Params:
            interface (string): interface to configure
            ip_address (string): desired ip address
            gateway (string): gateway address
            netmask (string): netmask
            fallback (bool): is configuration used as fallback
        """
        res = False


        #then add new one
        if self.dhcpcd.installed():
            #use dhcpcd
            #TODO: handle dhcpcd + handle fallback option
            self.__delete_static_interface(interface)
            if not fallback:
                res = self.__add_static_interface(interface, ip_address, gateway, netmask)
            else:
                res = self.__add_fallback_interface(interface, ip_address, gateway, netmask)

        else:
            #use /etc/network/interfaces file

            #delete existing configuration for specified interface
            if not self.etcnetworkinterfaces.delete_interface(interface):
                self.logger.error('Unable to save wired static configuration: unable to delete interface %s' % interface)
                raise CommandError(u'Unable to save data')
            
            #finally add new configuration
            if not self.etcnetworkinterfaces.add_static_interface(interface, EtcNetworkInterfaces.OPTION_HOTPLUG, ip_address, gateway, netmask):
                self.logger.error('Unable to save wired static configuration: unable to add interface %s' % interface)
                raise CommandError(u'Unable to save data')

        #restart interface
        #self.__restart_interface(interface)

        return True

    def save_wired_dhcp_configuration(self, interface):
        """
        Save wired dhcp configuration

        Params:
            interface (string): interface name
        """
        if self.dhcpcd.installed():
            #save config using dhcpcd

            #TODO

            #get interface config
            config = self.dhcpcd.get_configuration(interface)
            self.logger.debug(u'Interface config in dhcpcd: %s' % config)
            if config is None:
                raise CommandError(u'Interface %s is not configured' % interface)

            #delete configuration for specified interface (not configuration is needed for dhcp)
            if not config[u'fallback']:
                self.__delete_static_interface(interface)
            else:
                self.__delete_fallback_interface(interface)

        else:
            #save config using /etc/network/interface file
            
            #get interface config
            config = self.etcnetworkinterfaces.get_configuration(interface)
            self.logger.debug(u'Interface config in /etc/network/interfaces: %s' % config)
            if config is None:
                raise CommandError(u'Interface %s is not configured' % interface)

            #delete existing configuration for specified interface
            if not self.etcnetworkinterfaces.delete_interface(interface):
                self.logger.error('Unable to save wired dhcp configuration: unable to delete interface %s' % interface)
                raise CommandError(u'Unable to save data')
            
            #finally add new configuration
            if not self.etcnetworkinterfaces.add_dhcp_interface(interface, EtcNetworkInterfaces.OPTION_AUTO + EtcNetworkInterfaces.OPTION_HOTPLUG):
                self.logger.error('Unable to save wired dhcp configuration: unable to add interface %s' % interface)
                raise CommandError(u'Unable to save data')

        #restart interface
        #self.__restart_interface(interface)

        return True


    #-------------
    #WIRELESS AREA
    #-------------

    def __scan_wifi_networks(self, interface):
        """
        Scan wifi networks and store them in class member wifi_networks

        TODO:
            iwconfig/iwlist seems to be deprecated, we need to replace it with iw command
            https://dougvitale.wordpress.com/2011/12/21/deprecated-linux-networking-commands-and-their-replacements/

        Note:
            https://ubuntuforums.org/showthread.php?t=1402284 for different iwlist samples

        Args:
            interface (string): interface to use to scan networks

        Returns:
            dict: list of found wifi networks::
                {
                    network name (string): {
                        interface (string): interface on which wifi network was found
                        network (string): network name (essid)
                        encryption (string): network encryption (wpa|wpa2|wep|unsecured|unknown)
                        signallevel (float): signal level (in %)
                    },
                    ...
                }

        """
        #check params
        if interface is None or len(interface)==0:
            raise MissingParameter('Interface parameter is missing')

        #get wireless configuration
        wifi_config = self.wpasupplicant.get_configurations()
        self.logger.debug('Wifi config: %s' % wifi_config)

        #get networks
        networks = self.iwlist.get_networks(interface)
        self.logger.debug('Wifi networks: %s' % networks)

        #set some configuration flags
        for network in networks.keys():
            networks[network][u'hidden'] = False
            if network in wifi_config.keys():
                networks[network][u'configured'] = True
                networks[network][u'disabled'] = wifi_config[network][u'disabled']
            else:
                networks[network][u'configured'] = False
                networks[network][u'disabled'] = False

        #add hidden network
        count = 0
        for network in wifi_config.keys():
            if wifi_config[network][u'hidden']:
                networks[wifi_config[network][u'network']] = {
                    u'encryption': wifi_config[network][u'encryption'],
                    u'interface': None,
                    u'network': wifi_config[network][u'network'],
                    u'configured': True,
                    u'disabled': wifi_config[network][u'disabled']
                }
                count += 1

        #refresh cache
        self.wifi_networks[interface] = networks

        return networks

    def refresh_wifi_networks(self):
        """
        Scan wifi networks for all connected interfaces

        Return:
            dict: found wifi networks
        """
        self.wifi_networks = {}
        self.wifi_network_names = []

        #get wifi interfaces and connected network
        self.wifi_interfaces = self.iwconfig.get_interfaces()

        #scan networks for each interfaces
        for interface in self.wifi_interfaces.keys():
            #scan interface
            networks = self.__scan_wifi_networks(interface)

            #save network names
            self.wifi_network_names = self.wifi_network_names + list(set(networks) - set(self.wifi_network_names))

        self.last_wifi_networks_scan = int(time.time())

        self.logger.debug('Wifi networks: %s' % self.wifi_networks)
        self.logger.debug('Wifi network names: %s' % self.wifi_network_names)

        return self.wifi_networks

    def test_wifi_network(self, interface, network, password=None, encryption=None, hidden=False):
        """ 
        Try to connect to specified wifi network. Save anything and revert back to original state after test.

        Args:
            interface (string) interface name
            network (string): network name
            password (string): password
            encryption (wpa|wpa2|wep|unsecured): network encryption
            hidden (bool) hidden network

        Raises:
            CommandError
        """
        #create test wpa_supplicant.conf file
        test_wpasupplicant = u'/tmp/test_wpa_%s.conf' % unicode(uuid.uuid4())
        if not self.wpasupplicant.write_fake_wpasupplicant(test_wpasupplicant, network, encryption, password, hidden):
            self.logger.error(u'Unable to generate fake wpasupplicant file for testing (%s)' % test_wpasupplicant)
            raise Exception(u'Unable to connect to network: internal error')

        c = Console()
        error = None
        try:

            #kill wpa_supplicant and wpa_cli processes
            res = c.command(u'/usr/bin/pkill -9 -f "/sbin/wpa_.*%s"' % interface)
            self.logger.debug(u'pkill output: %s' % res)
    
            #try to connect
            log_file = u'/tmp/wpa_%s.log' % unicode(uuid.uuid4())
            error_file = u'/tmp/error_%s.log' % unicode(uuid.uuid4())
            self.logger.debug('FILES = %s %s' % (log_file, error_file))
            res = c.command(u'/sbin/wpa_supplicant -i %s -c %s -t -f %s 2> %s' % (interface, test_wpasupplicant, log_file, error_file), 10.0)
            #self.logger.debug('wpa_supplicant output: %s' % res)
            #if res[u'error'] or res[u'killed']:
            #    raise Exception(u'Unable to connect to network: is network in range?')

            #wpa_supplicant command can only be killed by CTRL-C because it uses wpa_cli
            #so we need to kill it explicitely
            res = c.command(u'/usr/bin/pkill -9 -f "/sbin/wpa_supplicant.*%s"' % interface)
            self.logger.debug(u'pkill output: %s' % res)

            #parse result
            with open(log_file) as f:
                lines = f.readlines()
            with open(error_file) as f:
                lines += f.readlines()
            self.logger.debug('lines: %s' % u''.join(lines))
            groups = re.findall(r'(CTRL-EVENT-SSID-TEMP-DISABLED).*reason=(.*?)\s|(CTRL-EVENT-CONNECTED)|(CTRL-EVENT-DISCONNECTED)|(pre-shared key may be incorrect)', '\n'.join(lines))
            connection_failed = False
            connection_succeed = False
            invalid_password = False
            for group in groups:
                group = filter(None, group)
                self.logger.debug('group: %s' % group)
                if group[0] is not None and len(group[0])>0:
                    if group[0]==u'CTRL-EVENT-SSID-TEMP-DISABLED' and group[1]==u'WRONG_KEY':
                        #true invalid password detected, stop statement
                        self.logger.debug(u'Test network: invalid password')
                        invalid_password = True
                        connection_failed = True
                        break

                    elif group[0]==u'CTRL-EVENT-CONNECTED':
                        #connection successful detected, stop statement
                        self.logger.debug(u'Connection to network succeed')
                        connection_failed = False
                        connection_succeed = True
                        break

                    elif group[0]==u'CTRL-EVENT-DISCONNECTED':
                        #connection failure for unknow reason, continue parsing to get reason
                        connection_failed = True

                    elif group[0]==u'pre-shared key may be incorrect':
                        #maybe invalid password specified
                        invalid_password = True

            #check result
            if connection_failed and invalid_password:
                raise Exception(u'Unable to connect: invalid password specified')
            elif hidden:
                raise Exception('Unable to connect: invalid infos specified for hidden network')
            elif connection_failed or not connection_succeed:
                raise Exception(u'Unable to connect: problem with wifi')

        except Exception as e:
            error = unicode(e)

        finally:
            #remove temp files
            try:
                os.remove(test_wpasupplicant)
                os.remove(log_file)
                os.remove(error_file)
            except:
                pass

            #kill all wpa_ instances
            res = c.command(u'/usr/bin/pkill -9 -f "/sbin/wpa_.*%s"' % interface)
            self.logger.debug(u'pkill output: %s' % res)

            #reconfigure interface (stop-start-reconfigure)
            self.reconfigure_interface(interface)

        if error:
            raise CommandError(error)

        return True

    def save_wifi_network(self, interface, network, password=None, encryption=None, hidden=False):
        """
        Save wifi network configuration

        Args:
            interface (string): interface
            network (string): network to connect interface to
            password (string): network connection password
            encryption (string): encryption type (wpa|wpa2|wep|unsecured)
            hidden (bool): True if network is hidden

        Returns:
            bool: True if connection succeed

        Raises:
            CommandError
        """
        #save config in wpa_supplicant.conf file
        if not self.wpasupplicant.add_network(network, encryption, password, hidden):
            raise CommandError('Unable to save configuration')

        #reconfigure interface
        return self.wpacli.reconfigure_interface(interface)

    def delete_wifi_network(self, interface, network):
        """
        Delete specified network

        Args:
            network (string): network config to delete

        Return:
            bool: True if network deleted
        """
        if not self.wpasupplicant.delete_network(network):
            raise CommandError(u'Unable to delete network')

        #reconfigure interface
        return self.wpacli.reconfigure_interface(interface)

    def update_wifi_network_password(self, interface, network, password):
        """
        Update wifi network configuration

        Args:
            interface (string): interface name
            network (string): network to connect interface to
            password (string): network connection password

        Returns:
            bool: True if update succeed

        Raises:
            CommandError
        """
        if not self.wpasupplicant.update_network_password(network, password):
            raise CommandError(u'Unable to update password')

        #reconfigure interface
        return self.wpacli.reconfigure_interface(interface)

    def enable_wifi_network(self, interface, network):
        """
        Enable wifi network

        Args:
            interface (string): interface name
            network (string): network name

        Return:
            bool: True if network updated

        Raises:
            CommandError
        """
        if not self.wpasupplicant.enable_network(network):
            raise CommandError(u'Unable to enable network')

        #reconfigure interface
        return self.wpacli.reconfigure_interface(interface)

    def disable_wifi_network(self, interface, network):
        """
        Disable wifi network

        Args:
            interface (string): interface name
            network (string): network name

        Return:
            bool: True if network updated

        Raises:
            CommandError
        """
        if not self.wpasupplicant.disable_network(network):
            raise CommandError(u'Unable to enable network')

        #reconfigure interface
        return self.wpacli.reconfigure_interface(interface)

    def reconfigure_interface(self, interface):
        """
        Reconfigure specified interface

        Args:
            interface (string): interface to reconfigure

        Return:
            bool: True if command succeed
        """
        if interface is None or len(interface)==0:
            raise MissingParameter('Parameter interface is missing')
        if interface not in self.wifi_interfaces.keys():
            raise InvalidParameter('Interface %s does\t exist or is not configured' % interface)

        #restart network interface
        if not self.ifupdown.restart_interface(interface):
            return False

        #reconfigure interface
        return self.wpacli.reconfigure_interface(interface)

