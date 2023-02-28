#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
from cleep.libs.internals.console import AdvancedConsole
from cleep.libs.configs.wpasupplicantconf import WpaSupplicantConf
import cleep.libs.internals.tools as Tools
from cleep.exception import MissingParameter, InvalidParameter


class Wpacli(AdvancedConsole):
    """
    Command /sbin/wpa_cli helper

    Note:
        Man page https://www.freebsd.org/cgi/man.cgi?wpa_cli
    """

    STATUS_CURRENT = 2
    STATUS_DISABLED = 0
    STATUS_ENABLED = 1

    # states from https://w1.fi/wpa_supplicant/devel/defs_8h.html#a4aeb27c1e4abd046df3064ea9756f0bc
    STATE_DISCONNECTED = "DISCONNECTED"
    STATE_INTERFACE_DISABLED = "INTERFACE_DISABLED"
    STATE_INACTIVE = "INACTIVE"
    STATE_SCANNING = "SCANNING"
    STATE_AUTHENTICATING = "AUTHENTICATING"
    STATE_ASSOCIATING = "ASSOCIATING"
    STATE_ASSOCIATED = "ASSOCIATED"
    STATE_4WAY_HANDSHAKE = "4WAY_HANDSHAKE"
    STATE_GROUP_HANDSHAKE = "GROUP_HANDSHAKE"
    STATE_COMPLETED = "COMPLETED"
    STATE_UNKNOWN = "UNKNOWN"
    STATES = [
        STATE_DISCONNECTED,
        STATE_INTERFACE_DISABLED,
        STATE_INACTIVE,
        STATE_SCANNING,
        STATE_AUTHENTICATING,
        STATE_ASSOCIATING,
        STATE_ASSOCIATED,
        STATE_4WAY_HANDSHAKE,
        STATE_GROUP_HANDSHAKE,
        STATE_COMPLETED,
    ]

    def __init__(self):
        """
        Constructor
        """
        AdvancedConsole.__init__(self)

        # members
        self.logger = logging.getLogger(self.__class__.__name__)
        self.wpacli = "/sbin/wpa_cli"
        self.configured_networks = {}
        self.scanned_networks = {}
        self.__update_configured_networks = True

    def __command(self, command):
        """
        Execute wpa_cli command and parse result to check if command failed or not

        Args:
            command (string): command to execute

        Returns:
            tuple: command result::

                (
                    bool: True if command succeed
                    string: command output
                )

        """
        res = self.command(command)
        self.logger.debug("command result: %s" % res)
        if res["error"] or res["killed"]:
            # command failed
            self.logger.debug("Command failed: %s", command)
            return (False, "")

        # check output
        stdout = "\n".join(res["stdout"][1:])
        if stdout.find("OK") >= 0:
            return (True, "")
        if stdout.find("FAIL") >= 0:
            self.logger.debug("Wpa_cli failed: %s" % res)
            return (False, "")

        self.logger.debug(
            "Wpa_cli succeed with other result: %s (stdout=%s)",res, stdout
        )
        return (True, stdout)

    def get_configured_networks(self):
        """
        Get configured networks. It returns network ids to manipulate it.

        Results:
            dict: configured networks::

                {
                    network (string): {
                        id (int): network id. This id is used to perform other wpacli actions
                        network (string): network name
                        bssid (string): bssid (can be 'any')
                        status (int): network status (STATUS_DISABLED, STATUS_ENABLED, STATUS_CURRENT)
                    },
                    ...
                }

        """
        results = self.find(
            f"{self.wpacli} list_networks",
            r"^(\d)\s+(.*?)\s+(any|.{2}:.{2}:.{2}:.{2}:.{2}:.{2})\s*(?:\[(.*?)\])?$",
        )
        entries = {}
        for _, groups in results:
            # filter None values
            groups = list(filter(None, groups))

            # status
            status = self.STATUS_ENABLED
            if len(groups) == 4:
                value = groups[3].lower()
                if value == "current":
                    status = self.STATUS_CURRENT
                elif value == "disabled":
                    status = self.STATUS_DISABLED

            # new entry
            entries[groups[1]] = {
                "id": groups[0],
                "ssid": groups[1],
                "bssid": groups[2],
                "status": status,
            }

        self.configured_networks = entries
        self.__update_configured_networks = False
        return entries

    def scan_networks(self, interface, duration=3.0):
        """
        Scan networks

        Args:
            interface (string): interface to scan
            duration (float): time to wait before retrieving scan results (default 3 seconds)

        Result:
            bool: True if command succeed (but maybe not connected!)
        """
        # launch scan
        if interface:
            # scan only specified interface
            self.command(f"{self.wpacli} -i {interface} scan")
        else:
            # scan all interfaces
            self.command(f"{self.wpacli} scan")

        # wait few seconds
        time.sleep(duration)

        # parse results
        if interface:
            results = self.find(
                f"{self.wpacli} -i {interface} scan_results",
                r"^(.{2}:.{2}:.{2}:.{2}:.{2}:.{2})\s+(\d+)\s+(.*?)\s+(\[.*\])\s+(.*)$",
            )
        else:
            results = self.find(
                f"{self.wpacli} scan_results",
                r"^(Selected interface) \'(.*?)\'|(.{2}:.{2}:.{2}:.{2}:.{2}:.{2})\s+(\d+)\s+(.*?)\s+(\[.*\])\s+(.*)$",
            )
        entries = {}
        current_interface = interface
        for _, groups in results:
            # filter None values
            groups = list(filter(None, groups))

            if groups[0].startswith("Selected interface"):
                # set current interface
                current_interface = groups[1]

            elif current_interface is not None:
                # update networks on current interface

                # encryption
                flags = groups[3].lower()
                encryption = WpaSupplicantConf.ENCRYPTION_TYPE_UNKNOWN
                if flags.find("wpa2"):
                    encryption = WpaSupplicantConf.ENCRYPTION_TYPE_WPA2
                elif flags.find("wpa"):
                    encryption = WpaSupplicantConf.ENCRYPTION_TYPE_WPA
                elif flags.find("wep"):
                    encryption = WpaSupplicantConf.ENCRYPTION_TYPE_WEP
                else:
                    encryption = WpaSupplicantConf.ENCRYPTION_TYPE_UNSECURED

                # signal level
                signal_level = "?"
                try:
                    signal_level = int(groups[2])
                    signal_level = Tools.dbm_to_percent(signal_level)
                except Exception:
                    pass

                # save entry
                if current_interface not in entries.keys():
                    entries[current_interface] = {}
                entries[current_interface][groups[4]] = {
                    "interface": interface,
                    "network": groups[4],
                    "encryption": encryption,
                    "signallevel": signal_level,
                }

        self.scanned_networks = entries
        return entries

    def enable_network(self, network):
        """
        Enable specified network

        Args:
            network (string): network name

        Returns:
            bool: True if network enabled, False if network is not configured
        """
        if len(self.configured_networks) == 0 or self.__update_configured_networks:
            # no network, update list
            self.get_configured_networks()

        # check if network exists
        if network not in self.configured_networks.keys():
            self.logger.error('Network "%s" is not configured', network)
            return False

        # enable network
        network_id = self.configured_networks[network]["id"]
        result = self.__command(f"{self.wpacli} enable_network {network_id}")[0]

        # save config
        if result:
            self.__command(f"{self.wpacli} save_config")
            self.__update_configured_networks = True

        return result

    def disable_network(self, network):
        """
        Disable specified network

        Args:
            network (string): network name

        Returns:
            bool: True if network disabled, False if network is not configured
        """
        if len(self.configured_networks) == 0 or self.__update_configured_networks:
            # no network, update list
            self.get_configured_networks()

        # check if network exists
        if network not in self.configured_networks.keys():
            self.logger.error('Network "%s" is not configured', network)
            return False

        # disable network
        network_id = self.configured_networks[network]["id"]
        result = self.__command(f"{self.wpacli} disable_network {network_id}")[0]

        # save config
        if result:
            self.__command(f"{self.wpacli} save_config")
            self.__update_configured_networks = True

        return result

    def add_network(self, network, encryption, password, hidden=False):
        """
        Start specified interface

        Note:
            https://www.freebsd.org/cgi/man.cgi?wpa_supplicant.conf%285%29

        Args:
            network (string): network name
            encryption (string): encryption
            password (string): password (if no password set to empty string). If you need
                               encrypted password use WpaSupplicantConf encrypt_password function
            hidden (bool): True if hidden network

        Result:
            bool: True if command succeed (but maybe not connected!)
        """
        # check parameters
        if network is None or len(network) == 0:
            raise MissingParameter("Parameter network is missing")
        if encryption is None:
            raise MissingParameter("Parameter encryption is missing")
        if encryption not in WpaSupplicantConf.ENCRYPTION_TYPES:
            raise InvalidParameter("Parameter encryption is not valid")
        if password is None:
            raise MissingParameter("Parameter password is missing")

        # check if network exists
        if len(self.configured_networks) == 0 or self.__update_configured_networks:
            # no network, update list
            self.get_configured_networks()
        if network in self.configured_networks:
            self.logger.error('Network "%s" is already configured', network)
            return False

        # add network entry
        (_, network_id) = self.__command(f"{self.wpacli} add_network")
        try:
            network_id = int(network_id)
        except Exception:
            self.logger.error('Invalid network id "%s"', network_id)
            return False

        # set network name
        if not self.__command(f"{self.wpacli} set_network {network_id} ssid '\"{network}\"'")[0]:
            self.logger.error("Unable to set network ssid")
            return False

        # set encryption
        command = None
        if encryption in (
            WpaSupplicantConf.ENCRYPTION_TYPE_WPA2,
            WpaSupplicantConf.ENCRYPTION_TYPE_WPA,
            WpaSupplicantConf.ENCRYPTION_TYPE_WEP,
        ):
            command = f"{self.wpacli} set_network {network_id} key_mgmt WPA-PSK WPA-EAP"
        else:
            command = f"{self.wpacli} set_network {network_id} key_mgmt NONE"
        if not self.__command(command)[0]:
            self.logger.error("Unable to set network encryption")
            return False

        # set password
        if len(password) > 0:
            if not self.__command(f"{self.wpacli} set_network {network_id} psk '\"{password}\"'")[0]:
                self.logger.error("Unable to set network password")
                return False

        # set hidden
        if hidden:
            if not self.__command(f"{self.wpacli} set_network {network_id} scan_ssid 1")[0]:
                self.logger.error("Unable to set network hidden flag")
                return False

        return True

    def remove_network(self, network):
        """
        Remove specified network

        Args:
            network (string): network name

        Returns:
            bool: True if network removed
        """
        if len(self.configured_networks) == 0 or self.__update_configured_networks:
            # no network, update list
            self.get_configured_networks()

        # check if network exists
        if network not in self.configured_networks.keys():
            self.logger.error('Network "%s" is not configured', network)
            return False

        # disable network
        network_id = self.configured_networks[network]["id"]
        result = self.__command(f"{self.wpacli} remove_network {network_id}")[0]

        # save config
        if result:
            self.__command(f"{self.wpacli} save_config")
            self.__update_configured_networks = True

        return result

    def select_network(self, network):
        """
        Select specified network. All other networks are automatically disabled by this command

        Args:
            network (string): network name

        Returns:
            bool: True if network selected
        """
        if len(self.configured_networks) == 0 or self.__update_configured_networks:
            # no network, update list
            self.get_configured_networks()

        # check if network exists
        if network not in self.configured_networks.keys():
            self.logger.error('Network "%s" is not configured', network)
            return False

        # disable network
        network_id = self.configured_networks[network]["id"]
        result = self.__command(f"{self.wpacli} select_network {network_id}")[0]

        # save config
        if result:
            self.__command(f"{self.wpacli} save_config")
            self.__update_configured_networks = True

        return result

    def reconfigure_interface(self, interface, pause=5.0):
        """
        Reconfigure specified interface

        Args:
            interface (string): interface name
            pause (float): pause before returning result. The pause helps to avoid empty networks list

        Returns:
            bool: True if reconfigure succeed
        """
        # check params
        if interface is None or len(interface) == 0:
            raise MissingParameter("Parameter interface is missing")

        # reconfigure
        res = self.command(f"{self.wpacli} -i {interface} reconfigure", timeout=10.0)
        if res["error"] or res["killed"]:
            return False

        # pause if requested
        if pause:
            time.sleep(pause)

        return True

    def get_status(self, interface_name):
        """
        Return interface status

        Args:
            interface_name (string): interface name to get status on

        Returns:
            dict: wifi interface status::

            {
                network (string): connected network name
                state (string): state info (see STATE_XXX)
                ipaddress (string): ip address
            )

        """
        results = self.find(
            f"{self.wpacli} -i {interface_name} status",
            r"^(ssid)=(.*)|(wpa_state)=(.*)|(ip_address)=(.*)$",
        )
        network = None
        ip_address = None
        state = self.STATE_UNKNOWN
        for _, groups in results:
            # filter None values
            groups = list(filter(None, groups))

            if groups[0].startswith("ssid"):
                # network
                network = groups[1]
            elif groups[0].startswith("ip_address"):
                # ip
                ip_address = groups[1]
            elif groups[0].startswith("wpa_state"):
                # state
                if groups[1] in self.STATES:
                    state = groups[1]

        return {"network": network, "state": state, "ipaddress": ip_address}
