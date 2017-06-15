#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.config import Config
from console import Console
from raspiot.utils import MissingParameter, InvalidParameter
import re
import time

class Blkid():

    CACHE_DURATION = 5.0

    def __init__(self):
        self.console = Console()
        self.timestamp = None
        self.__devices = {}
        self.__uuids = {}

    def __refresh(self):
        #check if refresh is needed
        if self.timestamp is not None and time.time()-self.timestamp<=self.CACHE_DURATION:
            return

        res = self.console.command(u'/sbin/blkid')
        if not res[u'error'] and not res[u'killed']:
            #parse data
            matches = re.finditer(r'^(\/dev\/.*?):.*UUID=\"(.*?)\"\s+.*$', u'\n'.join(res[u'stdout']), re.UNICODE | re.MULTILINE)
            for matchNum, match in enumerate(matches):
                groups = match.groups()
                if len(groups)==2:
                    self.__devices[groups[0]] = groups[1]
                    self.__uuids[groups[1]] = groups[0]

        self.timestamp = time.time()

    def get_devices(self):
        self.__refresh()

        return self.__devices

    def get_device(self, uuid):
        self.__refresh()

        if self.__uuids.has_key(uuid):
            return self.__uuids[uuid]

        return None

    def get_uuid(self, device):
        self.__refresh()

        if self.__devices.has_key(device):
            return self.__devices[device]

        return None


class Fstab(Config):
    """
    Handles /etc/fstab file
    """

    CONF = u'/etc/fstab'

    def __init__(self, backup=True):
        """
        Constructor
        """
        Config.__init__(self, self.CONF, None, backup)
        self.blkid = Blkid()

    #def get_uuid_by_device(self, device):
    #    """
    #    Return uuid corresponding to device

    #    Args:
    #        device (string): device as presented in fstab

    #    Returns:
    #        string: uuid
    #        None: if nothing found
    #    """
    #    if device is None or len(device)==0:
    #        raise MissingParameter('Device parameter is missing')

    #    #get blkid data
    #    if self.blkid_cache.need_update():
    #        res = self.console.command(u'/sbin/blkid | grep "%s"' % device)
    #        if res[u'error'] or res[u'killed']:
    #            return None

    #        self.blkid_cache.set_lines(res[u'stdout'])

    #        items = res[u'stdout'][0].split()
    #        for item in items:
    #            if item.lower().startswith(u'uuid='):
    #                return item[5:].replace('"', '').strip()

    #    return None

    #def get_device_by_uuid(self, uuid):
    #    """
    #    Return device corresponding to uuid

    #    Args:
    #        uuid (string): device uuid

    #    Returns:
    #        string: device
    #        None: if nothing found
    #    """
    #    if uuid is None or len(uuid)==0:
    #        raise MissingParameter('Uuid parameter is missing')

    #    res = self.console.command(u'/sbin/blkid | grep "%s"' % uuid)
    #    print res
    #    if res[u'error'] or res[u'killed']:
    #        return None
    #    else:
    #        items = res[u'stdout'].split()
    #        return items[0].replace(':', '').strip()

    #    return None

    def get_all_devices(self):
        """
        Return all devices as returned by command blkid

        Returns:
            dict: list of devices
                {
                    'device': {
                        device: '',
                        uuid: ''
                    },
                    ...
                }
        """
        devices = {}

        for device, uuid in self.blkid.get_devices().iteritems():
            entry = {
                u'device': device,
                u'uuid': uuid
            }
            devices[device] = entry

        return devices

    def get_mountpoints(self):
        """
        Return all mountpoints as presented in /etc/fstab file

        Returns:
            dict: list of mountpoints
                {
                    'mountpoint': {
                        device: '',
                        uuid: '',
                        mountpoint: '',
                        mounttype: '',
                        options: ''
                    },
                    ...
                }
        """
        mountpoints = {}
        pattern_type = r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:)(.*?)$|^(UUID)(=)(.*?)$|^\/(dev)(\/)(.*?)$|^(.*?)(:)(.*?)$'

        results = self.find(r'^(?!#)(.+?)\s+(.+?)\s+(.+?)\s+(.+?)\s+(.+?)\s+(.+?)\s*$', re.MULTILINE | re.UNICODE)
        for group, groups in results:
            #remove none values
            groups = filter(None, groups)

            if len(groups)==6:
                #get type of mount point
                sub_results = self.find_in_string(pattern_type, groups[0], re.UNICODE)
                for sub_group, sub_groups in sub_results:
                    #remove none values
                    sub_groups = filter(None, sub_groups)
                    
                    if len(sub_groups)==3:
                        if sub_groups[0].startswith(u'UUID') and sub_groups[1]=='=':
                            #uuid
                            uuid = sub_groups[2]
                            device = self.blkid.get_device(uuid)
                            mountpoint = groups[1]
                            mounttype = groups[2]
                            options = groups[3]
                            local = True
                        elif sub_groups[0].startswith(u'dev') and sub_groups[1]=='/':
                            #device
                            device = sub_group
                            uuid = self.blkid.get_uuid(device)
                            mountpoint = groups[1]
                            mounttype = groups[2]
                            options = groups[3]
                            local = True
                        elif (sub_groups[0][1].isdigit() and sub_groups[1]==':') or sub_groups[1]==':':
                            #ip or hostname
                            device = sub_group
                            uuid = None
                            mountpoint = groups[1]
                            mounttype = groups[2]
                            options = groups[3]
                            local = False
                        else:
                            #unknown entry
                            continue

                        #add entry
                        mountpoints[mountpoint] = {
                            u'group': group,
                            u'local': local,
                            u'device': device,
                            u'uuid': uuid,
                            u'mountpoint': mountpoint,
                            u'mounttype': mounttype,
                            u'options': options
                        }
                    else:
                        #invalid type, drop line
                        continue
                
            else:
                #invalid line, drop result
                continue

        return mountpoints

    def add_mountpoint(self, device, mountpoint, mounttype, options):
        """
        Add specified mount point to /etc/fstab file

        Args:
            device (string): device path
            mountpoint (string): mountpoint
            mounttype (string): type of mountpoint (ext4, ext3...)
            options (string): specific options for mountpoint
                              
        Returns:
            bool: True if mountpoint added succesfully, False otherwise

        Raises:
            MissingParameter
        """
        #check params
        if mountpoint is None or len(mountpoint)==0:
            raise MissingParameter(u'Mountpoint parameter is missing')
        if device is None or len(device)==0:
            raise MissingParameter(u'Device parameter is missing')
        if mounttype is None or len(mounttype)==0:
            raise MissingParameter(u'Mounttype parameter is missing')
        if options is None or len(options)==0:
            raise MissingParameter(u'Options parameter is missing')

        #check if mountpoint not already exists
        mountpoints = self.get_mountpoints()
        if mountpoints.has_key(mountpoint):
            return False

        line = u'\n%s\t%s\t%s\t%s\t0\t0\n' % (device, mountpoint, mounttype, options)
        return self.add(line)

    def delete_mountpoint(self, mountpoint):
        """
        Delete specified mount point from /etc/fstab file
        
        Args:
            mountpoint (string): mountpoint to delete
        
        Returns:
            bool: True if removed, False otherwise

        Raises:
            MissingParameter
        """
        #check params
        if mountpoint is None or len(mountpoint)==0:
            raise MissingParameter(u'Mountpoint parameter is missing')

        #check if mountpoint exists
        mountpoints = self.get_mountpoints()
        if not mountpoints.has_key(mountpoint):
            return False

        #delete mountpoint
        return self.remove(mountpoints[mountpoint][u'group'])

    def reload_fstab(self):
        """
        Reload fstab file (mount -a)
        
        Returns:
            bool: True if command successful, False otherwise
        """
        res = self.console.command(u'/bin/mount -a')
        if res[u'error'] or res[u'killed']:
            return False

        else:
            return True


