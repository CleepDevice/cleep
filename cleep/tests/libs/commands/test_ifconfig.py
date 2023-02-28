#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from ifconfig import Ifconfig
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class IfconfigTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')
        self.i = Ifconfig()

    def tearDown(self):
        pass

    def test_get_configurations(self):
        interfaces = self.i.get_configurations()
        interface = list(interfaces.keys())[0]
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
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_ifconfig.py; coverage report -m -i
    unittest.main()
