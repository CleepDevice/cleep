#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
from raspiot.libs.config import Config
import os
import re
import io

class ConfigTxt(Config):
    """
    Helper class to update and read /boot/config.txt file

    Notes:
        * https://www.raspberrypi.org/documentation/configuration/config-txt/README.md
        * http://elinux.org/RPiconfig
        * http://raspi.tv/how-to-enable-spi-on-the-raspberry-pi
    """

    CONF = u'/boot/config.txt'

    KEY_DTOVERLAY = u'dtoverlay'
    KEY_DTPARAM = u'dtparam'

    DTOVERLAY_ONEWIRE = u'w1-gpio'
    DTOVERLAY_LIRC = u'lirc-rpi'
    DTPARAM_SPI = u'spi'
    DTPARAM_SPI_VALUE = u'on'
    DTPARAM_I2C = u'i2c_arm'
    DTPARAM_I2C_VALUE = u'on'

    def __init__(self, backup=True):
        """
        Constructor
        """
        Config.__init__(self, self.CONF, u'#', backup)

    def __get_entries(self, key):
        """
        Return file entries according to specified key

        Returns:
            list: entry informations (empty if nothing found)::
                {
                    <found value for key>: {
                       key (string): <specified key>,
                       value (string): <found value for key>,
                       disabled (bool): entry is disabled or not
                    },
                    ...
                }
        """
        entries = {}

        results = self.search(u'(#?)%s=(.*?)(\s|\Z)' % key)
        for group, groups in results:
            disabled = False
            if groups[0]==u'#':
                disabled = True

            entry = {
                u'group': group,
                u'key': key,
                u'value': groups[1],
                u'disabled': disabled
            }
            entries[groups[1]] = entry

        return entries

    def __is_dtoverlay_enabled(self, dtoverlay):
        """
        Is DTOVERLAY is enabled

        Returns:
            bool: True if specified dtoverlay enabled
        """
        entries = self.__get_entries(self.KEY_DTOVERLAY)

        if entries.has_key(dtoverlay):
            return not entries[dtoverlay][u'disabled']
        else:
            return False

    def __enable_dtoverlay(self, dtoverlay, disable=False):
        """
        Enable/disable specified dtoverlay

        Args:
            dtoverlay (string): existing dtoverlay
            disable (bool): True to disable instead of enable
        """
        entries = self.__get_entries(self.KEY_DTOVERLAY)

        if entries.has_key(dtoverlay):
            if entries[dtoverlay][u'disabled']:
                #dtoverlay is disabled
                if disable:
                    #dtoverlay already disabled
                    return True
                else:
                    #uncomment line
                    return self.uncomment(entries[dtoverlay]['group'])

            else:
                #dtoverlay not disabled
                if disable:
                    #disable dtoverlay
                    return self.comment(entries[dtoverlay]['group'])
                else:
                    #entry already enabled
                    return True

        else:
            #entry does not exist yet
            if disable:
                #do nothing
                return True
            else:
                #add new dtoverlay entry
                return self.add([u'%s=%s' % (self.KEY_DTOVERLAY, dtoverlay)])

        return False

    def is_onewire_enabled(self):
        """
        Return True if onewire is enabled

        Returns:
            bool: True if onewire enabled
        """
        return self.__is_dtoverlay_enabled(self.DTOVERLAY_ONEWIRE)

    def enable_onewire(self):
        """
        Enable onewire support
        """
        return self.__enable_dtoverlay(self.DTOVERLAY_ONEWIRE)

    def disable_onewire(self):
        """
        Disable onewire support
        """
        return self.__enable_dtoverlay(self.DTOVERLAY_ONEWIRE, True)

    def is_lirc_enabled(self):
        """
        Return True if LIRC is enabled

        Returns:
            bool: True if LIRC enabled
        """
        return self.__is_dtoverlay_enabled(self.DTOVERLAY_LIRC)

    def enable_lirc(self):
        """
        Enable LIRC support
        """
        return self.__enable_dtoverlay(self.DTOVERLAY_LIRC)

    def disable_lirc(self):
        """
        Disable LIRC support
        """
        return self.__enable_dtoverlay(self.DTOVERLAY_LIRC, True)

    def __is_dtparam_enabled(self, dtparam, dtvalue):
        """
        Is DTPARAM is enabled

        Returns:
            bool: True if specified dtparam enabled
        """
        entries = self.__get_entries(self.KEY_DTPARAM)
        
        if dtvalue is not None:
            key = u'%s=%s' % (dtparam, dtvalue)
        else:
            key = u'%s' % dtparam

        if entries.has_key(key):
            return not entries[key][u'disabled']
        else:
            return False

    def __enable_dtparam(self, dtparam, dtvalue, disable=False):
        """
        Enable/disable specified dtparam

        Args:
            dtparam (string): existing dtparam
            disable (bool): True to disable instead of enable
        """
        entries = self.__get_entries(self.KEY_DTPARAM)

        if dtvalue is not None:
            key = u'%s=%s' % (dtparam, dtvalue)
        else:
            key = u'%s' % dtparam

        if entries.has_key(key):
            if entries[key][u'disabled']:
                #dtparam is disabled
                if disable:
                    #dtparam already disabled
                    return True
                else:
                    #uncomment line
                    return self.uncomment(entries[key]['group'])

            else:
                #dtparam not disabled
                if disable:
                    #disable dtparam
                    return self.comment(entries[key]['group'])
                else:
                    #entry already enabled
                    return True

        else:
            #entry does not exist yet
            if disable:
                #do nothing
                return True
            else:
                #add new dtparam entry
                return self.add([u'%s=%s' % (self.KEY_DTPARAM, key)])

        return False

    def is_spi_enabled(self):
        """
        Return True if SPI is enabled

        Returns:
            bool: True if SPI enabled
        """
        return self.__is_dtparam_enabled(self.DTPARAM_SPI, self.DTPARAM_SPI_VALUE)

    def enable_spi(self):
        """
        Enable SPI support
        """
        return self.__enable_dtparam(self.DTPARAM_SPI, self.DTPARAM_SPI_VALUE)

    def disable_spi(self):
        """
        Disable SPI support
        """
        return self.__enable_dtparam(self.DTPARAM_SPI, self.DTPARAM_SPI_VALUE, True)

    def is_i2c_enabled(self):
        """
        Return True if i2c is enabled

        Returns:
            bool: True if i2c enabled
        """
        return self.__is_dtparam_enabled(self.DTPARAM_I2C, self.DTPARAM_I2C_VALUE)

    def enable_i2c(self):
        """
        Enable i2c support
        """
        return self.__enable_dtparam(self.DTPARAM_I2C, self.DTPARAM_I2C_VALUE)

    def disable_i2c(self):
        """
        Disable i2c support
        """
        return self.__enable_dtparam(self.DTPARAM_I2C, self.DTPARAM_I2C_VALUE, True)




