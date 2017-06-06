#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
from raspiot.libs.config import Config
import unittest
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
        for group, groups in results.iteritems():
            #filter
            if group is None or len(group)==0:
                continue

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
                content += '%s=%s ' % (entry['key'], entry['value'])
            else:
                content += '%s ' % entry['key']

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



class cmdlinetxtTests(unittest.TestCase):
    def setUp(self):
        #fake config file
        fd = open('cmdline.txt', 'w')
        fd.write("""dwc_otg.lpm_enable=0 console=serial0,115200 console=tty1 root=PARTUUID=45ea7472-02 rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait""")
        fd.close()
        
        self.c = CmdlineTxt()
        self.c.CONF = 'cmdline.txt'

    def tearDown(self):
        os.remove('cmdline.txt')

    def test_console(self):
        self.assertTrue(self.c.is_console_enabled())
        self.assertFalse(self.c.enable_console())
        self.assertTrue(self.c.disable_console())
        self.assertFalse(self.c.is_console_enabled())
        self.assertTrue(self.c.enable_console())
        self.assertTrue(self.c.is_console_enabled())




