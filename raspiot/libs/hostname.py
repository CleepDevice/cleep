#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import MissingParameter
import io

class Hostname():
    """
    Helper class to update and read /etc/hostname file
    """

    CONF = u'/etc/hostname'

    def __init__(self, backup=True):
        """
        Constructor
        """
        self.hostname = None

    def set_hostname(self, hostname):
        """
        Set raspi hostname

        Args:
            hostname (string): hostname

        Return:
            bool: True if hostname saved successfully, False otherwise
        """
        if hostname is None or len(hostname)==0:
            raise MissingParameter('Hostname parameter is missing')

        self.hostname = hostname

        try:
            with io.open(self.CONF, u'w') as fd:
                fd.write(u'%s' % self.hostname)
        except:
            return False

        return True

    def get_hostname(self):
        """
        Return raspi hostname

        Returns:
            string: raspi hostname
        """
        if self.hostname is None:
            with io.open(self.CONF, u'r') as fd:
                content = fd.readlines()

            if len(content)>0:
                self.hostname = content[0].strip()
        
        return self.hostname

