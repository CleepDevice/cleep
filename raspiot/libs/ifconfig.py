#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
import netifaces
import time


class Ifconfig():
    """
    Command /sbin/ifconfig
    
    Note:
        Command ifconfig parsing is replaced by netifaces library
    """

    CACHE_DURATION = 5.0

    def __init__(self):
        """
        Constructor
        """
        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        self.timestamp = None
        self.interfaces = {}

    def __refresh(self):
        """
        Refresh all data
        """
        #check if refresh is needed
        if self.timestamp is not None and time.time()-self.timestamp<=self.CACHE_DURATION:
            self.logger.debug('Don\'t refresh')
            return

        entries = {}
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            #drop some interfaces
            if interface=='lo':
                continue

            #get raw data
            ifaddresses = netifaces.ifaddresses(interface)
            gateways = netifaces.gateways()

            #get mac address
            mac = None
            if len(ifaddresses[netifaces.AF_LINK])>0 and u'addr' in ifaddresses[netifaces.AF_LINK][0].keys():
                mac = ifaddresses[netifaces.AF_LINK][0]['addr']

            #ipv4
            ipv4 = None
            netmask_ipv4 = None
            if netifaces.AF_INET in ifaddresses.keys() and len(ifaddresses[netifaces.AF_INET])>0 and u'addr' in ifaddresses[netifaces.AF_INET][0].keys():
                ipv4 = ifaddresses[netifaces.AF_INET][0]['addr']
                netmask_ipv4 = ifaddresses[netifaces.AF_INET][0]['netmask']
            gateway_ipv4 = None
            if netifaces.AF_INET in gateways.keys():
                if gateways[netifaces.AF_INET][0][1]==interface:
                    gateway_ipv4 = gateways[netifaces.AF_INET][0][0]

            #ipv6
            ipv6 = None
            netmask_ipv6 = None
            if netifaces.AF_INET6 in ifaddresses.keys() and len(ifaddresses[netifaces.AF_INET6])>0 and u'addr' in ifaddresses[netifaces.AF_INET6][0].keys():
                ipv6 = ifaddresses[netifaces.AF_INET6][0]['addr']
                netmask_ipv6 = ifaddresses[netifaces.AF_INET6][0]['netmask']
            gateway_ipv6 = None
            if netifaces.AF_INET6 in gateways.keys():
                if gateways[netifaces.AF_INET6][0][1]==interface:
                    gateway_ipv6 = gateways[netifaces.AF_INET6][0][0]

            entries[interface] = {
                u'interface': interface,
                u'mac': mac,
                u'ipv4': ipv4,
                u'gateway_ipv4': gateway_ipv4,
                u'netmask_ipv4': netmask_ipv4,
                u'ipv6': ipv6,
                u'gateway_ipv6': gateway_ipv6,
                u'netmask_ipv6': netmask_ipv6
            }

        #save interfaces
        self.interfaces = entries

        #update timestamp
        self.timestamp = time.time()

    def get_configurations(self):
        """
        Return current network configuration

        Return:
            dict: interfaces configurations::
                {
                    interface1: {
                        interface (string)): interface name
                        mac (string): mac address
                        ipv4 (string): ipv4
                        gateway_ipv4 (string): gateway ipv4
                        netmask_ipv4 (string): gateway ipv4
                        ipv6 (string): ipv6
                        gateway_ipv6 (string): gateway ipv6
                        netmask_ipv6 (string): gateway ipv6
                    },
                    ...
                }
        """
        self.__refresh()

        return self.interfaces

