#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.installraspiot import InstallRaspiot
from raspiot.libs.cleepfilesystem import CleepFilesystem
import unittest
import logging
import time
import os

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(filename)s:%(lineno)d %(levelname)s : %(message)s')

class InstallRaspiotTests(unittest.TestCase):

    def setUp(self):
        self.url_raspiot = 'https://github.com/tangb/raspiot/raw/master/tests/installraspiot/%s.zip'
        self.url_checksum = 'https://github.com/tangb/raspiot/raw/master/tests/installraspiot/%s.sha256'
        self.fs = CleepFilesystem()
        self.fs.DEBOUNCE_DURATION = 0.0

    def tearDown(self):
        if os.path.exists('/usr/bin/gpio'):
            os.system('/usr/bin/yes 2>/dev/null | apt-get purge wiringpi > /dev/null 2>&1')
        if os.path.exists('/tmp/preinst.tmp'):
            os.remove('/tmp/preinst.tmp')
        if os.path.exists('/tmp/postinst.tmp'):
            os.remove('/tmp/postinst.tmp')

    def callback(self, status):
        pass

    def test_install_ok_with_scripts(self):
        #install
        name = 'installraspiot.ok'
        url_raspiot = self.url_raspiot % name
        url_checksum = self.url_checksum % name
        i = InstallRaspiot(url_raspiot, url_checksum, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_UPDATING:
            time.sleep(1)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_UPDATED)

        #check installation
        self.assertTrue(os.path.exists('/usr/bin/gpio'))
        self.assertTrue(os.path.exists('/tmp/preinst.tmp'))
        self.assertTrue(os.path.exists('/tmp/postinst.tmp'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_error_postscript(self):
        #install
        name = 'installraspiot.post-ko'
        url_raspiot = self.url_raspiot % name
        url_checksum = self.url_checksum % name
        i = InstallRaspiot(url_raspiot, url_checksum, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_UPDATING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_ERROR_POSTINST)

        #check installation
        self.assertTrue(os.path.exists('/tmp/preinst.tmp'))
        self.assertTrue(os.path.exists('/usr/bin/gpio'))
        self.assertFalse(os.path.exists('/tmp/postinst.tmp'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_error_prescript(self):
        #install
        name = 'installraspiot.pre-ko'
        url_raspiot = self.url_raspiot % name
        url_checksum = self.url_checksum % name
        i = InstallRaspiot(url_raspiot, url_checksum, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_UPDATING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_ERROR_PREINST)

        #check installation
        self.assertFalse(os.path.exists('/tmp/preinst.tmp'))
        self.assertFalse(os.path.exists('/usr/bin/gpio'))
        self.assertFalse(os.path.exists('/tmp/postinst.tmp'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_error_deb(self):
        #install
        name = 'installraspiot.deb-ko'
        url_raspiot = self.url_raspiot % name
        url_checksum = self.url_checksum % name
        i = InstallRaspiot(url_raspiot, url_checksum, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_UPDATING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_ERROR_DEB)

        #check installation
        self.assertTrue(os.path.exists('/tmp/preinst.tmp'))
        self.assertFalse(os.path.exists('/usr/bin/gpio'))
        self.assertFalse(os.path.exists('/tmp/postinst.tmp'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_ok_without_script(self):
        #install
        name = 'installraspiot.noscript-ok'
        url_raspiot = self.url_raspiot % name
        url_checksum = self.url_checksum % name
        i = InstallRaspiot(url_raspiot, url_checksum, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_UPDATING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_UPDATED)

        #check installation
        self.assertFalse(os.path.exists('/tmp/preinst.tmp'))
        self.assertTrue(os.path.exists('/usr/bin/gpio'))
        self.assertFalse(os.path.exists('/tmp/postinst.tmp'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_bad_checksum(self):
        #install
        name = 'installraspiot.badchecksum-ko'
        url_raspiot = self.url_raspiot % name
        url_checksum = self.url_checksum % name
        i = InstallRaspiot(url_raspiot, url_checksum, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_UPDATING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_ERROR_DOWNLOAD_ARCHIVE)

        #check installation
        self.assertFalse(os.path.exists('/tmp/preinst.tmp'))
        self.assertFalse(os.path.exists('/usr/bin/gpio'))
        self.assertFalse(os.path.exists('/tmp/postinst.tmp'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)
    

