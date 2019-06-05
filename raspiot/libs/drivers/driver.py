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
    DRIVER_GPIO = u'gpio'

    #PROCESSING STATUS
    PROCESSING_NONE = 0
    PROCESSING_INSTALLING = 1
    PROCESSING_UNINSTALLING = 2

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
        self.logger.setLevel(logging.DEBUG)
        self.type = driver_type
        self.name = driver_name
        self._processing = self.PROCESSING_NONE

    def install(self, end_callback, params=None, logger=None):
        """
        Install driver

        Args:
            end_callback (function): function called when install complete. Function args: driver_type (string), driver_name (string), success (bool), message (string)
            params (dict): additionnal parameters if necessary
            logger (logging): logging instance. If None driver logger will be provided
        """
        if self._processing!=self.PROCESSING_NONE:
            raise CommandError(u'Driver is already processing')

        def install(callback, params):
            message = None
            success = True
            self.cleep_filesystem.enable_write(root=True, boot=True)
            self._processing = self.PROCESSING_INSTALLING
            try:
                self._install(params)
            except Exception as e:
                self.logger.exception(u'Error during driver installation:')
                message = str(e)
                success = False
            finally:
                self.cleep_filesystem.disable_write(root=True, boot=True)
                self._processing = self.PROCESSING_NONE
            callback(self.type, self.name, success, message)

        task = Task(None, install, logger if logger else self.logger, [end_callback, params])
        task.start()

    def _install(self, params):
        """
        Install driver

        Args:
            params (dict): optionnal parameters
        """
        raise NotImplementedError(u'Function "install" must be implemented in "%s"' % self.__class__.__name__)

    def uninstall(self, end_callback, params=None, logger=None):
        """
        Uninstall driver

        Args:
            end_callback (function): function called when install complete. Function args: driver type (string), driver name (string), success (bool), message (string)
            params (dict): additionnal parameters if necessary
            logger (logging): logging instance. If None driver logger will be provided
        """
        if self._processing!=self.PROCESSING_NONE:
            raise CommandError(u'Driver is already processing')

        def uninstall(callback, params):
            message = None
            success = True
            self.cleep_filesystem.enable_write(root=True, boot=True)
            self._processing = self.PROCESSING_UNINSTALLING
            try:
                self._uninstall(params)
            except Exception as e:
                self.logger.exception(u'Error during driver installation:')
                message = str(e)
                success = False
            finally:
                self.cleep_filesystem.disable_write(root=True, boot=True)
                self._processing = self.PROCESSING_NONE
            callback(self.type, self.name, success, message)

        task = Task(None, uninstall, logger if logger else self.logger, [end_callback, params])
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
        
    def processing(self):
        """
        Return processing status

        Returns:
            int: processing status (see Driver.PROCESSING_XXX)
        """
        return self._processing

