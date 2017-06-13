#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.etcmodules import EtcModules
import unittest
import os

class etcmodulesTests(unittest.TestCase):
    def setUp(self):
        #fake config file
        fd = open('modules.conf', 'w')
        fd.write("""# /etc/modules: kernel modules to load at boot time.
#
# This file contains the names of kernel modules that should be loaded
# at boot time, one per line. Lines beginning with "#" are ignored.
w1-therm
w1-gpio
bcm4522""")
        fd.close()
        
        self.e = EtcModules(backup=False)
        self.e.CONF = 'modules.conf'

    def tearDown(self):
        os.remove('modules.conf')

    def test_onewire(self):
        self.assertTrue(self.e.is_onewire_enabled())
        self.assertTrue(self.e.enable_onewire())
        self.assertTrue(self.e.disable_onewire())
        self.assertFalse(self.e.is_onewire_enabled())
        self.assertTrue(self.e.enable_onewire())
        self.assertTrue(self.e.is_onewire_enabled())



