#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.config import Config
import os
import io
import json
import logging

class CleepWifiConf():
    """
    Helper class to read /boot/cleepwifi.conf
    Config base class is not used here to avoid using cleep_filesystem
    """

    CONF = u'/boot/cleepwifi.conf'

    def __init__(self):
        """
        Constructor
        """

        #members
        self.logger = logging.getLogger(self.__class__.__name__)

    def exists(self):
        """
        Return True if cleepwifi config file exists

        Return:
            bool: True if file exists
        """
        return os.path.exists(self.CONF)

    def get_configuration(self):
        """
        Return cleepwifi configuration

        Return:
            dict: configuration or None if error::
                {
                    network (string)
                    password (string)
                    encryption (wep|wpa|wpa2|unsecured)
                    hidden (bool)
                }
        """
        try:
            #only read content, no need to handle r/o filesystem
            fd = io.open(self.CONF, u'r')
            content = fd.read()
            fd.close()
            return json.loads(content)
        except:
            self.logger.exception(u'Unable to load %s:' % self.CONF)

        return None

    def delete(self, cleep_filesystem):
        """
        Delete wifi config file
        Cleep_filesystem is not passed on constructor because this class is shared with CleepDesktop that only needs
        to generate the file.

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance

        Return:
            bool: True if cleepwifi.conf deleted
        """
        return cleep_filesystem.remove(self.CONF)

            
