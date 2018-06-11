#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.installmodule import InstallModule, UninstallModule, PATH_FRONTEND
from raspiot.libs.cleepfilesystem import CleepFilesystem
import unittest
import logging
import time
import os
import shutil

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(filename)s:%(lineno)d %(levelname)s : %(message)s')

class InstallModuleTests(unittest.TestCase):

    def setUp(self):
        self.url_archive = 'https://github.com/tangb/raspiot/raw/master/tests/installmodule/%s.zip'
        self.archive_infos = {
            "description": "Test",
            "author": "Cleep",
            "country": None,
            "price": 0,
            "tags": [],
            "deps": [],
            "version": "1.0.0",
            "urls": {
                "info": None,
                "bugs": None,
                "site": None,
                "help": None
            },
            "icon": "message-processing",
            "download": None,
            "sha256": None
        }
        self.fs = CleepFilesystem()
        self.fs.DEBOUNCE_DURATION = 0.0

    def tearDown(self):
        if os.path.exists('/tmp/preinst.tmp'):
            os.remove('/tmp/preinst.tmp')
        if os.path.exists('/tmp/postinst.tmp'):
            os.remove('/tmp/postinst.tmp')
        if os.path.exists('/tmp/preuninst.tmp'):
            os.remove('/tmp/preuninst.tmp')
        if os.path.exists('/tmp/postuninst.tmp'):
            os.remove('/tmp/postuninst.tmp')
        if os.path.exists('/etc/raspiot/install/test/test.log'):
            f = open('/etc/raspiot/install/test/test.log', 'r')
            lines = f.readlines()
            f.close()
            for line in lines:
                os.remove(line.strip())
            shutil.rmtree('/etc/raspiot/install/test/', ignore_errors=True)

    def callback(self, status):
        pass

    #@unittest.skip('')
    def test_install_ok(self):
        #install
        name = 'raspiot_test_1.0.0.ok'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '4a158ba9ebe211790948ca3571628326a2fa8f339c22e6c5d1b4f11c9cb5b679'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/etc/raspiot/install/test/test.log'))
        self.assertTrue(os.path.exists('/etc/raspiot/install/test/preuninst.sh'))
        self.assertTrue(os.path.exists('/etc/raspiot/install/test/postuninst.sh'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    #@unittest.skip('')
    def test_install_ok_without_script(self):
        #install
        name = 'raspiot_test_1.0.0.noscript-ok'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '2dd607a7b07d9fc576ea125a7286c5ee14e0a0f3e4847f9c03574fb6b37c0f7c'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/etc/raspiot/install/test/test.log'))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/preuninst.sh'))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/postuninst.sh'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    #@unittest.skip('')
    def test_install_ko_checksum(self):
        #install
        name = 'raspiot_test_1.0.0.ok'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '2dd607a7b07d9fc576ea125a7286c5ee14e0a0f3e4847f9c03574fb6b37c0f7c'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_ERROR_DOWNLOAD)

        #check installation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/test.log'))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/preuninst.sh'))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/postuninst.sh'))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    #@unittest.skip('')
    def test_install_ko_preinst(self):
        #install
        name = 'raspiot_test_1.0.0.preinst-ko'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '61dd6b2c0a3593357cdd803339589c5bb08c5672ca59f0831569cb2e5c7c545c'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_ERROR_PREINST)

        #check installation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/test.log'))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/preuninst.sh'))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/postuninst.sh'))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    #@unittest.skip('')
    def test_install_ko_postinst(self):
        #install
        name = 'raspiot_test_1.0.0.postinst-ko'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = 'fa5ea42e26bdd6aeb1957d0bc259b9db8cd95df2445554ae7685cbcac940b090'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_ERROR_POSTINST)

        #check installation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test.log'))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/preuninst.sh'))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/postuninst.sh'))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)



class UninstallModuleTests(unittest.TestCase):

    def setUp(self):
        self.url_archive = 'https://github.com/tangb/raspiot/raw/master/tests/installmodule/%s.zip'
        self.archive_infos = {
            "description": "Test",
            "author": "Cleep",
            "country": None,
            "price": 0,
            "tags": [],
            "deps": [],
            "version": "1.0.0",
            "urls": {
                "info": None,
                "bugs": None,
                "site": None,
                "help": None
            },
            "icon": "message-processing",
            "download": None,
            "sha256": None
        }
        self.fs = CleepFilesystem()
        self.fs.DEBOUNCE_DURATION = 0.0

    def tearDown(self):
        if os.path.exists('/tmp/preinst.tmp'):
            os.remove('/tmp/preinst.tmp')
        if os.path.exists('/tmp/postinst.tmp'):
            os.remove('/tmp/postinst.tmp')
        if os.path.exists('/tmp/preuninst.tmp'):
            os.remove('/tmp/preuninst.tmp')
        if os.path.exists('/tmp/postuninst.tmp'):
            os.remove('/tmp/postuninst.tmp')
        if os.path.exists('/etc/raspiot/install/test/test.log'):
            f = open('/etc/raspiot/install/test/test.log', 'r')
            lines = f.readlines()
            f.close()
            for line in lines:
                os.remove(line.strip())
            if os.path.exists('/etc/raspiot/install/test/'):
                shutil.rmtree('/etc/raspiot/install/test/')

    def callback(self, status):
        pass

    #@unittest.skip('')
    def test_uninstall_ok(self):
        #install
        name = 'raspiot_test_1.0.0.ok'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '4a158ba9ebe211790948ca3571628326a2fa8f339c22e6c5d1b4f11c9cb5b679'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/etc/raspiot/install/test/test.log'))
        self.assertTrue(os.path.exists('/etc/raspiot/install/test/preuninst.sh'))
        self.assertTrue(os.path.exists('/etc/raspiot/install/test/postuninst.sh'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

        #uninstall module
        u = UninstallModule('test', False, self.callback, self.fs)
        u.start()
        time.sleep(0.5)

        #wait until end of uninstall
        while u.get_status()[u'status']==u.STATUS_UNINSTALLING:
            time.sleep(0.5)
        self.assertEqual(u.get_status()['status'], u.STATUS_UNINSTALLED)

        #check uninstallation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/')))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/'))

    #@unittest.skip('')
    def test_uninstall_without_script_ok(self):
        #install
        name = 'raspiot_test_1.0.0.noscript-ok'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '2dd607a7b07d9fc576ea125a7286c5ee14e0a0f3e4847f9c03574fb6b37c0f7c'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/etc/raspiot/install/test/test.log'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

        #uninstall module
        u = UninstallModule('test', False, self.callback, self.fs)
        u.start()
        time.sleep(0.5)

        #wait until end of uninstall
        while u.get_status()[u'status']==u.STATUS_UNINSTALLING:
            time.sleep(0.5)
        self.assertEqual(u.get_status()['status'], u.STATUS_UNINSTALLED)

        #check uninstallation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/test.log'))

    #@unittest.skip('')
    def test_uninstall_ko_preuninst(self):
        #install
        name = 'raspiot_test_1.0.0.preuninst-ko'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '628065d3cc0a4ab802986c46ea7a9fc190f8b5d7ffef8674ec152feb5eb116b0'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/etc/raspiot/install/test/test.log'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

        #uninstall module
        u = UninstallModule('test', False, self.callback, self.fs)
        u.start()
        time.sleep(0.5)

        #wait until end of uninstall
        while u.get_status()[u'status']==u.STATUS_UNINSTALLING:
            time.sleep(0.5)
        self.assertEqual(u.get_status()['status'], u.STATUS_UNINSTALLED_ERROR_PREUNINST)

        #check uninstallation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/test.log'))

    #@unittest.skip('')
    def test_uninstall_ko_postuninst(self):
        #install
        name = 'raspiot_test_1.0.0.postuninst-ko'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '0886ae4795232f1b04e185cd5e433e49fc9b5e68c28b9d4ade9ae4f7d2e4aac7'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/etc/raspiot/install/test/test.log'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

        #uninstall module
        u = UninstallModule('test', False, self.callback, self.fs)
        u.start()
        time.sleep(0.5)

        #wait until end of uninstall
        while u.get_status()[u'status']==u.STATUS_UNINSTALLING:
            time.sleep(0.5)
        self.assertEqual(u.get_status()['status'], u.STATUS_UNINSTALLED_ERROR_POSTUNINST)

        #check uninstallation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/')))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/'))

    #@unittest.skip('')
    def test_uninstall_ko_remove(self):
        #install
        name = 'raspiot_test_1.0.0.postuninst-ko'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '0886ae4795232f1b04e185cd5e433e49fc9b5e68c28b9d4ade9ae4f7d2e4aac7'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/etc/raspiot/install/test/test.log'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

        #remove installed file to simulate error
        os.remove('/etc/raspiot/install/test/test.log')

        #uninstall module
        u = UninstallModule('test', False, self.callback, self.fs)
        u.start()
        time.sleep(0.5)

        #wait until end of uninstall
        while u.get_status()[u'status']==u.STATUS_UNINSTALLING:
            time.sleep(0.5)
        self.assertEqual(u.get_status()['status'], u.STATUS_UNINSTALLED_ERROR_REMOVE)

        #check uninstallation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/')))
        self.assertFalse(os.path.exists('/etc/raspiot/install/test/'))


