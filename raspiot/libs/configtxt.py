#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter, CommandError
from raspiot.libs.config import Config
import unittest
import os
import re
import io

class ConfigTxt(Config):
    """
    Helper class to update and read /boot/config.txt file

    Notes:
        https://www.raspberrypi.org/documentation/configuration/config-txt/README.md
    """

    CONF = u'/boot/config.txt'

    MODE_WRITE = u'w'
    MODE_READ = u'r'
    MODE_APPEND = u'a'

    KEY_DTOVERLAY = u'dtoverlay'

    ENTRY_ONEWIRE = u'w1-gpio'
    ENTRY_LIRC = u'lirc-rpi'

    def __init__(self):
        """
        Constructor
        """
        Config.__init__(self, self.CONF, u'#')

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

        results = self.search(u'(#?)%s=(.*?)\s' % key)
        for group, groups in results.iteritems():
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
                #onewire is disabled
                if disable:
                    #onewire already disabled
                    return True
                else:
                    #uncomment line
                    return self.uncomment(entries[dtoverlay]['group'])

            else:
                #onewire not disabled
                if disable:
                    #disable onewire
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
                #add new onewire entry
                return self.add(u'%s=%s' % (self.KEY_DTOVERLAY, dtoverlay))

        return False

    def is_onewire_enabled(self):
        """
        Return True if onewire is enabled

        Returns:
            bool: True if onewire enabled
        """
        return self.__is_dtoverlay_enabled(self.ENTRY_ONEWIRE)

    def enable_onewire(self):
        """
        Enable onewire support
        """
        return self.__enable_dtoverlay(self.ENTRY_ONEWIRE)

    def disable_onewire(self):
        """
        Disable onewire support
        """
        return self.__enable_dtoverlay(self.ENTRY_ONEWIRE, True)

    def is_lirc_enabled(self):
        """
        Return True if LIRC is enabled

        Returns:
            bool: True if onewire enabled
        """
        return self.__is_dtoverlay_enabled(self.ENTRY_LIRC)

    def enable_lirc(self):
        """
        Enable LIRC support
        """
        return self.__enable_dtoverlay(self.ENTRY_LIRC)

    def disable_lirc(self):
        """
        Disable LIRC support
        """
        return self.__enable_dtoverlay(self.ENTRY_LIRC, True)

class configtxtTests(unittest.TestCase):
    def setUp(self):
        #fake config file
        fd = open('config.txt', 'w')
        fd.write("""# For more options and information see 
# http://rpf.io/configtxtreadme
# Some settings may impact device functionality. See link above for details

# uncomment if you get no picture on HDMI for a default "safe" mode
#hdmi_safe=1

# uncomment this if your display has a black border of unused pixels visible
# and your display can output without overscan
#disable_overscan=1

# uncomment the following to adjust overscan. Use positive numbers if conso
# goes off screen, and negative if there is too much border
# goes off screen, and negative if there is too much border
#overscan_left=16
#overscan_right=16
#overscan_top=16
#overscan_bottom=16

# uncomment to force a console size. By default it will be display's size minus
# overscan.
#framebuffer_width=1280
#framebuffer_height=720

# uncomment if hdmi display is not detected and composite is being output
#hdmi_force_hotplug=1
coucou
# uncomment to force a specific HDMI mode (this will force VGA)
#hdmi_group=1
#hdmi_mode=1

# uncomment to force a HDMI mode rather than DVI. This can make audio work in
# DMT (computer monitor) modes
#hdmi_drive=2

# uncomment to increase signal to HDMI, if you have interference, blanking, or
# no display
#config_hdmi_boost=4

# uncomment for composite PAL 
#sdtv_mode=2

#uncomment to overclock the arm. 700 MHz is the default.
#arm_freq=800

# Uncomment some or all of these to enable the optional hardware interfaces
#dtparam=i2c_arm=on
#dtparam=i2s=on
#dtparam=spi=on

# Uncomment this to enable the lirc-rpi module
#dtoverlay=lirc-rpi

# Additional overlays and parameters are documented /boot/overlays/README

# Enable audio (loads snd_bcm2835)
dtparam=audio=on

# Enable 1wire
#dtoverlay=w1-gpio
""")
        fd.close()
        
        self.c = ConfigTxt()
        self.c.CONF = 'config.txt'

    def tearDown(self):
        os.remove('config.txt')
        pass

    def test_enable_then_disable_onewire(self):
        self.assertFalse(self.c.is_onewire_enabled())
        self.assertTrue(self.c.enable_onewire())
        self.assertTrue(self.c.is_onewire_enabled())
        self.assertTrue(self.c.disable_onewire())
        self.assertFalse(self.c.is_onewire_enabled())

    def test_remove_dtoverlays(self):
        results = self.c.search(u'(#?)%s=(.*?)\s' % self.c.KEY_DTOVERLAY)
        self.assertTrue(results.has_key(u'#dtoverlay=lirc-rpi\n'))
        self.assertTrue(results.has_key(u'#dtoverlay=w1-gpio\n'))
        self.assertTrue(self.c.remove([u'#dtoverlay=w1-gpio']))
        self.assertTrue(self.c.remove([u'#dtoverlay=lirc-rpi']))
        results = self.c.search(u'(#?)%s=(.*?)\s' % self.c.KEY_DTOVERLAY)
        self.assertFalse(results.has_key(u'#dtoverlay=lirc-rpi\n'))
        self.assertFalse(results.has_key(u'#dtoverlay=w1-gpio\n'))

    def test_add_dtoverlays(self):
        self.assertTrue(self.c.remove([u'#dtoverlay=w1-gpio', u'#dtoverlay=lirc-rpi']))
        results = self.c.search(u'(#?)%s=(.*?)\s' % self.c.KEY_DTOVERLAY)
        self.assertFalse(results.has_key(u'#dtoverlay=lirc-rpi\n'))
        self.assertFalse(results.has_key(u'#dtoverlay=w1-gpio\n'))
        self.assertTrue(self.c.add([u'dtoverlay=w1-gpio', u'dtoverlay=lirc-rpi']))
        results = self.c.search(u'(#?)%s=(.*?)\s' % self.c.KEY_DTOVERLAY)
        self.assertFalse(results.has_key(u'dtoverlay=lirc-rpi\n'))
        self.assertFalse(results.has_key(u'dtoverlay=w1-gpio\n'))



