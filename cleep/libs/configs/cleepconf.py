# !/usr/bin/env python
#  -*- coding: utf-8 -*-

import ast
import os
import time
import logging
from passlib.hash import sha256_crypt
from configparser import ConfigParser
from cleep.common import CORE_MODULES


class CleepConf:
    """
    Helper class to update and read values from /etc/cleep/cleep.conf file
    """

    CONF = "/etc/cleep/cleep.conf"

    DEFAULT_CONFIG = {
        "general": {"modules": [], "updated": []},
        "rpc": {
            "rpc_host": "0.0.0.0",
            "rpc_port": 80,
            "rpc_cert": "",
            "rpc_key": "",
        },
        "debug": {"trace_enabled": False, "debug_core": False, "debug_modules": []},
        "auth": {"accounts": {}, "enabled": False},
    }

    def __init__(self, cleep_filesystem):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
        """
        # members
        self.cleep_filesystem = cleep_filesystem
        self.logger = logging.getLogger(self.__class__.__name__)
        self.__conf = None

    def __open(self):
        """
        Open config file

        Returns:
            ConfigParser: ConfigParser instance
        """
        self.__conf = ConfigParser()

        if not os.path.exists(self.CONF):
            # create empty file
            fdesc = self.cleep_filesystem.open(self.CONF, "w")
            fdesc.write("")
            self.cleep_filesystem.close(fdesc)
            time.sleep(0.10)

        # load conf content
        fdesc = self.cleep_filesystem.open(self.CONF, "r")
        self.__conf.read_file(fdesc)
        self.cleep_filesystem.close(fdesc)

        return self.__conf

    def __close(self, write=False):
        """
        Close everything and write new content if forced
        """
        if self.__conf and write:
            # workaround for unicode writing http://bugs.python.org/msg187829
            fdesc = self.cleep_filesystem.open(self.CONF, "w")
            self.__conf.write(fdesc)
            self.cleep_filesystem.close(fdesc)

    def check(self):
        """
        Check configuration file content, adding missing section or options

        Returns:
            bool: True if updated
        """
        try:
            config = self.__open()
            updated = False

            # merge with default config
            for (section, section_keys) in self.DEFAULT_CONFIG.items():
                # fix missing section
                if not config.has_section(section):
                    config.add_section(section)
                    updated = True

                # fix missing section keys
                for (key, value) in section_keys.items():
                    if not config.has_option(section, key):
                        config.set(section, key, str(value))
                        updated = True
            return updated
        finally:
            self.__close(updated)

    def as_dict(self):
        """
        Return all config content as dict

        Returns:
            dict: config content
        """
        try:
            conf = self.__open()
            config = {}

            for section in conf.sections():
                config[section] = {}
                for option, val in conf.items(section):
                    try:
                        config[section][option] = ast.literal_eval(val)
                    except Exception:
                        # unable to eval option, consider it as a string
                        config[section][option] = f"{val}"

            return config
        finally:
            self.__close()

    def install_module(self, module):
        """
        Add module to list of modules to load at startup

        Args:
            module (string): module name to load

        Returns:
            bool: True if module installed
        """
        try:
            conf = self.__open()
            self.logger.trace("Conf=%s", conf)

            # check if module isn't already installed
            modules = ast.literal_eval(conf.get("general", "modules"))
            if module in modules:
                return True

            # install module
            modules.append(module)
            conf.set("general", "modules", str(modules))

            return True
        finally:
            self.__close(True)

    def uninstall_module(self, module):
        """
        Remove module from list of loaded modules

        Args:
            module (string): module name to uninstall

        Returns:
            bool: True if module uninstalled
        """
        try:
            conf = self.__open()

            # check if module is installed
            modules = ast.literal_eval(conf.get("general", "modules"))
            if module not in modules:
                self.logger.warning(
                    'Trying to uninstall not installed module "%s"', module
                )
                return False

            # uninstall module
            modules.remove(module)
            conf.set("general", "modules", str(modules))

            return True
        finally:
            self.__close(True)

    def update_module(self, module):
        """
        Add module name in updated config list item

        Args:
            module (string): module name to set as updated

        Returns:
            bool: True if operation succeed
        """
        try:
            conf = self.__open()

            # check if module installed
            modules = ast.literal_eval(conf.get("general", "modules"))
            if module not in modules:
                self.logger.warning(
                    'Trying to update not installed module "%s"', module
                )
                return False

            # check if module not already updated
            updated = ast.literal_eval(conf.get("general", "updated"))
            if module in updated:
                return True

            # update module
            updated.append(module)
            conf.set("general", "updated", str(updated))

            return True
        finally:
            self.__close(True)

    def clear_updated_modules(self):
        """
        Erase updated module list from config
        """
        try:
            conf = self.__open()

            # clear list content
            updated = ast.literal_eval(conf.get("general", "updated"))
            updated[:] = []
            conf.set("general", "updated", str(updated))
        finally:
            self.__close(True)

    def is_module_installed(self, module):
        """
        Return True if specified module is installed

        Args:
            module (string): module name to check

        Returns:
            bool: True if module is installed
        """
        try:
            conf = self.__open()
            modules = ast.literal_eval(conf.get("general", "modules"))

            return module in modules
        finally:
            self.__close()

    def is_module_updated(self, module):
        """
        Return True if specified module is installed

        Args:
            module (string): module name to check

        Returns:
            bool: True if module is installed
        """
        try:
            conf = self.__open()
            modules = ast.literal_eval(conf.get("general", "updated"))

            return module in modules
        finally:
            self.__close()

    def enable_trace(self):
        """
        Enable trace logging mode
        """
        try:
            conf = self.__open()
            conf.set("debug", "trace_enabled", str(True))
        finally:
            self.__close(True)

    def disable_trace(self):
        """
        Disable trace logging mode
        """
        try:
            conf = self.__open()
            conf.set("debug", "trace_enabled", str(False))
        finally:
            self.__close(True)

    def is_trace_enabled(self):
        """
        Return trace status

        Returns:
            bool: True if trace enabled
        """
        try:
            conf = self.__open()

            return ast.literal_eval(conf.get("debug", "trace_enabled"))
        finally:
            self.__close()

    def enable_core_debug(self):
        """
        Enable core debug
        """
        try:
            conf = self.__open()
            conf.set("debug", "debug_core", str(True))
        finally:
            self.__close(True)

    def disable_core_debug(self):
        """
        Disable core debug
        """
        try:
            conf = self.__open()
            conf.set("debug", "debug_core", str(False))
        finally:
            self.__close(True)

    def is_core_debugged(self):
        """
        Return core debug status

        Returns:
            bool: True if core debug enabled
        """
        try:
            conf = self.__open()

            return ast.literal_eval(conf.get("debug", "debug_core"))
        finally:
            self.__close()

    def enable_module_debug(self, module):
        """
        Enable module debug

        Args:
            module (string): module name to debug

        Returns:
            bool: True if module debug enabled
        """
        try:
            conf = self.__open()

            # check if module is installed
            modules = ast.literal_eval(conf.get("general", "modules"))
            if module not in modules and module not in CORE_MODULES:
                self.logger.warning(
                    'Trying to enable debug for not installed module "%s"', module
                )
                return False

            # check if module is in debug list
            modules = ast.literal_eval(conf.get("debug", "debug_modules"))
            if module in modules:
                # module already in debug list
                return True

            # add module to debug list
            modules.append(module)
            conf.set("debug", "debug_modules", str(modules))

            return True
        finally:
            self.__close(True)

    def disable_module_debug(self, module):
        """
        Disable module debug

        Args:
            module (string): module name to disable

        Returns:
            bool: True if module debug disabled
        """
        try:
            conf = self.__open()

            # check if module is in debug list
            modules = ast.literal_eval(conf.get("debug", "debug_modules"))
            if module not in modules:
                # module not in debug list
                return False

            # remove module from debug list
            modules.remove(module)
            conf.set("debug", "debug_modules", str(modules))

            return True
        finally:
            self.__close(True)

    def is_module_debugged(self, module):
        """
        Return True if module debug is enabled

        Args:
            module (string): module name to check

        Returns:
            bool: True if module debug is enabled, False if disabled
        """
        try:
            conf = self.__open()
            modules = ast.literal_eval(conf.get("debug", "debug_modules"))

            return module in modules
        finally:
            self.__close()

    def set_rpc_config(self, host, port):
        """
        Set rpc configuration

        Args:
            host (string): rpc server host value
            port (int): rpc server port value

        Returns:
            bool: True if rpc config saved
        """
        try:
            conf = self.__open()
            conf.set("rpc", "rpc_host", host)
            conf.set("rpc", "rpc_port", str(port))

            return True
        finally:
            self.__close(True)

    def get_rpc_config(self):
        """
        Get rpc configuration

        Returns:
            tuple: rpc host and port values::

                (
                    host (string),
                    port (int)
                )

        """
        try:
            conf = self.__open()
            rpc = (conf.get("rpc", "rpc_host"), conf.getint("rpc", "rpc_port"))

            return rpc
        finally:
            self.__close()

    def set_rpc_security(self, cert, key):
        """
        Set rpc security configuration

        Args:
            cert (string): certificate file path
            key (string): key file path

        Returns:
            bool: True if values saved successfully
        """
        try:
            conf = self.__open()
            conf.set("rpc", "rpc_cert", cert)
            conf.set("rpc", "rpc_key", key)

            return True
        finally:
            self.__close(True)

    def get_rpc_security(self):
        """
        Get rpc security configuration

        Returns:
            tuple: cert and key values::

                (
                    cert,
                    key
                )

        """
        try:
            conf = self.__open()
            rpc = (conf.get("rpc", "rpc_cert"), conf.get("rpc", "rpc_key"))
            return rpc
        finally:
            self.__close()

    def get_auth_accounts(self):
        """
        Return auth existing accounts with encrypted password

        Returns:
            dict: if with_passwords options enabled, return dict with account-password::

                {
                    account (str): encrypted password (str),
                    ...
                }

        """
        try:
            conf = self.__open()

            return ast.literal_eval(conf.get("auth", "accounts"))
        finally:
            self.__close()

    def get_auth(self):
        """
        Return auth config at once

        Returns:
            dict: auth config::

            {
                enabled (bool): True if auth enabled, False otherwise
                accounts (list): List of accounts names
            }

        """
        try:
            conf = self.__open()
            accounts = ast.literal_eval(conf.get("auth", "accounts"))
            enabled = ast.literal_eval(conf.get("auth", "enabled"))

            return {"enabled": enabled, "accounts": list(accounts.keys())}
        finally:
            self.__close()

    def add_auth_account(self, account, password):
        """
        Add auth account

        Args:
            account (str): account name
            password (str): account password
        """
        try:
            conf = self.__open()
            accounts = ast.literal_eval(conf.get("auth", "accounts"))

            if account in accounts:
                raise Exception("Account already exists")

            accounts[account] = sha256_crypt.hash(password)
            conf.set("auth", "accounts", str(accounts))
        finally:
            self.__close(True)

    def delete_auth_account(self, account):
        """
        Delete auth account

        Args:
            account (str): account name
        """
        try:
            conf = self.__open()
            accounts = ast.literal_eval(conf.get("auth", "accounts"))

            if account not in accounts:
                raise Exception("Account does not exist")

            del accounts[account]
            conf.set("auth", "accounts", str(accounts))

            # disable auth if no more account
            if len(accounts) == 0:
                conf.set("auth", "enabled", str(False))
        finally:
            self.__close(True)

    def enable_auth(self, enable=True):
        """
        Enable or disable authentication

        Args:
            enable (bool): True to enable auth (default) False to disable auth
        """
        try:
            conf = self.__open()
            conf.set("auth", "enabled", str(enable))
        finally:
            self.__close(True)

    def is_auth_enabled(self):
        """
        Return if auth is enabled

        Returns:
            bool: True if auth enabled, False otherwise
        """
        try:
            conf = self.__open()
            enabled = ast.literal_eval(conf.get("auth", "enabled"))
            return enabled
        finally:
            self.__close()
