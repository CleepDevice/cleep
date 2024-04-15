#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
from cleep.libs.internals.task import Task
from cleep.exception import CommandError

class Driver:
    """
    Base driver class
    """

    # Driver types
    # Audio driver: all hat that deals with audio (sound card, microphones...)
    DRIVER_AUDIO = 'audio'
    # Driver video: sll stuff with video capabilities (camera...)
    DRIVER_VIDEO = 'video'
    # Display driver: all stuff that allows to display infos (screen, digits...)
    DRIVER_DISPLAY = 'display'
    # Electronic driver: all hat with electronical parts (led, sensors...)
    DRIVER_ELECTRONIC = 'electronic'
    # Power driver: hat with power purpose (UPS...)
    DRIVER_POWER = 'power'
    # Positionning driver: hat with positionning capabilities (GPS...)
    DRIVER_POSITIONNING = 'position'
    # Home automation driver: stuff with home automation purpose (protocol dongle, hat...)
    DRIVER_HOMEAUTOMATION = 'homeautomation'

    # PROCESSING STATUS
    PROCESSING_NONE = 0
    PROCESSING_INSTALLING = 1
    PROCESSING_UNINSTALLING = 2

    def __init__(self, driver_type, driver_name):
        """
        Constructor

        Args:
            driver_type (string): driver type. Must be one of available DRIVER_XXX types
            driver_name (string): driver name.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.type = driver_type
        self.name = driver_name
        self._processing = self.PROCESSING_NONE

    def _on_registered(self): # pragma: no cover
        """
        Function triggered when driver is registered and configured
        """
        raise NotImplementedError('Function "_on_registered" must be implemented in "%s"' % self.__class__.__name__)

    def configure(self, params):
        """
        Configure

        Note:
            This function is called by Cleep during driver registration process

        Args:
            params (dict): driver parameters::

                {
                    cleep_filesystem (CleepFilesystem): CleepFilesystem instance
                    task_factory (TaskFactory): TaskFactory instance
                }

        """
        self.cleep_filesystem = params['cleep_filesystem']
        self.task_factory = params['task_factory']

    def install(self, end_callback, params=None, logger=None):
        """
        Install driver

        Args:
            end_callback (function): function called when install complete. Function args: driver_type (string), driver_name (string), success (bool), message (string)
            params (dict): additionnal parameters if necessary
            logger (logging): logging instance. If None driver logger will be provided

        Returns:
            Task: install task instance
        """
        if self._processing!=self.PROCESSING_NONE:
            raise CommandError('Driver is already installing')

        # set processing flag asap
        self._processing = self.PROCESSING_INSTALLING

        def install(callback, params):
            self.logger.trace('Installing driver...')
            message = None
            success = True
            self.cleep_filesystem.enable_write(root=True, boot=True)
            try:
                self._install(params)
            except Exception as e:
                self.logger.exception('Error during driver installation:')
                message = str(e)
                success = False
            finally:
                self.cleep_filesystem.disable_write(root=True, boot=True)
                self._processing = self.PROCESSING_NONE
            callback(self.type, self.name, success, message)

        self.logger.trace('Launch driver install task')
        task = self.task_factory.create_task(None, install, [end_callback, params])
        task.start()
        return task

    def uninstall(self, end_callback, params=None, logger=None):
        """
        Uninstall driver

        Args:
            end_callback (function): function called when install complete. Function args: driver type (string), driver name (string), success (bool), message (string)
            params (dict): additionnal parameters if necessary
            logger (logging): logging instance. If None driver logger will be provided

        Returns:
            Task: install task instance
        """
        if self._processing!=self.PROCESSING_NONE:
            raise CommandError('Driver is already uninstalling')

        # set processing flag asap
        self._processing = self.PROCESSING_UNINSTALLING

        def uninstall(callback, params):
            message = None
            success = True
            self.cleep_filesystem.enable_write(root=True, boot=True)
            try:
                self._uninstall(params)
            except Exception as e:
                self.logger.exception('Error during driver installation:')
                message = str(e)
                success = False
            finally:
                self.cleep_filesystem.disable_write(root=True, boot=True)
                self._processing = self.PROCESSING_NONE
            callback(self.type, self.name, success, message)

        self.logger.trace('Launch driver uninstall task')
        task = self.task_factory.create_task(None, uninstall, [end_callback, params])
        task.start()
        return task

    def processing(self):
        """
        Return processing status

        Returns:
            int: processing status (see Driver.PROCESSING_XXX)
        """
        return self._processing

    def _install(self, params): # pragma: no cover
        """
        Install driver

        Warning:
            Must be implemented

        Args:
            params (dict): optionnal parameters
        """
        raise NotImplementedError('Function "install" must be implemented in "%s"' % self.__class__.__name__)

    def _uninstall(self, params=None): # pragma: no cover
        """
        Uninstall driver. Don't forget to enable writings during driver installation.

        Warning:
            Must be implemented

        Args:
            params (dict): additionnal parameters if necessary
        """
        raise NotImplementedError('Function "uninstall" must be implemented in "%s"' % self.__class__.__name__)

    def is_installed(self): # pragma: no cover
        """
        Is driver installed ?

        Warning:
            Must be implemented

        Returns:
            bool: True if driver is installed
        """
        raise NotImplementedError('Function "is_installed" must be implemented in "%s"' % self.__class__.__name__)

    def require_reboot(self): # pragma: no cover
        """
        Require device reboot after install/uninstall

        Warning:
            Must be implemented

        Returns:
            bool: True if driver install/uninstall requires to reboot device
        """
        raise NotImplementedError('Function "require_reboot" must be implemented in "%s"' % self.__class__.__name__)
        
