#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.configtxt import ConfigTxt
import unittest
import os


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
#dtoverlay=w1-gpio""")
        fd.close()
        
        self.c = ConfigTxt(backup=False)
        self.c.CONF = 'config.txt'

    def tearDown(self):
        os.remove('config.txt')

    def __find_key(self, key, results):
        for k,v in results:
            if key==k:
                return True
        return False

    def test_remove_dtoverlays(self):
        results = self.c.find(u'(#?)%s=(.*?)(\s|\Z)' % self.c.KEY_DTOVERLAY)
        self.assertTrue(self.__find_key(u'#dtoverlay=lirc-rpi', results))
        self.assertTrue(self.__find_key(u'#dtoverlay=w1-gpio', results))
        self.assertTrue(self.c.remove_lines([u'#dtoverlay=w1-gpio']))
        self.assertTrue(self.c.remove_lines([u'#dtoverlay=lirc-rpi']))

        results = self.c.find(u'(#?)%s=(.*?)(\s|\Z)' % self.c.KEY_DTOVERLAY)
        self.assertFalse(self.__find_key(u'#dtoverlay=lirc-rpi', results))
        self.assertFalse(self.__find_key(u'#dtoverlay=w1-gpio', results))

    def test_add_dtoverlays(self):
        self.assertTrue(self.c.remove_lines([u'#dtoverlay=w1-gpio', u'#dtoverlay=lirc-rpi']))
        results = self.c.find(u'(#?)%s=(.*?)(\s|\Z)' % self.c.KEY_DTOVERLAY)
        self.assertFalse(self.__find_key(u'#dtoverlay=lirc-rpi', results))
        self.assertFalse(self.__find_key(u'#dtoverlay=w1-gpio', results))

        self.assertTrue(self.c.add_lines([u'dtoverlay=w1-gpio', u'dtoverlay=lirc-rpi']))
        results = self.c.find(u'(#?)%s=(.*?)(\s|\Z)' % self.c.KEY_DTOVERLAY)
        self.assertFalse(self.__find_key(u'#dtoverlay=lirc-rpi', results))
        self.assertFalse(self.__find_key(u'#dtoverlay=w1-gpio', results))

    def test_enable_disable_onewire(self):
        self.assertFalse(self.c.is_onewire_enabled())
        self.assertTrue(self.c.enable_onewire())
        self.assertTrue(self.c.is_onewire_enabled())
        self.assertTrue(self.c.disable_onewire())
        self.assertFalse(self.c.is_onewire_enabled())

    def test_enable_disable_lirc(self):
        self.assertFalse(self.c.is_lirc_enabled())
        self.assertTrue(self.c.enable_lirc())
        self.assertTrue(self.c.is_lirc_enabled())
        self.assertTrue(self.c.disable_lirc())
        self.assertFalse(self.c.is_lirc_enabled())

    def test_spi(self):
        self.assertFalse(self.c.is_spi_enabled())
        self.assertTrue(self.c.enable_spi())
        self.assertTrue(self.c.is_spi_enabled())
        self.assertTrue(self.c.disable_spi())
        self.assertFalse(self.c.is_spi_enabled())

    def test_i2c(self):
        self.assertFalse(self.c.is_i2c_enabled())
        self.assertTrue(self.c.enable_i2c())
        self.assertTrue(self.c.is_i2c_enabled())
        self.assertTrue(self.c.disable_i2c())
        self.assertFalse(self.c.is_i2c_enabled())

