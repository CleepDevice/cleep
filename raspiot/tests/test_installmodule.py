#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.installmodule import InstallModule, UninstallModule, PATH_FRONTEND, UpdateModule
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
import unittest
import logging
import time
import os
import shutil

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(filename)s:%(lineno)d %(levelname)s : %(message)s')
#logging.basicConfig(level=logging.DEBUG, format=u'%(asctime)s %(filename)s:%(lineno)d %(levelname)s : %(message)s')

class InstallModuleTests(unittest.TestCase):

    def setUp(self):
        self.url_archive = 'https://github.com/tangb/cleep-os/raw/master/cleepos/tests/resources/installmodule/%s.zip'
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
        self.fs.enable_write()

    def tearDown(self):
        if os.path.exists('/tmp/preinst.tmp'):
            os.remove('/tmp/preinst.tmp')
        if os.path.exists('/tmp/postinst.tmp'):
            os.remove('/tmp/postinst.tmp')
        if os.path.exists('/tmp/preuninst.tmp'):
            os.remove('/tmp/preuninst.tmp')
        if os.path.exists('/tmp/postuninst.tmp'):
            os.remove('/tmp/postuninst.tmp')
        if os.path.exists('/opt/raspiot/install/test/test.log'):
            f = open('/opt/raspiot/install/test/test.log', 'r')
            lines = f.readlines()
            f.close()
            for line in lines:
                os.remove(line.strip())
            shutil.rmtree('/opt/raspiot/install/test/', ignore_errors=True)
        if os.path.exists('/usr/lib/python2.7/dist-packages/raspiot/modules/test'):
            shutil.rmtree('/usr/lib/python2.7/dist-packages/raspiot/modules/test')
        if os.path.exists('/opt/raspiot/html/js/modules/test'):
            shutil.rmtree('/opt/raspiot/html/js/modules/test')

    def callback(self, status):
        pass

    def test_install_ok(self):
        #install
        name = 'cleepmod_test_1.0.0.ok'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '5a522882b74f990ba0175808f52540bd1c1bcfe258873f83fc9e90e85d64a8f4'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/test.log'))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/preuninst.sh'))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/postuninst.sh'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_ok_without_script(self):
        #install
        name = 'cleepmod_test_1.0.0.noscript-ok'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '0b43bcff0e4dc88f4e24261913bd118cb53c9c9a82ab1a61b053477615421da7'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/test.log'))
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/preuninst.sh'))
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/postuninst.sh'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_ko_checksum(self):
        #install
        name = 'cleepmod_test_1.0.0.ok'
        self.archive_infos['download'] = self.url_archive % name
        #enter invalid checkum
        self.archive_infos['sha256'] = '5a522882b74f990ba0175808f52540bd1c1bcfe258873f83fc9e90e85d64a8f'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_ERROR_DOWNLOAD)

        #check installation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/test.log'))
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/preuninst.sh'))
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/postuninst.sh'))
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_ko_preinst(self):
        #install
        name = 'cleepmod_test_1.0.0.preinst-ko'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '7c96e007d2ecebcde543c2bbf7f810904976f1dae7a8bfce438807e5b30392a6'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_ERROR_PREINST)

        #check installation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/test.log'))
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/preuninst.sh'))
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/postuninst.sh'))
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

    def test_install_ko_postinst(self):
        #install
        name = 'cleepmod_test_1.0.0.postinst-ko'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '31d04988811c1ab449278bce66d608d1fbbc9324b0d60dd260ce36a326b700b4'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_ERROR_POSTINST)

        #check installation
        self.assertFalse(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertFalse(os.path.exists('/opt/raspiot/install/test.log'))
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/preuninst.sh'))
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/postuninst.sh'))
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)


class UninstallModuleTests(unittest.TestCase):

    def setUp(self):
        self.url_archive = 'https://github.com/tangb/cleep-os/raw/master/cleepos/tests/resources/installmodule/%s.zip'
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
        self.fs.enable_write()

    def tearDown(self):
        if os.path.exists('/tmp/preinst.tmp'):
            os.remove('/tmp/preinst.tmp')
        if os.path.exists('/tmp/postinst.tmp'):
            os.remove('/tmp/postinst.tmp')
        if os.path.exists('/tmp/preuninst.tmp'):
            os.remove('/tmp/preuninst.tmp')
        if os.path.exists('/tmp/postuninst.tmp'):
            os.remove('/tmp/postuninst.tmp')
        if os.path.exists('/opt/raspiot/install/test/test.log'):
            f = open('/opt/raspiot/install/test/test.log', 'r')
            lines = f.readlines()
            f.close()
            for line in lines:
                os.remove(line.strip())
            if os.path.exists('/opt/raspiot/install/test/'):
                shutil.rmtree('/opt/raspiot/install/test/', ignore_errors=True)
        if os.path.exists('/usr/lib/python2.7/dist-packages/raspiot/modules/test'):
            shutil.rmtree('/usr/lib/python2.7/dist-packages/raspiot/modules/test')
        if os.path.exists('/opt/raspiot/html/js/modules/test'):
            shutil.rmtree('/opt/raspiot/html/js/modules/test')

    def callback(self, status):
        pass

    def test_uninstall_ok(self):
        #install
        name = 'cleepmod_test_1.0.0.ok'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '5a522882b74f990ba0175808f52540bd1c1bcfe258873f83fc9e90e85d64a8f4'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/test.log'))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/preuninst.sh'))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/postuninst.sh'))

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
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/'))

    def test_uninstall_without_script_ok(self):
        #install
        name = 'cleepmod_test_1.0.0.noscript-ok'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '0b43bcff0e4dc88f4e24261913bd118cb53c9c9a82ab1a61b053477615421da7'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/test.log'))

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
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/test.log'))

    def test_uninstall_ko_preuninst(self):
        #install
        name = 'cleepmod_test_1.0.0.preuninst-ko'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '0565957885fb6438bfbeeb44e54f7ec66bb0144d196e9243bfd8e452b3e22853'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/test.log'))

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
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/test.log'))

    def test_uninstall_ko_postuninst(self):
        #install
        name = 'cleepmod_test_1.0.0.postuninst-ko'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '0b7a48ca0c39926915a22213fccc871064b5e8e5054e4095d0b9b4c14ce39493'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/test.log'))

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
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/'))

    def test_uninstall_ko_remove(self):
        #install
        name = 'cleepmod_test_1.0.0.postuninst-ko'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '0b7a48ca0c39926915a22213fccc871064b5e8e5054e4095d0b9b4c14ce39493'
        i = InstallModule('test', self.archive_infos, False, self.callback, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/test.log'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

        #remove installed file to simulate error
        os.remove('/opt/raspiot/install/test/test.log')

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
        self.assertFalse(os.path.exists('/opt/raspiot/install/test/'))




class UpdateModuleTests(unittest.TestCase):

    def setUp(self):
        self.url_archive = 'https://github.com/tangb/cleep-os/raw/master/cleepos/tests/resources/installmodule/%s.zip'
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
        #self.fs.enable_write()

    def tearDown(self):
        if os.path.exists('/tmp/preinst.tmp'):
            os.remove('/tmp/preinst.tmp')
        if os.path.exists('/tmp/postinst.tmp'):
            os.remove('/tmp/postinst.tmp')
        if os.path.exists('/tmp/preuninst.tmp'):
            os.remove('/tmp/preuninst.tmp')
        if os.path.exists('/tmp/postuninst.tmp'):
            os.remove('/tmp/postuninst.tmp')
        if os.path.exists('/opt/raspiot/install/test/test.log'):
            f = open('/opt/raspiot/install/test/test.log', 'r')
            lines = f.readlines()
            f.close()
            for line in lines:
                os.remove(line.strip())
            if os.path.exists('/opt/raspiot/install/test/'):
                shutil.rmtree('/opt/raspiot/install/test/')
        if os.path.exists('/usr/lib/python2.7/dist-packages/raspiot/modules/test'):
            shutil.rmtree('/usr/lib/python2.7/dist-packages/raspiot/modules/test')
        if os.path.exists('/opt/raspiot/html/js/modules/test'):
            shutil.rmtree('/opt/raspiot/html/js/modules/test')

    def callback(self, status):
        pass

    def test_update_ok(self):
        #install
        name = 'cleepmod_test_1.0.0.ok'
        self.archive_infos['download'] = self.url_archive % name
        self.archive_infos['sha256'] = '5a522882b74f990ba0175808f52540bd1c1bcfe258873f83fc9e90e85d64a8f4'
        i = InstallModule('test', self.archive_infos, False, None, self.fs)
        i.start()
        time.sleep(0.5)

        #wait until end of install
        while i.get_status()[u'status']==i.STATUS_INSTALLING:
            time.sleep(0.5)
        self.assertEqual(i.get_status()[u'status'], i.STATUS_INSTALLED)

        #check installation
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/desc.json')))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/test.log'))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/preuninst.sh'))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/postuninst.sh'))

        #make sure cleepfilesystem free everything
        time.sleep(1.0)

        #update module
        u = UpdateModule('test', self.archive_infos, self.callback, self.fs)
        u.start()
        time.sleep(0.5)

        #wait until end of update
        while u.get_status()[u'status']==u.STATUS_UPDATING:
            time.sleep(0.5)
        self.assertEqual(u.get_status()['status'], u.STATUS_UPDATED)

        #check update
        self.assertTrue(os.path.exists(os.path.join(PATH_FRONTEND, 'js/modules/test/')))
        self.assertTrue(os.path.exists('/opt/raspiot/install/test/'))

