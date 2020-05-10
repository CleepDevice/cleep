#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.exception import MissingParameter
from raspiot.libs.configs.config import Config

class Hostname(Config):
    """
    Helper class to update and read /etc/hostname file
    """

    CONF = u'/etc/hostname'

    def __init__(self, cleep_filesystem, backup=True):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            backup (bool): True to enable backup
        """
        Config.__init__(self, cleep_filesystem, self.CONF, backup)

        #members
        self.hostname = None

    def set_hostname(self, hostname):
        """
        Set raspi hostname

        Args:
            hostname (string): hostname

        Returns:
            bool: True if hostname saved successfully, False otherwise
        """
        if hostname is None or len(hostname)==0:
            raise MissingParameter('Parameter "hostname" is missing')

        self.hostname = hostname
        result = False

        fd = None
        try:
            fd = self.cleep_filesystem.open(self.CONF, u'w')
            fd.write(u'%s' % self.hostname)
            result = True
        except:
            self.hostname = None
            self.logger.exception(u'Unable to write hostname file:')
        finally:
            self.cleep_filesystem.close(fd)

        return result

    def get_hostname(self):
        """
        Return raspi hostname

        Returns:
            string: raspi hostname
        """
        if self.hostname is None:
            fd = self.cleep_filesystem.open(self.CONF, u'r')
            content = fd.readlines()
            self.cleep_filesystem.close(fd)

            if len(content)>0:
                self.hostname = content[0].strip()
        
        return self.hostname

