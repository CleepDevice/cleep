#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
from raspiot.libs.config import Config
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

    def __init__(self):
        """
        Constructor
        """
        Config.__init__(self, self.CONF, None)

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

        results = self.search(u'(.*?)(?:=(.*?))?(?:\s|\Z)')
        for group, groups in results:
            #add new entry
            entry = {
                u'group': group,
                u'key': groups[0],
                u'value': groups[1]
            }
            entries[groups[0]] = entry

        return entries

    def __save_entries(self, entries):
        """
        Save all specified entries

        Args:
            entries (dict): dict as returned with __get_entries
        """
        #prepare content
        content = u''
        for key, entry in entries.iteritems():
            if entry['value'] is not None:
                content += u'%s=%s ' % (entry[u'key'], entry[u'value'])
            else:
                content += u'%s ' % entry[u'key']

        #write content
        fd = self._open(self.MODE_WRITE)
        fd.write(content)
        self._close()

    def is_console_enabled(self):
        """
        Return True if console is enabled
        
        Returns:
            bool: True if console enabled
        """
        entries = self.__get_entries()
        return entries.has_key(self.KEY_CONSOLE)

    def enable_console(self):
        """
        Enable console
        Add console=serial0,115200 entry

        Returns:
            bool: Return True if serial enabled. False if serial already enabled
        """
        entries = self.__get_entries()
        if not entries.has_key(self.KEY_CONSOLE):
            #add entry
            entries[self.KEY_CONSOLE] = {
                u'group': u'%s=%s' % (self.KEY_CONSOLE, self.VALUE_CONSOLE),
                u'key': self.KEY_CONSOLE,
                u'value': self.VALUE_CONSOLE
            }

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
        if entries.has_key(self.KEY_CONSOLE):
            #delete entry
            del entries[self.KEY_CONSOLE]
            #save changes
            self.__save_entries(entries)

            return True

        return False



