#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from lsblk import Lsblk
from cleep.libs.tests.lib import TestLib
import unittest
import logging
import time

class LsblkTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.l = Lsblk()

    def tearDown(self):
        pass

    def test_get_devices_infos(self):
        infos = self.l.get_devices_infos()
        logging.info(infos)
        self.assertTrue(len(infos)>0)
        self.assertTrue('mmcblk0' in infos)
        self.assertTrue('mmcblk0p1' in infos['mmcblk0'])
        self.assertTrue('mmcblk0p2' in infos['mmcblk0'])

        self.assertTrue('name' in infos['mmcblk0']['mmcblk0p1'])
        self.assertTrue('major' in infos['mmcblk0']['mmcblk0p1'])
        self.assertTrue('minor' in infos['mmcblk0']['mmcblk0p1'])
        self.assertTrue('size' in infos['mmcblk0']['mmcblk0p1'])
        self.assertTrue('totalsize' in infos['mmcblk0']['mmcblk0p1'])
        self.assertTrue('percent' in infos['mmcblk0']['mmcblk0p1'])
        self.assertTrue('readonly' in infos['mmcblk0']['mmcblk0p1'])
        self.assertTrue('mountpoint' in infos['mmcblk0']['mmcblk0p1'])
        self.assertTrue('partition' in infos['mmcblk0']['mmcblk0p1'])
        self.assertTrue('removable' in infos['mmcblk0']['mmcblk0p1'])
        self.assertTrue('drivemodel' in infos['mmcblk0']['mmcblk0p1'])

    def test_get_drives(self):
        infos = self.l.get_drives()
        logging.info(infos)
        self.assertTrue(len(infos)>0)
        self.assertTrue('mmcblk0' in infos)

        self.assertTrue('name' in infos['mmcblk0'])
        self.assertTrue('major' in infos['mmcblk0'])
        self.assertTrue('minor' in infos['mmcblk0'])
        self.assertTrue('size' in infos['mmcblk0'])
        self.assertTrue('totalsize' in infos['mmcblk0'])
        self.assertTrue('percent' in infos['mmcblk0'])
        self.assertTrue('readonly' in infos['mmcblk0'])
        self.assertTrue('mountpoint' in infos['mmcblk0'])
        self.assertTrue('partition' in infos['mmcblk0'])
        self.assertTrue('removable' in infos['mmcblk0'])
        self.assertTrue('drivemodel' in infos['mmcblk0'])

    def test_get_partitions(self):
        infos = self.l.get_partitions()
        logging.info(infos)
        self.assertTrue(len(infos)>0)
        self.assertFalse('mmcblk0' in infos)
        self.assertTrue('mmcblk0p1' in infos)
        self.assertTrue('mmcblk0p2' in infos)

        self.assertTrue('name' in infos['mmcblk0p1'])
        self.assertTrue('major' in infos['mmcblk0p1'])
        self.assertTrue('minor' in infos['mmcblk0p1'])
        self.assertTrue('size' in infos['mmcblk0p1'])
        self.assertTrue('totalsize' in infos['mmcblk0p1'])
        self.assertTrue('percent' in infos['mmcblk0p1'])
        self.assertTrue('readonly' in infos['mmcblk0p1'])
        self.assertTrue('mountpoint' in infos['mmcblk0p1'])
        self.assertTrue('partition' in infos['mmcblk0p1'])
        self.assertTrue('removable' in infos['mmcblk0p1'])
        self.assertTrue('drivemodel' in infos['mmcblk0p1'])

    def test_get_device_infos(self):
        self.assertIsNotNone(self.l.get_device_infos('mmcblk0'))
        self.assertIsNotNone(self.l.get_device_infos('mmcblk0p1'))
        self.assertIsNotNone(self.l.get_device_infos('mmcblk0p2'))
        self.assertIsNone(self.l.get_device_infos('mmcblk0p3'))

    def test_use_cache(self):
        tick = time.time()
        self.l.get_devices_infos()
        without_cache_duration = time.time() - tick
        tick = time.time()
        self.l.get_devices_infos()
        with_cache_duration = time.time() - tick
        self.assertLess(with_cache_duration, without_cache_duration, 'Cache seems to not be used')

if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_lsblk.py; coverage report -m -i
    unittest.main()
