#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.console import Console
import re
import time
import logging

class Lsmod(Console):
    """
    Lsmod command helper
    """

    CACHE_DURATION = 2.0

    def __init__(self):
        """
        Constructor
        """
        Console.__init__(self)

        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        self.timestamp = None
        self.modules = []

    def __refresh(self):
        """
        Refresh all data
        """
        #check if refresh is needed
        if self.timestamp is not None and time.time()-self.timestamp<=self.CACHE_DURATION:
            self.logger.debug('Don\'t refresh')
            return

        res = self.command(u'/bin/lsmod | /usr/bin/awk \'NR>1 { print $1}\'')
        modules = []
        if not res[u'error'] and not res[u'killed']:
            for module in res[u'stdout']:
                modules.append(module)

        #save devices
        self.modules = modules

        #update timestamp
        self.timestamp = time.time()

    def get_loaded_modules(self):
        """
        Return all loaded modules

        Return:
            list: list of modules
        """
        self.__refresh()

        return self.modules

    def is_module_loaded(self, module):
        """
        Return True if specified module is loaded
        """
        self.__refresh()

        return module.replace(u'-', u'_') in self.modules

