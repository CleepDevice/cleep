#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('/root/cleep/raspiot/libs/commands')
from blkid import Blkid
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.utils import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pformat


class BlkidTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')
        self.b = Blkid()

    def tearDown(self):
        pass

    def test_get_devices(self):
        devices = self.b.get_devices()
        logging.debug('Devices: %s' % devices)
        self.assertEqual(len(devices), 2, 'Blkid should find 2 mountpoints')
        for device, _ in devices.items():
            self.assertTrue(device.find('/dev')!=-1, 'Device should contains /dev/xxx')

    def test_get_device_by_uuid(self):
        devices = self.b.get_devices()
        logging.debug('Devices: %s' % self.b.devices)
        device = devices[devices.keys()[0]]
        logging.debug('Device: %s' % device)
        result = self.b.get_device_by_uuid(device[u'uuid'])
        self.assertEqual(result['device'], device['device'])

    def test_get_device_by_uuid_invalid_uuid(self):
        self.assertEqual(self.b.get_device_by_uuid('uuid'), None)

    def test_get_device_by_partuuid(self):
        devices = self.b.get_devices()
        logging.debug('Devices: %s' % self.b.devices)
        device = devices[devices.keys()[0]]
        logging.debug('Device: %s' % device)
        result = self.b.get_device_by_partuuid(device[u'partuuid'])
        self.assertEqual(result['device'], device['device'])

    def test_get_device_by_partuuid_invalid_partuuid(self):
        self.assertEqual(self.b.get_device_by_partuuid('uuid'), None)

    def test_get_device(self):
        devices = self.b.get_devices()
        mountpoint = devices.keys()[0]
        uuid = devices[mountpoint]
        self.assertEqual(self.b.get_device(mountpoint), uuid)

    def test_get_device_invalid_device(self):
        self.assertEqual(self.b.get_device('mountpoint'), None)

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_blkid.py
    #coverage report -m
    unittest.main()
