#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.exception import InvalidParameter, MissingParameter, CommandError
from cleep.libs.configs.config import Config
import os
import re
import io

class EtcModules(Config):
    """
    Helper class to update and read /etc/modules file
    """

    CONF = '/etc/modules'

    MODULE_ONEWIRETHERM = 'w1-therm'
    MODULE_ONEWIREGPIO = 'w1-gpio'
    MODULE_SOUND_BCM2835 = 'snd-bcm2835'

    def __init__(self, cleep_filesystem, backup=True):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
        """
        Config.__init__(self, cleep_filesystem, self.CONF, '#', backup)

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

        results = self.find('^(?!#)(.*?)$', re.UNICODE | re.MULTILINE)
        for group, groups in results:
            #add new entry
            entry = {
                'group': group,
                'module': groups[0]
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
        return module_name.replace('_', '-') in self.__get_entries()

    def __enable_module(self, module_name):
        """
        Enable module

        Args:
            module_name (string): module to enable

        Returns:
            bool: Return True if module enabled. False if module already enabled
        """
        out = True

        entries = self.__get_entries()
        if module_name not in entries:
            out = self.add_lines(['%s' % module_name])

        return out

    def __disable_module(self, module_name):
        """
        Disable module

        Args:
            module_name (string): module to disable

        Returns:
            bool: Return True if module disabled
        """
        out = True

        entries = self.__get_entries()
        if module_name in entries:
            out = self.remove_lines(['%s' % module_name])

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
        return self.__is_module_enabled(self.MODULE_SOUND_BCM2835)

    def enable_embedded_sound(self):
        """
        DEPRECATED: use enable_module instead
        Enable embedded sound module

        Returns:
            bool: True if embedded sound module has been enabled
        """
        return self.__enable_module(self.MODULE_SOUND_BCM2835)

    def disable_embedded_sound(self):
        """
        DEPRECATED: use disable_module instead
        Disable embedded sound module

        Returns:
            bool: True if embedded sound module has been disabled
        """
        return self.__disable_module(self.MODULE_SOUND_BCM2835)

    def enable_module(self, module_name):
        """
        Enable specified module adding it into /etc/modules file and probing it
        No error are returned in case of invalid module name

        Args:
            module_name (string): module name

        Returns:
            bool: True if module is enabled
        """
        if module_name is None or len(module_name)==0:
            raise MissingParameter('Parameter "module_name" is missing')
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
        if module_name is None or len(module_name)==0:
            raise MissingParameter('Parameter "module_name" is missing')

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
        if module_name is None or len(module_name)==0:
            raise MissingParameter('Parameter "module_name" is missing')

        return self.__is_module_enabled(module_name)

