#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.commands.lsmod import Lsmod
import unittest
import logging

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class IwlistTests(unittest.TestCase):

    def setUp(self):
        self.l = Lsmod()

    def tearDown(self):
        pass

    def test_get_loaded_modules(self):
        mods = self.l.get_loaded_modules()
        logging.info(mods)
        self.assertTrue(len(mods)>0)

    def test_is_gpio_loaded(self):
        self.assertFalse(self.l.is_module_loaded('w1-therm'))

    def test_is_hciuart_loaded(self):
        self.assertTrue(self.l.is_module_loaded('hci-uart'))

