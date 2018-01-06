#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.iwconfig import Iwconfig
import unittest
import logging

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class IwconfigTests(unittest.TestCase):

    def setUp(self):
        self.i = Iwconfig()

    def tearDown(self):
        pass

    def test_get_interfaces(self):
        interfaces = self.i.get_interfaces()
        self.assertFalse('lo' in interfaces.keys())
        self.assertGreaterEqual(len(interfaces), 1)
        if len(interfaces)>0:
            interface = interfaces[interfaces.keys()[0]]
            self.assertTrue('network' in interface.keys())

