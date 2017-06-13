#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.cmdlinetxt import CmdlineTxt
import unittest
import os


class cmdlinetxtTests(unittest.TestCase):
    def setUp(self):
        #fake config file
        fd = open('cmdline.txt', 'w')
        fd.write("""dwc_otg.lpm_enable=0 console=serial0,115200 console=tty1 root=PARTUUID=45ea7472-02 rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait""")
        fd.close()
        
        self.c = CmdlineTxt()
        self.c.CONF = 'cmdline.txt'

    def tearDown(self):
        os.remove('cmdline.txt')

    def test_console(self):
        self.assertTrue(self.c.is_console_enabled())
        self.assertFalse(self.c.enable_console())
        self.assertTrue(self.c.disable_console())
        self.assertFalse(self.c.is_console_enabled())
        self.assertTrue(self.c.enable_console())
        self.assertTrue(self.c.is_console_enabled())




