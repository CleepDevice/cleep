#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from udevadm import Udevadm
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
import time

class LsblkTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.u = Udevadm()

    def tearDown(self):
        pass

    def test_get_device_type(self):
        mmcblk0 = self.u.get_device_type('mmcblk0')
        logging.debug('Mmcblk0: %s' % mmcblk0)
        self.assertEqual(mmcblk0, self.u.TYPE_MMC)

    def test_use_cache(self):
        tick = time.time()
        self.u.get_device_type('mmcblk0')
        without_cache_duration = time.time() - tick
        tick = time.time()
        self.u.get_device_type('mmcblk0')
        with_cache_duration = time.time() - tick
        self.assertLess(with_cache_duration, without_cache_duration, 'Cache seems to not be used')

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","*test_*.py" --concurrency=thread test_lsblk.py; coverage report -m -i
    unittest.main()
