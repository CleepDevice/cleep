#!/usr/bin/env python
# -*- coding: utf-8 -*-

from console import Console
import re
import time

class Lsblk():
    """
    """

    CACHE_DURATION = 5.0

    def __init__(self):
        """
        Constructor
        """
        self.console = Console()
        self.timestamp = None
        self.devices = {}
        self.partitions = []

    def __refresh(self):
        """
        Refresh all data
        """
        #check if refresh is needed
        if self.timestamp is not None and time.time()-self.timestamp<=self.CACHE_DURATION:
            return

        res = self.console.command(u'/bin/lsblk --list --bytes --output NAME,MAJ:MIN,TYPE,RM,SIZE,RO,MOUNTPOINT,RA,MODEL')
        if not res[u'error'] and not res[u'killed']:
            self.partitions = []

            #parse data
            matches = re.finditer(r'^(.*?)\s+(\d+):(\d+)\s+(.*?)\s+(\d)\s+(.*?)\s+(\d)\s+(.*?)\s+(\d+)(\s|.*?)$', u'\n'.join(res[u'stdout']), re.UNICODE | re.MULTILINE)
            for matchNum, match in enumerate(matches):
                groups = match.groups()
                if len(groups)==10:
                    #name
                    name = groups[0]
                    
                    #drive properties
                    partition = True
                    model = None
                    if groups[3].find('disk')!=-1:
                        current_drive = name
                        model = groups[9]
                        partition = False
                        total_size = groups[5]
                        try:
                            total_size = int(total_size)
                        except:
                            pass

                    #readonly flag
                    readonly = True
                    if groups[6]=='0':
                        readonly = False

                    #removable flag
                    removable = True
                    if groups[4]=='0':
                        removable = False

                    #mountpoint
                    mountpoint = groups[7]

                    #size and percent
                    size = groups[5]
                    percent = None
                    try:
                        size = int(size)
                        percent = int(float(size)/float(total_size)*100.0)
                    except:
                        pass

                    #fill device
                    device = {
                        u'name': name,
                        u'major': groups[1],
                        u'minor': groups[2],
                        u'size': size,
                        u'totalsize': total_size,
                        u'percent': percent,
                        u'readonly': readonly,
                        u'mountpoint': mountpoint,
                        u'partition': partition,
                        u'removable': removable,
                        u'drivemodel': model
                    }

                    #save device
                    if current_drive not in self.devices:
                        self.devices[current_drive] = {}
                    self.devices[current_drive][name] = device

                    #partition
                    if partition:
                        self.partitions.append(name)

        self.timestamp = time.time()

    def get_devices_infos(self):
        """
        Return all devices

        Return:
            dict: dict of devices
        """
        self.__refresh()
        return self.devices

    def get_drives(self):
        """
        Return only drives names

        Return:
            list: list of drivess names
        """
        self.__refresh()
        return self.devices.keys()

    def get_partitions(self):
        """
        Return only partitions names

        Return:
            list: list of partitions names
        """
        self.__refresh()
        return self.partitions

    def get_device_infos(self, device):
        """
        Return device infos according to device name (sda, sdb1...)

        Args:
            device (string): existing device name

        Return:
            dict: dict of device infos or None if device not found
        """
        self.__refresh()
        for drive in self.devices.keys():
            if device in self.devices[drive]:
                return self.devices[drive][device]

        return None

