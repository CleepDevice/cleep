#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import time
import logging
from cleep.libs.internals.console import Console


class Udevadm(Console):
    """
    udevadm is used to determine device type.
    Device type can be ATA, USB, SDCARD or MMC
    """

    CACHE_DURATION = 10.0

    TYPE_UNKNOWN = 0
    TYPE_ATA = 1
    TYPE_USB = 2
    TYPE_SDCARD = 3
    TYPE_MMC = 4

    def __init__(self):
        """
        Constructor
        """
        Console.__init__(self)

        # members
        self.timestamps = {}
        self.devices = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def __refresh(self, device):
        """
        Refresh data filling devices class member

        Args:
            device (string): device name
        """
        # check if refresh is needed
        if (
            device in self.timestamps
            and time.time() - self.timestamps[device] <= self.CACHE_DURATION
        ):
            self.logger.trace("Use cached data")
            return

        # add new device entry if necessary
        if device not in self.devices:
            self.devices[device] = self.TYPE_UNKNOWN

        res = self.command(f'/bin/udevadm info --query=property --name="{device}"')
        self.logger.debug('udevadm res=%s', res)
        if not res["error"] and not res["killed"]:
            # parse data
            matches = re.finditer(
                r"^(?:(ID_DRIVE_FLASH_SD)=(\d)|(ID_DRIVE_MEDIA_FLASH_SD)=(\d)|(ID_BUS)=(.*?)|(ID_USB_DRIVER)=(.*?)|(ID_ATA)=(\d)|(ID_PATH_TAG)=(.*?))$",
                "\n".join(res["stdout"]),
                re.UNICODE | re.MULTILINE,
            )
            id_path_tag_with_mmc = False
            for _, match in enumerate(matches):
                # get values and filter None values
                groups = match.groups()
                groups = list(filter(None, groups))

                if len(groups) == 2:
                    if groups[0] == "ID_BUS" and groups[1] == "usb":
                        # usb stuff (usb stick, usb card reader...)
                        self.devices[device] = self.TYPE_USB
                        break
                    if groups[0] == "ID_DRIVE_FLASH_SD" and groups[1] == "1":
                        # sdcard
                        self.devices[device] = self.TYPE_SDCARD
                        break
                    if groups[0] == "ID_DRIVE_MEDIA_FLASH_SD" and groups[1] == "1":
                        # sdcard
                        self.devices[device] = self.TYPE_SDCARD
                        break
                    if groups[0] == "ID_BUS" and groups[1] == "ata":
                        # ata device (SATA, PATA)
                        self.devices[device] = self.TYPE_ATA
                        break
                    if groups[0] == "ID_ATA":
                        # ata device (SATA, PATA)
                        self.devices[device] = self.TYPE_ATA
                        break
                    if groups[0] == "ID_PATH_TAG" and groups[1].find("mmc") != -1:
                        # mmc device
                        id_path_tag_with_mmc = True

                    # unknown device type
                    self.devices[device] = self.TYPE_UNKNOWN

            if id_path_tag_with_mmc and self.devices[device] == self.TYPE_UNKNOWN:
                self.devices[device] = self.TYPE_MMC

        self.timestamps[device] = time.time()

    def get_device_type(self, device):
        """
        Return specified device type

        Args:
            device (string): device name (for example mmcblk0)

        Returns:
            int: device type (ATA=1, USB=2, SDCARD=3, MMC=4, UNKNOWN=0, see class constants)
        """
        self.__refresh(device)
        return self.devices[device]
