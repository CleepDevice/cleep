#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter
import unittest
import os

class WpaSupplicantConf():
    """
    Helper class to update and read /etc/wpa_supplicant/wpa_supplicant.conf file
    """

    CONF = '/etc/wpa_supplicant/wpa_supplicant.conf'

    def __open(self):
        """
        Open config file
        @return ConfigParser instance (ConfigParser)
        @raise Exception if file doesn't exist
        """
        pass

    def __close(self, write=False):
        """
        Close everything and write new content if specified
        @param write: write new content if set to True
        """
        pass




class WpaSupplicantConfTests(unittest.TestCase):
    def setUp(self):
        #fake conf file
        pass

