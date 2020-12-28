#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import logging
import json
from cleep.libs.internals.console import Console

class Rfkill(Console):
    """
    Command /usr/sbin/rfkill helper
    """

    TYPE_WIFI = 'wlan'
    TYPE_BLUETOOTH = 'bluetooth'

    FLAG_BLOCKED = 'blocked'
    FLAG_UNBLOCKED = 'unblocked'

    COMMAND_BLOCK = 'block'
    COMMAND_UNBLOCK = 'unblock'

    def __init__(self):
        """
        Constructor
        """
        Console.__init__(self)

        # members
        self._list_command = '/usr/sbin/rfkill --json --output DEVICE,ID,TYPE,TYPE-DESC,SOFT,HARD list all'
        self._block_command = '/usr/sbin/rfkill %(command)s %(ident)s'
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)

    def __refresh(self):
        """
        Refresh all data
        """
        resp = self.command(self._list_command)
        self.logger.debug(resp)

        if resp['returncode'] !=0:
            self.logger.error('Rfkill command failed %s' % resp)
            return None

        rfkill = json.loads(''.join(resp['stdout']))
        return rfkill['']

    def get_wifi_infos(self):
        """
        Returns wifi infos if any

        Returns:
            dict: wifi infos or None if no wireless adapter::

            {
                device (string): device name
                id (int): rfkill device id
                desc (string): device description
                blocked (bool): True if device is blocked (hard or soft)
            }

        """
        devices = self.__refresh()
        if not devices:
            return None

        info = next((device for device in devices if device['type'] == self.TYPE_WIFI), None)
        if not info:
            return None

        return {
            'device': info['device'],
            'id': info['id'],
            'desc': info['type-desc'],
            'blocked': info['soft'] == self.FLAG_BLOCKED or info['hard'] == self.FLAG_BLOCKED
        }

    def get_bluetooth_infos(self):
        """
        Returns bluetooth infos if any

        Returns:
            dict: bluetooth infos or None if no bluetooth adapter::

            {
                device (string): device name
                id (int): rfkill device id
                desc (string): device description
                blocked (bool): True if device is blocked (hard or soft)
            }

        """
        devices = self.__refresh()
        if not devices:
            return None

        info = next((device for device in devices if device['type'] == self.TYPE_BLUETOOTH), None)
        if not info:
            return None

        return {
            'device': info['device'],
            'id': info['id'],
            'desc': info['type-desc'],
            'blocked': info['soft'] == self.FLAG_BLOCKED or info['hard'] == self.FLAG_BLOCKED
        }

    def __block_device(self, device_id, block):
        """
        Block/unblock specified device

        Args:
            device_id (int): device id. If None specified, block/unblock all devices
            block (bool): True to block device, False to unblock
        """
        ident = 'all' if device_id is None else device_id
        command = self.COMMAND_BLOCK if block else self.COMMAND_UNBLOCK
        resp = self.command(self._block_command % {'command': command, 'ident': ident})

        return resp['returncode'] == 0

    def block_device(self, device_id):
        """
        Block specified device

        Args:
            device_id (int): device id as returned by get_xxx_infos function

        Returns:
            bool: True if command succeed
        """
        return self.__block_device(device_id, True)

    def unblock_device(self, device_id):
        """
        Unblock specified device

        Args:
            device_id (int): device id as returned by get_xxx_infos function

        Returns:
            bool: True if command succeed
        """
        return self.__block_device(device_id, False)

