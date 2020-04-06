#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.exceptions import InvalidParameter, MissingParameter, CommandError
from raspiot.libs.configs.config import Config
import os
import re
import io

class CmdlineTxt(Config):
    """
    Helper class to update and read /boot/cmdline.txt file

    Notes:
        https://www.raspberrypi.org/documentation/configuration/cmdline-txt.md
    """

    CONF = u'/boot/cmdline.txt'

    KEY_CONSOLE = u'console'
    VALUE_CONSOLE = u'serial0,115200'

    def __init__(self, cleep_filesystem):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
        """
        Config.__init__(self, cleep_filesystem, self.CONF, None)

    def __get_entries(self):
        """
        Return all file entries

        Returns:
            list: entry informations (empty if nothing found)::

                {
                    key (string): [
                        value (string),
                        ...
                    ],
                    ...
                }

        """
        entries = []

        results = self.find(u'(.*?)(?:=(.*?))?(?:\s|\Z)')
        for group, groups in results:
            self.logger.trace('group=%s' % group)
            self.logger.trace(groups)

            #add new entry
            key = groups[0]
            value = groups[1] if len(groups)==2 else None

            #if key not in entries.keys():
            #    entries[key] = []
            #entries[key].append(value)
            entries.append((key, value))

        return entries

    def __save_entries(self, entries):
        """
        Save all specified entries

        Args:
            entries (dict): dict as returned with __get_entries
        """
        #prepare content
        content = u''
        #for key, values in entries.items():
        #    for value in values:
        #        if value is None:
        #            content += u'%s ' % key
        #        else:
        #            content += u'%s=%s ' % (key, value)
        for (key, value) in entries:
            if value is None:
                content += u'%s ' % key
            else:
                content += u'%s=%s ' % (key, value)

        #write content
        fd = self._open(self.MODE_WRITE)
        fd.write(content)
        self._close()

    def __key_value_exists(self, key, value, entries):
        """
        Check if specified combo key/value exists in entries

        Returns:
            bool: True if combo exists
        """
        for entry in entries:
            if entry[0]==key and entry[1]==value:
                return True

        return False

    def is_console_enabled(self):
        """
        Return True if console is enabled
        
        Returns:
            bool: True if console enabled
        """
        entries = self.__get_entries()
        #self.logger.trace('console_enabled? %s, %s' % (entries.has_key(self.KEY_CONSOLE), entries[self.KEY_CONSOLE]))
        #return entries.has_key(self.KEY_CONSOLE) and self.VALUE_CONSOLE in entries[self.KEY_CONSOLE]
        return self.__key_value_exists(self.KEY_CONSOLE, self.VALUE_CONSOLE, entries)

    def enable_console(self):
        """
        Enable console
        Add console=serial0,115200 entry

        Returns:
            bool: Return True if serial enabled. False if serial already enabled
        """
        entries = self.__get_entries()
        self.logger.trace('entries: %s' % entries)
        #if not entries.has_key(self.KEY_CONSOLE) or (entries.has_key(self.KEY_CONSOLE) and self.VALUE_CONSOLE not in entries[self.KEY_CONSOLE]):
        if not self.__key_value_exists(self.KEY_CONSOLE, self.VALUE_CONSOLE, entries):
            #add entry
            entries.append((self.KEY_CONSOLE, self.VALUE_CONSOLE))

            #save changes
            self.__save_entries(entries)

            return True

        return False

    def disable_console(self):
        """
        Disable console
        Remove console=serial0,115200 entry

        Returns:
            bool: Return True if serial disabled. False if serial already disabled
        """
        entries = self.__get_entries()
        #if entries.has_key(self.KEY_CONSOLE) and self.VALUE_CONSOLE in entries[self.KEY_CONSOLE]:
        if self.__key_value_exists(self.KEY_CONSOLE, self.VALUE_CONSOLE, entries):
            #remove value from entry values
            for entry in entries:
                if entry[0]==self.KEY_CONSOLE and entry[1]==self.VALUE_CONSOLE:
                    entries.remove(entry)
                    break
            #entries[self.KEY_CONSOLE].remove(self.VALUE_CONSOLE)

            #remove complete key if entry holds not more value
            #if len(entries[self.KEY_CONSOLE])==0:
            #    del entries[self.KEY_CONSOLE]

            #save changes
            self.__save_entries(entries)

            return True

        return False



