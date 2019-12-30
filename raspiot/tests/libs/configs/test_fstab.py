#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys 
sys.path.append('/root/cleep/raspiot/libs/configs')
from fstab import Fstab
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.utils import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pprint
import io
from mock import Mock

logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class FstabTests(unittest.TestCase):

    FILE_NAME = 'fstab'
    CONTENT = u"""# /etc/fstab: static file system information.
#
# Use 'blkid' to print the universally unique identifier for a
# device; this may be used with UUID= as a more robust way to name devices
# that works even if disks are added and removed. See fstab(5).
#
# <file system> <mount point>   <type>  <options>       <dump>  <pass>
# / was on /dev/sda1 during installation
UUID=b8e3f3c7-6324-4f58-8009-eace60bda876 /               ext4    discard,noatime,commit=600,errors=remount-ro 0       1
# /home was on /dev/sda6 during installation
UUID=79b36e19-a291-4682-a153-545b956a0607 /home           ext4    discard,noatime,commit=600,defaults         0       2
# swap was on /dev/sda5 during installation
UUID=58337582-3a9e-4a15-b4ad-4a7f354d9af3 none            swap    sw              0       0
/dev/sdb1       /media/usb0     auto    rw,user,noauto  0       0
/dev/sdb2       /media/usb1     auto    rw,user,noauto  0       0

#invalid type
TEST=b8e3f3c7-6324-4f58-8009-eace60bda876 /               ext4    discard,noatime,commit=600,errors=remount-ro 0       1

#server
192.168.1.1:/data/test       /media/test       nfs     soft,rw,nfsvers=3,rsize=32768,wsize=32768,timeo=600,actimeo=0,intr 0   0
desktop:/data/stuff       /media/stuff       nfs     soft,rw,nfsvers=3,rsize=32768,wsize=32768,timeo=600,actimeo=0,intr   0   0
192.168.1.1:/data/toserver       /media/toserver       nfs    soft,rw,nfsvers=3,rsize=32768,wsize=32768,timeo=600,actimeo=0,intr  0   0

#media
#192.168.1.10:/media/backup /media/tangmedia    nfs rsize=8192,wsize=8192,timeo=14,intr,vers=3

#store
192.168.1.53:/media/raid    /media/tangstore    nfs     soft,rw,nfsvers=3,rsize=32768,wsize=32768,timeo=600,actimeo=0,intr  0   0"""

    def setUp(self):
      	TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        f = Fstab
        f.CONF = self.FILE_NAME
        self.f = f(self.fs, False)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_get_mountpoints(self):
        mountpoints = self.f.get_mountpoints()
        self.assertEqual(len(mountpoints), 9)

        self.assertTrue(mountpoints.has_key(u'/media/usb1'))
        self.assertEqual(mountpoints[u'/media/usb1'][u'local'], True)
        self.assertTrue(mountpoints.has_key(u'/media/toserver'))
        self.assertEqual(mountpoints[u'/media/toserver'][u'local'], False)

    def test_devices(self):
        devices = self.f.get_all_devices()
        self.assertNotEqual(len(devices), 0)

    def test_add_mountpoint(self):
        self.assertRaises(MissingParameter, self.f.add_mountpoint, None, u'/dev/sda1', u'ext4', u'discard,noatime')
        self.assertRaises(MissingParameter, self.f.add_mountpoint, u'/media/mount', None, u'ext4', u'discard,noatime')
        self.assertRaises(MissingParameter, self.f.add_mountpoint, u'/media/mount', u'/dev/sda1', None, u'discard,noatime')
        self.assertRaises(MissingParameter, self.f.add_mountpoint, u'/media/mount', u'/dev/sda1', u'ext4', None)
        self.assertRaises(MissingParameter, self.f.add_mountpoint, u'', u'/dev/sda1', u'ext4', u'discard,noatime')
        self.assertRaises(MissingParameter, self.f.add_mountpoint, u'/media/mount', u'', 'ext4', u'discard,noatime')
        self.assertRaises(MissingParameter, self.f.add_mountpoint, u'/media/mount', u'/dev/sda1', u'', u'discard,noatime')
        self.assertRaises(MissingParameter, self.f.add_mountpoint, u'/media/mount', u'/dev/sda1', u'ext4', u'')

        self.assertTrue(self.f.add_mountpoint('/dev/sda1', '/media/mount', 'ext4', 'discard,noatime'))

        mountpoints = self.f.get_mountpoints()
        self.assertTrue(mountpoints.has_key(u'/media/mount'))

    def test_add_existing_mountpoint(self):
        self.assertFalse(self.f.add_mountpoint('/dev/sda1', '/media/tangstore', 'ext4', 'discard,noatime'))

    def test_delete_unknown_mountpoint(self):
        self.assertFalse(self.f.delete_mountpoint('/dev/dummy'))

    def test_delete_mountpoint(self):
        self.assertTrue(self.f.delete_mountpoint('/media/tangstore'))
        mountpoints = self.f.get_mountpoints()
        self.assertFalse(mountpoints.has_key(u'/media/tangstore'))

    def test_delete_mountpoint_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.f.delete_mountpoint(None)
        self.assertEqual(cm.exception.message, 'Parameter "mountpoint" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.f.delete_mountpoint('')
        self.assertEqual(cm.exception.message, 'Parameter "mountpoint" is missing')

    def test_reload_fstab(self):
        self.f.console = Mock()
        self.f.console.command.return_value = {
            'error': ['Error occured'],
            'killed': False,
        }
        self.assertFalse(self.f.reload_fstab())

        self.f.console.command.return_value = {
            'error': [],
            'killed': True,
        }
        self.assertFalse(self.f.reload_fstab())

        self.f.console.command.return_value = {
            'error': [],
            'killed': False,
        }
        self.assertTrue(self.f.reload_fstab())


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_fstab.py
    #coverage report -m
    unittest.main()
