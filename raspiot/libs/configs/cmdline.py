#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.console import Console
from raspiot.libs.commands.blkid import Blkid
from raspiot.libs.commands.lsblk import Lsblk
import re
import time

class Cmdline(Console):
    """
    Helper class for /proc/cmdline file reading (only!)
    """

    CACHE_DURATION = 3600.0

    def __init__(self):
        """
        Constructor
        """
        Console.__init__(self)

        #members
        self.blkid = Blkid()
        self.lsblk = Lsblk()
        self.timestamp = None
        self.root_drive = None
        self.root_partition = None

    def __refresh(self):
        """
        Refresh data
        """
        #check if refresh is needed
        if self.timestamp is not None and time.time()-self.timestamp<=self.CACHE_DURATION:
            return

        res = self.command(u'/bin/cat /proc/cmdline')
        if not res[u'error'] and not res[u'killed']:
            #parse data
            matches = re.finditer(r'root=(.*?)\s', u'\n'.join(res[u'stdout']), re.UNICODE | re.MULTILINE)
            for matchNum, match in enumerate(matches):
                groups = match.groups()
                if len(groups)==1:
                    self.logger.trace('Groups: %s' % groups)
                    if groups[0].startswith(u'UUID='):
                        #get device from uuid
                        uuid = groups[0].replace(u'UUID=', u'')
                        device = self.blkid.get_device_by_uuid(uuid)
                        self.logger.trace('device=%s' % device)
                        root_device = device[u'device']
                    elif groups[0].startswith(u'PARTUUID='):
                        #get device from uuid
                        partuuid = groups[0].replace(u'PARTUUID=', u'')
                        self.logger.trace('partuuid=%s' % partuuid)
                        device = self.blkid.get_device_by_partuuid(partuuid)
                        self.logger.trace('device=%s' % device)
                        root_device = device[u'device']
                    else:
                        #get device from path
                        uuid = groups[0]
                        device = self.blkid.get_device_by_uuid(uuid)
                        self.logger.trace('device=%s' % device)
                        root_device = device[u'device']

                    #get file system infos
                    drives = self.lsblk.get_drives()

                    #save data
                    self.root_drive = root_device.replace(u'/dev/', u'')
                    self.root_partition = None
                    for drive, partition in drives.items():
                        if self.root_drive.find(drive)!=-1:
                            self.root_partition = partition
                            break

        self.timestamp = time.time()

    def get_root_drive(self):
        """
        Return root drive

        Return:
            string: root drive
        """
        self.__refresh()
        return self.root_drive

    def get_root_partition(self):
        """
        Return root partition

        Return:
            string: root partition
        """
        self.__refresh()
        return self.root_partition

