#!/usr/bin/env python
# -*- coding: utf-8 -*-

from console import Console
import logging
import os

class ReadWrite():
    """
    Read/write library allows user to toggle read/write mode on cleep protected iso
    """

    STATUS_WRITE = 0
    STATUS_READ = 1

    PARTITION_ROOT = u'/'
    PARTITION_BOOT = u'/boot'

    def __init__(self):
        """
        Constructor
        """
        self.console = Console()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        self.status = None

    def __refresh(self, partition):
        """
        Refresh data

        Args:
            partition (string): partition to work on
        """
        partition_mod = partition.replace('/', '\/')
        res = self.console.command(u'/bin/mount | sed -n -e "s/^.* on %s .*(\(r[w|o]\).*/\1/p"' % partition_mod)

        #check errors
        if res[u'error'] or res[u'killed']:
            self.logger.error('Error when getting rw/ro flag: %s' % res)
        if len(res[u'stdout'])==0:
            self.logger.error('Error when getting rw/ro flag: %s' % res)

        #parse result
        line = res[u'stdout'][0].strip()
        if line=='rw':
            self.status[parition] = self.STATUS_WRITE
        elif line=='ro':
            self.status[partition] = self.STATUS_READ
        else:
            self.logger.error(u'Unable to get parition "%s" status: %s' % (partition, res[u'stdout']))
            raise Exception(u'Unable to get partition "%s" status' % partition)

    def __is_cleep_iso(self):
        """
        Detect if raspiot is running on cleep iso

        Return:
            bool: True if it's cleep iso
        """
        if os.path.exists('/tmp/raspiot'):
            return True

        return False

    def get_status(self):
        """
        Return current filesystem status

        Return:
            dict: partition status (please check STATUS_UNKNOWN that appears when problem occurs)::
                {
                    boot (int): STATUS_READ|STATUS_WRITE
                    root (int): STATUS_READ|STATUS_WRITE
                }
        """
        self.__refresh(self.PARTITION_BOOT)
        self.__refresh(self.PARTITION_ROOT)

        return self.status

    def __enable_write(self, partition):
        """
        Enable filesystem writing

        Args:
            partition (string): partition to work on

        Return:
            bool: True if write enabled, False otherwise
        """
        if not self.__is_cleep_iso():
            return False

        #execute command
        res = self.console(u'mount -o remount,rw %s' % partition)

        #check errors
        if res[u'error'] or res[u'killed']:
            self.logger.error('Error when turning on writing mode: %s' % res)
            
        #refresh status
        self.__refresh(partition)

        return self.status[partition] is self.STATUS_WRITE

    def __disable_write(self, partition):
        """
        Disable filesystem writings

        Args:
            partition (string): partition to work on

        Return:
            bool: True if read enabled, False otherwise
        """
        if not self.__is_cleep_iso():
            return False

        #execute command
        res = self.console(u'mount -o remount,ro %s' % partition)

        #check errors
        if res[u'error'] or res[u'killed']:
            self.logger.error('Error when turning on writing mode: %s' % res)
            
        #refresh status
        self.__refresh(partition)

        return self.status[partition] is self.STATUS_READ

    def enable_write_on_boot(self):
        """
        Enable filesystem writings on boot partition

        Return:
            bool: True if write enabled, False otherwise
        """
        return self.__enable_write(self.PARTITION_BOOT)

    def disable_write_on_boot(self):
        """
        Disable filesystem writings on boot partition

        Return:
            bool: True if write disabled, False otherwise
        """
        return self.__disable_write(self.PARTITION_BOOT)

    def enable_write_on_root(self):
        """
        Enable filesystem writings on root partition

        Return:
            bool: True if write enabled, False otherwise
        """
        return self.__enable_write(self.PARTITION_ROOT)

    def disable_write_on_root(self):
        """
        Disable filesystem writings on root partition

        Return:
            bool: True if write disabled, False otherwise
        """
        return self.__disable_write(self.PARTITION_ROOT)

