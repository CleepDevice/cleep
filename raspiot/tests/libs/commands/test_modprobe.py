#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('/root/cleep/raspiot/libs/commands')
from modprobe import Modprobe
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
import time
from mock import Mock

class ModprobeTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.m = Modprobe()

    def tearDown(self):
        pass

    def test_load_module(self):
        self.m.command = Mock()
        self.m.get_last_return_code = Mock(return_value=0)
        self.assertTrue(self.m.load_module('dummy'))
        self.assertTrue(self.m.command.called)

    def test_load_module_failed(self):
        self.m.command = Mock()
        self.m.get_last_return_code = Mock(return_value=1)
        self.assertFalse(self.m.load_module('dummy'))
        self.assertTrue(self.m.command.called)

    def test_unload_module(self):
        self.m.command = Mock()
        self.m.get_last_return_code = Mock(return_value=0)
        self.assertTrue(self.m.unload_module('dummy'))
        self.assertTrue(self.m.command.called)

    def test_unload_module_failed(self):
        self.m.command = Mock()
        self.m.get_last_return_code = Mock(return_value=1)
        self.assertFalse(self.m.unload_module('dummy'))
        self.assertTrue(self.m.command.called)


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_modprobe.py; coverage report -m
    unittest.main()
