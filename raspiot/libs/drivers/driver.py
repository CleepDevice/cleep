#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging

class Driver():
    """
    Base driver class
    """

    #driver types
    DRIVER_AUDIO = u'audio'

    def __init__(self, cleep_filesystem, driver_type, driver_name):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            driver_type (string): driver type. Must be one of available DRIVER_XXX types
            driver_name (string): driver name.
        """
        self.cleep_filesystem = cleep_filesystem
        self.type = driver_type
        self.name = driver_name

    def install(self, params=None):
        """
        Install driver. Don't forget to enable writings during driver installation.

        Args:
            params (dict): additionnal parameters if necessary
        """
        raise NotImplementedError(u'Function "install" must be implemented in "%s"' % self.__class__.__name__)

    def uninstall(self, params=None):
        """
        Uninstall driver. Don't forget to enable writings during driver installation.

        Args:
            params (dict): additionnal parameters if necessary
        """
        raise NotImplementedError(u'Function "uninstall" must be implemented in "%s"' % self.__class__.__name__)

    def is_installed(self):
        """
        Is driver installed ?

        Returns:
            bool: True if driver installed
        """
        raise NotImplementedError(u'Function "is_installed" must be implemented in "%s"' % self.__class__.__name__)
        

