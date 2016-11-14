#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('/root/cleep/raspiot/libs/commands')
from ifconfig import Ifconfig
from raspiot.libs.tests.lib import TestLib
import unittest
import logging

logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class IfconfigTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        self.i = Ifconfig()

    def tearDown(self):
        pass

    def test_get_configurations(self):
        interfaces = self.i.get_configurations()
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

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_ifconfig.py
    #coverage report -m
    unittest.main()
