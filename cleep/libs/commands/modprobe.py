#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.console import Console
import re
import time
import logging

class Modprobe(Console):
    """
    Modprobe command helper
    """

    def __init__(self):
        """
        Constructor
        """
        Console.__init__(self)

        #members
        self.logger = logging.getLogger(self.__class__.__name__)

    def load_module(self, module):
        """
        Load specified module

        Args:
            module (string): module name

        Returns:
            bool: True if module loaded successfully
        """
        cmd = u'/sbin/modprobe "%s"' % module.replace(u'-', u'_')
        self.logger.trace('Cmd: %s' % cmd)
        resp = self.command(cmd)
        self.logger.trace('Cmd "%s" resp: %s' % (cmd, resp))

        return True if self.get_last_return_code()==0 else False

    def unload_module(self, module):
        """
        Unload specified module

        Args:
            module (string): module name

        Returns:
            bool: True if module unloaded successfully
        """
        cmd = u'/sbin/modprobe --remove "%s"' % module.replace(u'-', u'_')
        resp = self.command(cmd)
        self.logger.trace('Cmd "%s" resp: %s' % (cmd, resp))

        return True if self.get_last_return_code()==0 else False

