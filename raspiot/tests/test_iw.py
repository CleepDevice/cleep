#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.commands.iw import Iw
import unittest
import logging

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class IwlistTests(unittest.TestCase):

    def setUp(self):
        self.i = Iw()

    def tearDown(self):
        pass

    def test_get_interfaces(self):
        adapters = self.i.get_adapters()
        print(adapters)
        self.assertGreaterEqual(len(adapters), 1)
        for adapter in adapters:
            item = adapters[adapter]
            self.assertTrue('interface' in item)
            self.assertTrue('network' in item)

