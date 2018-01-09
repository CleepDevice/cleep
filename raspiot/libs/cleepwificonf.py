#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.config import Config
import os
import json
import logging

class CleepWifiConf(Config):
    """
    Helper class to read /boot/cleepwifi.conf
    """

    CONF = u'/boot/cleepwifi.conf'

    def __init__(self):
        """
        Constructor
        """
        Config.__init__(self, self.CONF, u'', False)

        #members
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_configuration(self):
        """
        Return cleepwifi configuration

        Return:
            dict: configuration or None if error::
                {
                    network (string)
                    password (string)
                    encryption (wep|wpa|wpa2|unsecured)
                }
        """
        try:
            content = self.get_content()[0]
            return json.loads(content)
        except:
            self.logger.exception(u'Unable to load %s:' % self.CONF)

        return None

            
