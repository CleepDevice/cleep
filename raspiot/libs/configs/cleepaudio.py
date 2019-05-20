#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
from raspiot.libs.configs.config import Config
import os
import re
import io

class CleepAudio(Config):
    """
    Helper class to update and read /etc/modprobe.d/cleep-audio.conf file
    """

    CONF = u'/etc/modprobe.d/cleep-audio.conf'

    def __init__(self, cleep_filesystem, backup=False):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
        """
        Config.__init__(self, cleep_filesystem, self.CONF, u'#', backup)

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
        entries = []

        results = self.find(u'^blacklist (.*?)$', re.UNICODE | re.MULTILINE)
        for group, groups in results:
            entries.append(groups[0])
        self.logger.trace(u'Entries: %s' % entries)

        return entries

    def is_module_blacklisted(self, module_name):
        """
        Return True if module is blacklisted

        Args:
            module_name (string): module name
        
        Returns:
            bool: True if module is blacklisted
        """
        return module_name.replace(u'_', u'-') in self.__get_entries()

    def blacklist_module(self, module_name):
        """
        Blacklist module

        Args:
            module_name (string): module to blacklist

        Returns:
            bool: Return True if module blacklisted
        """
        out = True

        module_name = module_name.replace(u'_', u'-')
        entries = self.__get_entries()
        if module_name not in entries:
            out = self.add_lines([u'blacklist %s' % module_name])

        return out

    def unblacklist_module(self, module_name):
        """
        Unblacklist module

        Args:
            module_name (string): module to unblacklist

        Returns:
            bool: Return True if module unblacklisted
        """
        out = True

        module_name = module_name.replace(u'_', u'-')
        entries = self.__get_entries()
        if module_name in entries:
            out = self.remove_lines([u'blacklist %s' % module_name])

        return out

