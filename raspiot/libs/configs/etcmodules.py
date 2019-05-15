#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
from raspiot.libs.configs.config import Config
from raspiot.libs.internals.console import Console
import os
import re
import io

class EtcModules(Config):
    """
    Helper class to update and read /etc/modules file
    """

    CONF = u'/etc/modules'

    MODULE_ONEWIRETHERM = u'w1-therm'
    MODULE_ONEWIREGPIO = u'w1-gpio'
    MODULE_SOUND_BCM2835 = u'snd-bcm2835'

    def __init__(self, cleep_filesystem, backup=True):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
        """
        Config.__init__(self, cleep_filesystem, self.CONF, u'#', backup)
        self.console = Console()

    def __get_entries(self):
        """
        Return all file entries

        Returns:
            list: entry informations (empty if nothing found)::
                {
                    <found value for key>: {
                       group (string): full found string (usefull to replace)
                       key (string): <specified key>,
                       value (string): <found value for key>,
                    },
                    ...
                }
        """
        entries = {}

        results = self.find(u'^(?!#)(.*?)$', re.UNICODE | re.MULTILINE)
        for group, groups in results:
            #add new entry
            entry = {
                u'group': group,
                u'module': groups[0]
            }
            entries[groups[0]] = entry

        return entries

    def __is_module_enabled(self, module_name):
        """
        Return True if module is enabled in /etc/modules.
        It do not check if module is loaded! For that use Lsmod lib

        Args:
            module_name (string): module name
        
        Returns:
            bool: True if module is enabled
        """
        return module_name.replace(u'_', u'-') in self.__get_entries()

    def __enable_module(self, module_name):
        """
        Enable module

        Args:
            module_name (string): module to enable

        Returns:
            bool: Return True if module enabled. False if module already enabled
        """
        out = False

        entries = self.__get_entries()
        if not entries.has_key(module_name):
            out = self.add_lines([u'%s' % module_name])

        #modprobe module
        cmd = u'/sbin/modprobe -q "%s"' % module_name
        self.console.command(cmd)

        return out

    def __disable_module(self, module_name):
        """
        Disable module

        Args:
            module_name (string): module to disable

        Returns:
            bool: Return True if module disabled
        """
        out = False

        entries = self.__get_entries()
        if entries.has_key(module_name):
            out = self.remove_lines([u'%s' % module_name])

        #modprobe module
        cmd = u'/sbin/modprobe -q -r "%s"' % module_name
        self.console.command(cmd)

        return out

    def is_onewire_enabled(self):
        """
        DEPRECATED: use is_module_enabled instead
        Return True if onewire modules are enabled

        Returns:
            bool: True if onewire enabled
        """
        return self.__is_module_enabled(self.MODULE_ONEWIRETHERM)

    def enable_onewire(self):
        """
        DEPRECATED: use enable_module instead
        Enable onewire modules

        Returns:
            bool: True if onewire has been enabled
        """
        return self.__enable_module(self.MODULE_ONEWIRETHERM)

    def disable_onewire(self):
        """
        DEPRECATED: use disable_module instead
        Disable onewire modules

        Returns:
            bool: True if onewire has been disabled
        """
        return self.__disable_module(self.MODULE_ONEWIRETHERM)

    def is_embedded_sound_enabled(self):
        """
        DEPRECATED: use is_module_enabled instead
        Return True if embedded sound module is enabled

        Returns:
            bool: True if embedded sound module is enabled
        """
        return self.__is_module_enabled(self.MODULE_BCM2835)

    def enable_embedded_sound(self):
        """
        DEPRECATED: use enable_module instead
        Enable embedded sound module

        Returns:
            bool: True if embedded sound module has been enabled
        """
        return self.__enable_module(self.MODULE_BCM2835)

    def disable_embedded_sound(self):
        """
        DEPRECATED: use disable_module instead
        Disable embedded sound module

        Returns:
            bool: True if embedded sound module has been disabled
        """
        return self.__disable_module(self.MODULE_BCM2835)

    def enable_module(self, module_name):
        """
        Enable specified module adding it into /etc/modules file and probing it
        No error are returned in case of invalid module name

        Args:
            module_name (string): module name

        Returns:
            bool: True if module is enabled
        """
        return self.__enable_module(module_name)

    def disable_module(self, module_name):
        """
        Disable specified module adding it into /etc/modules file and probing it
        No error are returned in case of invalid module name

        Args:
            module_name (string): module name

        Returns:
            bool: True if module is disabled
        """
        return self.__disable_module(module_name)

    def is_module_enabled(self, module_name):
        """
        Return True if specified module is enabled
        No error are returned in case of invalid module name

        Args:
            module_name (string): module name

        Returns:
            bool: True if module is loaded
        """
        return self.__is_module_enabled(module_name)

