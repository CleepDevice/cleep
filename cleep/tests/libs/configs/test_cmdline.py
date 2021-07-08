#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from cmdline import Cmdline
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.exception import MissingParameter, InvalidParameter, CommandError
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pformat
import io
from unittest.mock import Mock

logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class CmdlineTest(unittest.TestCase):

    FILE_NAME = 'cmdline'
    CONTENT = u'coherent_pool=1M 8250.nr_uarts=0 bcm2708_fb.fbwidth=656 bcm2708_fb.fbheight=416 bcm2708_fb.fbswap=1 vc_mem.mem_base=0x3ec00000 vc_mem.mem_size=0x40000000  dwc_otg.lpm_enable=0 console=ttyS0,115200 console=tty1 root=90a83158-560d rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait quiet fastboot noswap ro'

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        c = Cmdline
        self.c = c()
        self.c.command = Mock(return_value={
            'error': False,
            'killed': False,
            'stderr': [],
            'stdout': [self.CONTENT],
        })
        self.blkid_mock = Mock()
        self.blkid_mock.CONF = self.FILE_NAME
        data = {
            'device': '/dev/mmcblk0p2',
            'uuid': '90a83158-560d-48ee-9de9-40c51d93c287',
            'type': 'ext4',
            'partuuid': '90a83158-560d'
        }
        self.blkid_mock.get_device_by_uuid.return_value = data
        self.blkid_mock.get_device_by_partuuid.return_value = data
        self.c.blkid = self.blkid_mock
        self.lsblk_mock = Mock()
        self.lsblk_mock.get_drives.return_value = {'mmcblk0p1': '/boot', 'mmcblk0p2': '/'}
        self.c.lsblk = self.lsblk_mock

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_get_root_drive(self):
        self.assertEqual(self.c.get_root_drive(), 'mmcblk0p2', 'Invalid returned root driver')

    def test_get_root_partition(self):
        self.assertEqual(self.c.get_root_partition(), '/', 'Invalid returned root partition')





class CmdlineWithPartuuidTest(unittest.TestCase):

    FILE_NAME = 'cmdline'
    CONTENT = u'coherent_pool=1M 8250.nr_uarts=0 bcm2708_fb.fbwidth=656 bcm2708_fb.fbheight=416 bcm2708_fb.fbswap=1 vc_mem.mem_base=0x3ec00000 vc_mem.mem_size=0x40000000  dwc_otg.lpm_enable=0 console=ttyS0,115200 console=tty1 root=PARTUUID=90a83158-560d rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait quiet fastboot noswap ro'

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        c = Cmdline
        self.c = c()
        self.c.command = Mock(return_value={
            'error': False,
            'killed': False,
            'stderr': [],
            'stdout': [self.CONTENT],
        })
        self.blkid_mock = Mock()
        self.blkid_mock.CONF = self.FILE_NAME
        data = {
            'device': '/dev/mmcblk0p2',
            'uuid': '90a83158-560d-48ee-9de9-40c51d93c287',
            'type': 'ext4',
            'partuuid': '90a83158-560d'
        }
        self.blkid_mock.get_device_by_uuid.return_value = data
        self.blkid_mock.get_device_by_partuuid.return_value = data
        self.c.blkid = self.blkid_mock
        self.lsblk_mock = Mock()
        self.lsblk_mock.get_drives.return_value = {'mmcblk0p1': '/boot', 'mmcblk0p2': '/'}
        self.c.lsblk = self.lsblk_mock

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_get_root_drive(self):
        self.assertEqual(self.c.get_root_drive(), 'mmcblk0p2', 'Invalid returned root driver')

    def test_get_root_partition(self):
        self.assertEqual(self.c.get_root_partition(), '/', 'Invalid returned root partition')





class CmdlineWithUuidTest(unittest.TestCase):

    FILE_NAME = 'cmdline'
    CONTENT = u'coherent_pool=1M 8250.nr_uarts=0 bcm2708_fb.fbwidth=656 bcm2708_fb.fbheight=416 bcm2708_fb.fbswap=1 vc_mem.mem_base=0x3ec00000 vc_mem.mem_size=0x40000000  dwc_otg.lpm_enable=0 console=ttyS0,115200 console=tty1 root=UUID=90a83158-560d-48ee-9de9-40c51d93c287 rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait quiet fastboot noswap ro'

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        c = Cmdline
        self.c = c()
        self.c.command = Mock(return_value={
            'error': False,
            'killed': False,
            'stderr': [],
            'stdout': [self.CONTENT],
        })
        self.blkid_mock = Mock()
        self.blkid_mock.CONF = self.FILE_NAME
        data = {
            'device': '/dev/mmcblk0p2',
            'uuid': '90a83158-560d-48ee-9de9-40c51d93c287',
            'type': 'ext4',
            'partuuid': '90a83158-560d'
        }
        self.blkid_mock.get_device_by_uuid.return_value = data
        self.blkid_mock.get_device_by_partuuid.return_value = data
        self.c.blkid = self.blkid_mock
        self.lsblk_mock = Mock()
        self.lsblk_mock.get_drives.return_value = {'mmcblk0p1': '/boot', 'mmcblk0p2': '/'}
        self.c.lsblk = self.lsblk_mock

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_get_root_drive(self):
        self.assertEqual(self.c.get_root_drive(), 'mmcblk0p2', 'Invalid returned root driver')

    def test_get_root_partition(self):
        self.assertEqual(self.c.get_root_partition(), '/', 'Invalid returned root partition')

if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_cmdline.py; coverage report -m -i
    unittest.main()

