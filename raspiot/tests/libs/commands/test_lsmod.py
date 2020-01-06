#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('/root/cleep/raspiot/libs/commands')
from lsmod import Lsmod
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from mock import Mock
import time

class LsmodTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.l = Lsmod()

    def tearDown(self):
        pass

    def test_get_loaded_modules(self):
        mods = self.l.get_loaded_modules()
        logging.info(mods)
        self.assertTrue(len(mods)>0)

    def test_is_module_loaded(self):
        self.assertTrue(self.l.is_module_loaded('hci-uart'))
        self.assertFalse(self.l.is_module_loaded('dummy'))

    def test_use_cache(self):
        tick = time.time()
        self.l.is_module_loaded('hci-uart')
        without_cache_duration = time.time() - tick
        tick = time.time()
        self.l.is_module_loaded('hci-uart')
        with_cache_duration = time.time() - tick
        self.assertLess(with_cache_duration, without_cache_duration, 'Cache seems to not be used')

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_lsmod.py; coverage report -m
    unittest.main()
