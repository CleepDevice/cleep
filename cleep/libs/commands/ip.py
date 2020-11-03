#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
try:
    from cleep.libs.internals.console import AdvancedConsole, Console
    from cleep.libs.internals import tools as Tools
except: # pragma no cover
    from console import AdvancedConsole, Console
import time
import os
import re

class Ip(AdvancedConsole):
    """
    Command /sbin/ip helper.
    """

    CACHE_DURATION = 5.0

    def __init__(self):
        """
        Constructor
        """
        AdvancedConsole.__init__(self)

        #members
        self._command = '/sbin/ip'
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

    def is_installed(self):
        """
        Return True if ip command is installed

        Returns:
            bool: True is installed
        """
        return os.path.exists(self._command)

    def get_status(self):
        """
        Get network status

        Returns:
            dict: network status by interfaces::

            {
                interface (string): {
                    interface (string): interface name
                    ipv4 (string): ipv4 address
                    netmask (string): netmask
                    ipv6 'string): ipv6 address
                    prefixlen (int): ipv6 prefix length
                    mac (string): mac address
                }
            }

        """
        results = self.find(
            '%s addr' % self._command,
            r'\d:\s+(\w+):.*|inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\/(\d+).*|inet6\s+(\w{1,4}::\w{1,4}:\w{1,4}:\w{1,4}:\w{1,4})\/(\d+).*|link\/ether\s+(\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2})'
        )
        self.logger.trace('Results: %s' % results)

        index = 1
        entry = None
        entries = {}
        for group, groups in results:
            groups = list(filter(lambda v: v is not None, groups))
            group = group.strip()

            if group.startswith('%s:' % index):
                index += 1
                # drop lo interface
                if groups[0] == 'lo':
                    self.logger.trace('Drop lo interface')
                    continue

                # save previous entry
                if entry:
                    self.logger.trace('Save entry in entries')
                    entries[entry['interface']] = entry

                # new entry
                entry = {
                    'interface': groups[0],
                    'ipv4': None,
                    'netmask': None,
                    'ipv6': None,
                    'prefixlen': None,
                    'mac': None,
                }

            elif group.startswith('inet6') and entry:
                # ipv6
                prefix = 0
                try:
                    prefix = int(groups[1])
                except: # pragma: no cover
                    self.logger.error('Invalid PrefixLen in command output')
                entry.update({
                    'ipv6': groups[0],
                    'prefixlen': prefix,
                })

            elif group.startswith('inet') and entry:
                # ipv4
                cidr = 24
                try:
                    cidr = int(groups[1])
                except: # pragma: no cover
                    self.logger.error('Invalid CIDR in command output')
                entry.update({
                    'ipv4': groups[0],
                    'netmask': Tools.cidr_to_netmask(cidr),
                })

            elif group.startswith('link') and entry:
                # mac
                entry.update({
                    'mac': groups[0],
                })

        # save last entry
        if entry and entry['interface'] not in entries:
            entries[entry['interface']] = entry

        return entries

    def restart_interface(self, interface_name):
        """
        Restart specified interface

        Warning:
            This function has 5 seconds sleep so make sure to set appropriate timeout if any

        Args:
            interface_name (string): interface name

        Returns:
            bool: True if interface restarted successfully
        """
        resp = self.command('%(command)s link set %(interface)s down && /bin/sleep 5 && %(command)s link set %(interface)s up' % {
            'command': self._command,
            'interface': interface_name,
        })

        return True if resp['returncode'] == 0 else False

