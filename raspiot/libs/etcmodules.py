#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
from raspiot.libs.config import Config
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

    def __init__(self, backup=True):
        """
        Constructor
        """
        Config.__init__(self, self.CONF, u'#', backup)

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

        results = self.search(u'^(?!#)(.*?)$', re.UNICODE | re.MULTILINE)
        for group, groups in results:
            #add new entry
            entry = {
                u'group': group,
                u'module': groups[0]
            }
            entries[groups[0]] = entry

        return entries

    def __is_module_enabled(self, module):
        """
        Return True if module is enabled

        Args:
            module (string): module name
        
        Returns:
            bool: True if module is enabled
        """
        entries = self.__get_entries()
        return entries.has_key(module)

    def __enable_module(self, module):
        """
        Enable module

        Args:
            module (string): module to enable

        Returns:
            bool: Return True if module enabled. False if module already enabled
        """
        entries = self.__get_entries()
        if not entries.has_key(module):
            return self.add([u'%s' % module])

        #module already enabled
        return True

    def __disable_module(self, module):
        """
        Disable module

        Args:
            module (string): module to disable

        Returns:
            bool: Return True if module disabled
        """
        entries = self.__get_entries()
        if entries.has_key(module):
            return self.remove([u'%s' % module])

        #module already disabled
        return True

    def is_onewire_enabled(self):
        """
        Return True if onewire modules are enabled

        Returns:
            bool: True if onewire enabled
        """
        return self.__is_module_enabled(self.MODULE_ONEWIRETHERM) and self.__is_module_enabled(self.MODULE_ONEWIREGPIO)

    def enable_onewire(self):
        """
        Enable onewire modules

        Returns:
            bool: True if onewire has been enabled
        """
        return self.__enable_module(self.MODULE_ONEWIRETHERM) and self.__enable_module(self.MODULE_ONEWIREGPIO)

    def disable_onewire(self):
        """
        Disable onewire modules

        Returns:
            bool: True if onewire has been disabled
        """
        return self.__disable_module(self.MODULE_ONEWIRETHERM) and self.__disable_module(self.MODULE_ONEWIREGPIO)


