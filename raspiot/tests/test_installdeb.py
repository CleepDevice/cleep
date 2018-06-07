#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.installdeb import InstallDeb
from raspiot.libs.cleepfilesystem import CleepFilesystem
import unittest
import logging
import time
import os

logging.basicConfig(level=logging.DEBUG, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class InstallDebTests(unittest.TestCase):

    def setUp(self):
        self.archive = 'wiringpi'
        self.fs = CleepFilesystem()
        self.fs.DEBOUNCE_DURATION = 0.0

    def tearDown(self):
        if os.path.exists('/usr/bin/gpio'):
            os.system('/usr/bin/yes 2>/dev/null | apt-get purge %s > /dev/null 2>&1' % self.archive)

    def callback(self, status):
        pass

    def test_install_block(self):
        #install deb file
        i = InstallDeb(self.callback, self.fs, blocking=True)
        res = i.install('%s.deb' % self.archive)
        self.assertTrue(res)

        #check deb is installed
        self.assertTrue(os.path.exists('/usr/bin/gpio'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_nonblock(self):
        #install deb in non blocking mode
        i = InstallDeb(self.callback, self.fs, blocking=False)
        res = i.install('%s.deb' % self.archive)
        self.assertIsNone(res)

        #wait end of install
        while True:
            s = i.get_status()
            if s['status']!=i.STATUS_RUNNING:
                break
            time.sleep(0.25)

        #check deb is installed
        self.assertTrue(os.path.exists('/usr/bin/gpio'))

    def test_install_failure(self):
        i = InstallDeb(self.callback, self.fs, blocking=True)
        res = i.install('test_intalldeb.py')
        self.assertFalse(res)

