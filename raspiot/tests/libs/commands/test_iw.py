#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('/root/cleep/raspiot/libs/commands')
from iw import Iw
from raspiot.libs.tests.lib import TestLib
import unittest
import logging

logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class IwlistTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        self.i = Iw()

    def tearDown(self):
        pass

    def test_is_installed(self):
        self.assertTrue(self.i.is_installed())

    def test_get_adapters(self):
        adapters = self.i.get_adapters()
        print(adapters)
        self.assertGreaterEqual(len(adapters), 1)
        for adapter, values in adapters.items():
            self.assertTrue('interface' in values)
            self.assertTrue('network' in values)

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_iw.py
    #coverage report -m
    unittest.main()
