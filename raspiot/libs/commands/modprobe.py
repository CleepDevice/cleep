#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.console import Console
import re
import time
import logging

class Modprob(Console):
    """
    Modprob command helper
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

        return module in self.modules

