#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from cleep.libs.configs.config import Config
from cleep.libs.commands.blkid import Blkid
from cleep.libs.internals.console import Console
from cleep.exception import MissingParameter


class Fstab(Config):
    """
    Handles /etc/fstab file
    """

    CONF = "/etc/fstab"

    def __init__(self, cleep_filesystem, backup=True):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            backup (bool): True to enable backup
        """
        Config.__init__(self, cleep_filesystem, self.CONF, None, backup)
        self.blkid = Blkid()
        self.console = Console()

    def get_all_devices(self):
        """
        Return all devices as returned by command blkid

        Returns:
            dict: list of devices::

                {
                    device (string): device name {
                        device (string): device name,
                        uuid (string): device uuid
                    },
                    ...
                }

        """
        devices = {}

        for device, uuid in self.blkid.get_devices().items():
            entry = {"device": device, "uuid": uuid}
            devices[device] = entry

        return devices

    def get_mountpoints(self):
        """
        Return all mountpoints as presented in /etc/fstab file

        Returns:
            dict: list of mountpoints::

                {
                    mountpoint (string): mountpoint name {
                        group (string): found group,
                        local (bool): local or remote mountpoint,
                        device (string): device,
                        uuid (string): device uuid,
                        mountpoint (string): mountpoint name,
                        mounttype (string): mount type,
                        options (string): mountpoint options
                    },
                    ...
                }

        """
        mountpoints = {}
        pattern_type = r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:)(.*?)$|^(UUID)(=)(.*?)$|^\/(dev)(\/)(.*?)$|^(.*?)(:)(.*?)$"

        results = self.find(
            r"^(?!#)(.+?)\s+(.+?)\s+(.+?)\s+(.+?)\s+(.+?)\s+(.+?)\s*$",
            re.MULTILINE | re.UNICODE,
        )
        self.logger.trace("results=%s", results)

        for group, groups in results:
            # remove none values
            groups = list(filter(None, groups))

            if len(groups) == 6:
                # get type of mount point
                sub_results = self.find_in_string(pattern_type, groups[0], re.UNICODE)
                for sub_group, sub_groups in sub_results:
                    # remove none values
                    sub_groups = list(filter(None, sub_groups))

                    if len(sub_groups) == 3:
                        if sub_groups[0].startswith("UUID") and sub_groups[1] == "=":
                            # uuid
                            uuid = sub_groups[2]
                            device = self.blkid.get_device(uuid)
                            mountpoint = groups[1]
                            mounttype = groups[2]
                            options = groups[3]
                            local = True
                        elif sub_groups[0].startswith("dev") and sub_groups[1] == "/":
                            # device
                            device = sub_group
                            uuid = self.blkid.get_device_by_uuid(device)
                            mountpoint = groups[1]
                            mounttype = groups[2]
                            options = groups[3]
                            local = True
                        elif (
                            sub_groups[0][1].isdigit() and sub_groups[1] == ":"
                        ) or sub_groups[1] == ":":
                            # ip or hostname
                            device = sub_group
                            uuid = None
                            mountpoint = groups[1]
                            mounttype = groups[2]
                            options = groups[3]
                            local = False
                        else:  # pragma: no cover
                            # unknown entry
                            continue

                        # add entry
                        mountpoints[mountpoint] = {
                            "group": group,
                            "local": local,
                            "device": device,
                            "uuid": uuid,
                            "mountpoint": mountpoint,
                            "mounttype": mounttype,
                            "options": options,
                        }

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
        # check params
        if mountpoint is None or len(mountpoint) == 0:
            raise MissingParameter("Mountpoint parameter is missing")
        if device is None or len(device) == 0:
            raise MissingParameter("Device parameter is missing")
        if mounttype is None or len(mounttype) == 0:
            raise MissingParameter("Mounttype parameter is missing")
        if options is None or len(options) == 0:
            raise MissingParameter("Options parameter is missing")

        # check if mountpoint not already exists
        mountpoints = self.get_mountpoints()
        self.logger.trace("mountpoints=%s", mountpoints.keys())
        if mountpoint in mountpoints:
            return False

        line = f"\n{device}\t{mountpoint}\t{mounttype}\t{options}\t0\t0\n"
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
        # check params
        if mountpoint is None or len(mountpoint) == 0:
            raise MissingParameter('Parameter "mountpoint" is missing')

        # check if mountpoint exists
        mountpoints = self.get_mountpoints()
        if mountpoint not in mountpoints:
            return False

        # delete mountpoint
        return self.remove(mountpoints[mountpoint]["group"])

    def reload_fstab(self):
        """
        Reload fstab file (mount -a)

        Returns:
            bool: True if command successful, False otherwise
        """
        res = self.console.command("/bin/mount -a")
        return res["returncode"] == 0
