#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from modprobe import Modprobe
from cleep.libs.tests.lib import TestLib
import unittest
import logging
import time
from unittest.mock import Mock

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
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_modprobe.py; coverage report -m -i
    unittest.main()
