#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

try:
    from cleep.libs.internals.console import AdvancedConsole
except:  # pragma no cover
    from console import AdvancedConsole
import time
import os


class Iw(AdvancedConsole):
    """
    Command /sbin/iw helper.
    Return wireless network interface infos.
    """

    CACHE_DURATION = 5.0

    def __init__(self):
        """
        Constructor
        """
        AdvancedConsole.__init__(self)

        # members
        self._command = "/sbin/iw dev"
        self.logger = logging.getLogger(self.__class__.__name__)
        self.adapters = {}
        self.timestamp = None

    def is_installed(self):
        """
        Return True if iw command is installed

        Returns:
            bool: True is installed
        """
        return os.path.exists("/sbin/iw")

    def __refresh(self):
        """
        Refresh all data
        """
        # check if refresh is needed
        if (
            self.timestamp is not None
            and time.time() - self.timestamp <= self.CACHE_DURATION
        ):  # pragma no cover
            self.logger.trace("Use cached data")
            return

        results = self.find(self._command, r"Interface\s(.*?)\s|ssid\s(.*?)\s")
        self.logger.trace("results=%s", results)
        if len(results) == 0:  # pragma no cover: unable to test if no interface
            self.adapters = {}
            return

        entries = {}
        current_entry = None
        for group, groups in results:
            # filter non values
            groups = list(filter(None, groups))

            if group.startswith("ssid") and current_entry is not None:
                # pylint: disable=E1137
                current_entry["network"] = groups[0]

            elif group.startswith("Interface"):
                current_entry = {"interface": groups[0], "network": None}
                entries[groups[0]] = current_entry

            elif group.startswith("ssid") and current_entry is not None:
                # pylint: disable=E1137
                current_entry["network"] = groups[0]

        # save adapters
        self.adapters = entries

        # update timestamp
        self.timestamp = time.time()

    def get_adapters(self):
        """
        Return all adapters with associated interface

        Returns:
            dict: list of adapters and connected network::

                {
                    adapter (string): {
                        interface (string): associated interface name
                        network (string): connected network
                    },
                    ...
                }

        """
        self.__refresh()

        return self.adapters
