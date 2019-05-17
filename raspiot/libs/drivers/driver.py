#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
from raspiot.libs.internals.task import Task

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
        self.logger = logging.getLogger(self.__class__.__name__)
        self.type = driver_type
        self.name = driver_name

    def install(self, end_callback, params=None):
        """
        Install driver

        Args:
            end_callback (function): function called when install complete. Function args: success (bool), message (string)
            params (dict): additionnal parameters if necessary
        """

        def install(callback, params):
            message = None
            success = True
            self.cleep_filesystem.enable_write(root=True, boot=True)
            try:
                self._install(params)
            except Exception as e:
                message = str(e)
                success = False
            finally:
                self.cleep_filesystem.disable_write(root=True, boot=True)
            callback(success, message)

        task = Task(None, install, self.logger, [end_callback, params])
        task.start()

    def _install(self, params):
        """
        Install driver

        Args:
            params (dict): optionnal parameters
        """
        raise NotImplementedError(u'Function "install" must be implemented in "%s"' % self.__class__.__name__)

    def uninstall(self, end_callback, params=None):
        """
        Uninstall driver

        Args:
            end_callback (function): function called when install complete. Function args: success (bool), message (string)
            params (dict): additionnal parameters if necessary
        """

        def uninstall(callback, params):
            message = None
            success = True
            self.cleep_filesystem.enable_write(root=True, boot=True)
            try:
                self._uninstall(params)
            except Exception as e:
                message = str(e)
                success = False
            finally:
                self.cleep_filesystem.disable_write(root=True, boot=True)
            callback(success, message)

        task = Task(None, uninstall, self.logger, [end_callback, params])
        task.start()

    def _uninstall(self, params=None):
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
        

