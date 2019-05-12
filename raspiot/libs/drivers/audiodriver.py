#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
from .driver import Driver

class AudioDriver(Driver):
    """
    Audio driver base class
    """

    def __init__(self, cleep_filesystem, driver_name):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            driver_name (string): driver name
        """
        Driver.__init__(self, cleep_filesystem, Driver.DRIVER_AUDIO, driver_name)

    def get_device_infos(self):
        """
        Returns infos about device associated to driver

        Returns:
            dict: device infos::

                {
                    cardname (string): handled card name
                    cardid (int): card id
                    deviceid (int): device id
                }

        """
        raise NotImplementedError(u'Function "get_infos" must be implemented in "%s"' % self.__class__.__name__)

    def enable(self, params=None):
        """ 
        Enable driver

        Args:
            params (dict): additionnal parameters if necessary
        """
        raise NotImplementedError(u'Function "enable" must be implemented in "%s"' % self.__class__.__name__)

    def disable(self, params=None):
        """ 
        Disable driver

        Args:
            params (dict): additionnal parameters if necessary
        """
        raise NotImplementedError(u'Function "disable" must be implemented in "%s"' % self.__class__.__name__)

    def is_enabled(self):
        """ 
        Is driver enabled

        Returns:
            bool: True if driver enabled
        """
        raise NotImplementedError(u'Function "is_enabled" must be implemented in "%s"' % self.__class__.__name__)

    def get_volumes(self):
        """ 
        Get volumes

        Returns:
            dict: volumes level::

                {
                    playback (float): playback volume
                    capture (float): capture volume
                }

        """
        raise NotImplementedError(u'Function "get_volumes" must be implemented in "%s"' % self.__class__.__name__)

    def set_volumes(self, playback=None, capture=None):
        """ 
        Set volumes

        Args:
            playback (float): playback volume (None to disable update)
            capture (float): capture volume (None to disable update)
        """
        raise NotImplementedError(u'Function "set_volumes" must be implemented in "%s"' % self.__class__.__name__)

