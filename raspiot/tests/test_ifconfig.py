#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.ifconfig import Ifconfig
import unittest
import logging

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class IfconfigTests(unittest.TestCase):

    def setUp(self):
        self.i = Ifconfig()

    def tearDown(self):
        pass

    def test_get_interfaces(self):
        interfaces = self.i.get_interfaces()
        interface = interfaces.keys()[0]
        self.assertFalse('lo' in interfaces.keys())
        self.assertGreaterEqual(len(interfaces), 1)
        self.assertTrue('mac' in interfaces[interface].keys())
        self.assertTrue('interface' in interfaces[interface].keys())
        self.assertTrue('ipv4' in interfaces[interface].keys())
        self.assertTrue('gateway_ipv4' in interfaces[interface].keys())
        self.assertTrue('netmask_ipv4' in interfaces[interface].keys())
        self.assertTrue('ipv6' in interfaces[interface].keys())
        self.assertTrue('gateway_ipv6' in interfaces[interface].keys())
        self.assertTrue('netmask_ipv6' in interfaces[interface].keys())

