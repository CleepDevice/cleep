#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
from cleep.exception import InvalidParameter, MissingParameter
from cleep.libs.configs.config import Config
from cleep.libs.internals.console import Console
from cleep.libs.internals.tools import netmask_to_cidr, cidr_to_netmask


class DhcpcdConf(Config):
    """
    Helper class to update and read /etc/dhcpcd.conf file.

    Note:
        see https://wiki.archlinux.org/index.php/dhcpcd
    """

    CONF = "/etc/dhcpcd.conf"

    def __init__(self, cleep_filesystem, backup=True):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            backup (bool): True if backup enabled
        """
        Config.__init__(self, cleep_filesystem, self.CONF, "#", backup)

    def is_installed(self):
        """
        Check if config file exists and dhcpcd daemon is running

        Returns:
            bool: True if all is fine
        """
        if os.path.exists(self.CONF):
            console = Console()
            res = console.command("/usr/bin/pgrep dhcpcd | /usr/bin/wc -l")
            if not res["error"] and not res["killed"] and res["stdout"][0] == "1":
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
        results = self.find(
            r"^(?:interface\s(.*?))$|^(?:static (.*?)=(.*?))$|^(?:fallback\s(\w+_\w+))$|^(?:profile\s(\w+_\w+))$",
            re.UNICODE | re.MULTILINE,
        )
        current_entry = None
        for group, groups in results:
            # init variables
            new_entry = None

            # filter none values
            groups = list(filter(None, groups))

            if group.startswith("interface"):
                new_entry = groups[0]
            elif group.startswith("profile"):
                new_entry = groups[0]
            elif current_entry is not None:
                if group.startswith("static ip_address"):
                    # format: X.X.X.X[/X]
                    splits = groups[1].split("/")
                    current_entry["ip_address"] = splits[0]
                    try:
                        netmask = cidr_to_netmask(int(splits[1]))
                        current_entry["netmask"] = netmask
                    except Exception:  # pragma: no cover
                        current_entry["netmask"] = "255.255.255.0"
                if group.startswith("static routers"):
                    # format: X.X.X.X
                    current_entry["gateway"] = groups[1]
                if group.startswith("static domain_name_servers"):
                    # format: X.X.X.X [X.X.X.X]...
                    current_entry["dns_address"] = groups[1]
                if group.startswith("fallback"):
                    # format: <interface id>
                    current_entry["fallback"] = groups[0]

            if new_entry is not None:
                # add new entry
                current_entry = {
                    "group": group,
                    "interface": new_entry,
                    "netmask": None,
                    "fallback": None,
                    "ip_address": None,
                    "gateway": None,
                    "dns_address": None,
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
        # check params
        if interface is None or len(interface) == 0:
            raise MissingParameter('Parameter "interface" is missing')

        interfaces = self.get_configurations()
        if interface in interfaces:
            return interfaces[interface]

        return None

    def add_static_interface(
        self, interface, ip_address, gateway, netmask, dns_address=None
    ):
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
        # check params
        if interface is None or len(interface) == 0:
            raise MissingParameter('Parameter "interface" is missing')
        if ip_address is None or len(ip_address) == 0:
            raise MissingParameter('Parameter "ip_address" is missing')
        if gateway is None or len(gateway) == 0:
            raise MissingParameter('Parameter "gatewa"y is missing')
        if netmask is None or len(netmask) == 0:
            raise MissingParameter('Parameter "netmask" is missing')

        # check if interface is not already configured
        if self.get_configuration(interface) is not None:
            raise InvalidParameter(f"Interface {interface} is already configured")

        # get CIDR value
        cidr = netmask_to_cidr(netmask)

        # fix dns
        if dns_address is None:
            dns_address = gateway

        # add new configuration
        lines = []
        lines.append(f"\ninterface {interface}\n")
        lines.append(f"static ip_address={ip_address}/{cidr}\n")
        lines.append(f"static routers={gateway}\n")
        lines.append(f"static domain_name_servers={dns_address}\n")

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
        # delete interface configuration lines
        count = self.remove_after(
            rf"^\s*interface\s*{interface['interface']}\s*$", r"^\s*static.*$", 4
        )
        if count != 4:  # pragma: no cover
            return False

        return True

    def add_fallback_interface(
        self, interface, ip_address, gateway, netmask, dns_address=None
    ):
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
        # check params
        if interface is None or len(interface) == 0:
            raise MissingParameter('Parameter "interface" is missing')
        if ip_address is None or len(ip_address) == 0:
            raise MissingParameter('Parameter "ip_address" is missing')
        if gateway is None or len(gateway) == 0:
            raise MissingParameter('Parameter "gateway" is missing')
        if netmask is None or len(netmask) == 0:
            raise MissingParameter('Parameter "netmask" is missing')

        # check if interface is not already configured
        if self.get_configuration(interface) is not None:
            raise InvalidParameter(f"Interface {interface} is already configured")

        # fix dns
        if dns_address is None or len(dns_address) == 0:
            dns_address = gateway

        # prepare configuration content
        lines = []
        lines.append(f"\nprofile fallback_{interface}\n")
        lines.append(
            f"static ip_address={ip_address}/{netmask_to_cidr(netmask)}\n"
        )
        lines.append(f"static routers={gateway}\n")
        lines.append(f"static domain_name_servers={dns_address}\n")
        lines.append(f"\ninterface {interface}\n")
        lines.append(f"fallback fallback_{interface}\n")

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
        # delete interface data and find profile name
        count = self.remove_after(
            rf"^\s*interface\s*{interface['interface']}\s*$",
            r"^\s*fallback\s*(.*?)\s*$",
            2,
        )
        if count != 2:  # pragma: no cover
            return False

        # delete profile data
        if interface["fallback"] is not None:
            count = self.remove_after(
                rf"^\s*profile\s*{interface['fallback']}\s*$", r"^\s*static.*$", 6
            )
            if count != 4:  # pragma: no cover
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
        # check params
        if interface_name is None or len(interface_name) == 0:
            raise MissingParameter('Parameter "interface_name" is missing')

        # get interface
        interface = self.get_configuration(interface_name)
        if interface is None:
            # interface not found
            self.logger.debug(f"Interface {interface_name} not found")
            return False

        if interface["fallback"] is not None:
            return self.__delete_fallback_interface(interface)
        return self.__delete_static_interface(interface)
