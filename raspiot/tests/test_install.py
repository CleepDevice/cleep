#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.install import Install
from raspiot.libs.console import Console
import unittest
import os
import time
import logging
import shutil

logging.basicConfig(level=logging.INFO, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class InstallTests(unittest.TestCase):
    """
    Install tests
    """

    def setUp(self):
        self.running = True
        self.deb = None
        self.status = Install.STATUS_IDLE
        self.stdout = []
        self.stderr = []
        self.i = Install(self.callback)
        self.archive = None
        self.directory = None

    def tearDown(self):
        #remove files
        if self.deb:
            os.remove(self.deb)
        if self.archive:
            os.remove(self.archive)

        #remove directories
        if self.directory:
            shutil.rmtree(self.directory)

    def callback(self, status):
        if status[u'status']==Install.STATUS_ERROR or status[u'status']==Install.STATUS_DONE:
            self.running = False
            self.status = status[u'status']
            self.stdout = status[u'stdout']
            self.stderr = status[u'stderr']

    def test_install_deb(self):
        self.running = True

        #download package that will be installed
        c = Console()
        c.command(u'aptitude download dhex', 60)
        self.deb = None
        for root, dirs, files in os.walk(u'.'):
            for file in files:
                if file.startswith(u'dhex') and file.endswith(u'.deb'):
                    self.deb = os.path.join(root, file)
                    break
        self.assertIsNotNone(self.deb)

        #process install
        self.i.install_deb(self.deb)
        while self.running:
            time.sleep(0.5)

        self.assertEqual(Install.STATUS_DONE, self.status)
        self.assertEqual(0, len(self.stderr))
        self.assertNotEqual(0, len(self.stdout))

    def test_refresh_packages(self):
        self.running = True

        #process refresh
        self.i.refresh_packages()
        while self.running:
            time.sleep(0.5)

        self.assertEqual(Install.STATUS_DONE, self.status)

    def test_already_running(self):
        self.running = True

        #process refresh
        self.i.refresh_packages()
            
        #launch again new process
        self.assertRaises(Exception, self.i.refresh_packages)

        #wait end of first process
        while self.running:
            time.sleep(0.5)

    def test_cancel(self):
        self.running = True

        #process refresh
        self.i.refresh_packages()
        time.sleep(2.0)
        status = self.i.get_status()
        self.assertEqual(Install.STATUS_PROCESSING, status['status'])

        self.i.cancel()
        status = self.i.get_status()
        self.assertEqual(Install.STATUS_CANCELED, status['status'])

    def test_install_package(self):
        self.running = True

        #process install
        self.i.install_package('dhex')
        while self.running:
            time.sleep(0.5)

        self.assertEqual(Install.STATUS_DONE, self.status)
        self.assertEqual(0, len(self.stderr))
        self.assertNotEqual(0, len(self.stdout))

        c = Console()
        res = c.command('dpkg -l | grep dhex')
        self.assertFalse(res['error'])
        self.assertTrue(res['stdout'][0].strip().startswith('ii'))

    def test_uninstall_package(self):
        self.running = True

        #process uninstall
        self.i.uninstall_package('dhex')
        while self.running:
            time.sleep(0.5)
        
        self.assertEqual(Install.STATUS_DONE, self.status)
        self.assertEqual(0, len(self.stderr))
        self.assertNotEqual(0, len(self.stdout))

        c = Console()
        res = c.command('dpkg -l | grep dhex')
        self.assertFalse(res['error'])
        self.assertNotEqual(0, len(res['stdout']))
        self.assertTrue(res['stdout'][0].strip().startswith('rc'))

    def test_uninstall_package_purge(self):
        self.running = True

        #process uninstall
        self.i.uninstall_package('dhex', purge=True)
        while self.running:
            time.sleep(0.5)
        
        self.assertEqual(Install.STATUS_DONE, self.status)
        self.assertEqual(0, len(self.stderr))
        self.assertNotEqual(0, len(self.stdout))

        c = Console()
        res = c.command('dpkg -l | grep dhex')
        self.assertFalse(res['error'])
        self.assertEqual(0, len(res['stdout']))
        self.assertEqual(0, len(res['stderr']))

    def test_install_archive_invalid_archive(self):
        self.running = True

        #process install
        self.assertRaises(Exception, self.i.install_archive, 'dummy_archive.tar.gz', '.')

    def test_install_archive_invalid_format(self):
        self.running = True

        self.archive = 'dummy_archive.7z'
        f = open(self.archive, 'w')
        f.write('dummy')
        f.close()
        time.sleep(.5)

        #process install
        self.assertRaises(Exception, self.i.install_archive, self.archive, '.')

    def test_install_archive(self):
        self.running = True

        self.archive = 'dummy_archive.tar.gz'
        self.directory = '/tmp/test_install'
        c = Console()
        res = c.command('tar czvf "%s" test*.py' % self.archive)
        self.assertFalse(res['error'])

        #process install
        self.i.install_archive(self.archive, self.directory)
        while self.running:
            time.sleep(0.5)

        self.assertEqual(Install.STATUS_DONE, self.status)
        self.assertEqual(0, len(self.stderr))
        self.assertTrue(os.path.exists(self.directory))
        path, dirs, files = os.walk(self.directory).next()
        self.assertNotEqual(0, len(files))
        

class InstallBlockingTests(unittest.TestCase):
    """
    Install tests with blocking mode enabled
    """

    def setUp(self):
        self.deb = None
        self.status = Install.STATUS_IDLE
        self.stdout = []
        self.stderr = []
        self.i = Install(self.callback, blocking=True)
        self.archive = None
        self.directory = None

    def tearDown(self):
        #remove files
        if self.deb:
            os.remove(self.deb)
        if self.archive:
            os.remove(self.archive)

        #remove directories
        if self.directory:
            shutil.rmtree(self.directory)

    def callback(self, status):
        if status[u'status']==Install.STATUS_ERROR or status[u'status']==Install.STATUS_DONE:
            self.status = status[u'status']
            self.stdout = status[u'stdout']
            self.stderr = status[u'stderr']

    def test_install_deb(self):
        self.running = True

        #download package that will be installed
        c = Console()
        c.command(u'aptitude download dhex', 60)
        self.deb = None
        for root, dirs, files in os.walk(u'.'):
            for file in files:
                if file.startswith(u'dhex') and file.endswith(u'.deb'):
                    self.deb = os.path.join(root, file)
                    break
        self.assertIsNotNone(self.deb)

        #process install
        res = self.i.install_deb(self.deb)
        self.assertTrue(res)
        self.assertEqual(Install.STATUS_DONE, self.status)
        self.assertEqual(0, len(self.stderr))
        self.assertNotEqual(0, len(self.stdout))

    def test_refresh_packages(self):
        self.running = True

        #process refresh
        res = self.i.refresh_packages()
        self.assertTrue(res)
        self.assertEqual(Install.STATUS_DONE, self.status)

    def test_install_package(self):
        self.running = True

        #process install
        res = self.i.install_package('dhex')
        self.assertTrue(res)
        self.assertEqual(Install.STATUS_DONE, self.status)
        self.assertEqual(0, len(self.stderr))
        self.assertNotEqual(0, len(self.stdout))

        c = Console()
        res = c.command('dpkg -l | grep dhex')
        self.assertFalse(res['error'])
        self.assertTrue(res['stdout'][0].strip().startswith('ii'))

    def test_uninstall_package(self):
        self.running = True

        #process uninstall
        res = self.i.uninstall_package('dhex')
        self.assertTrue(res)
        self.assertEqual(Install.STATUS_DONE, self.status)
        self.assertEqual(0, len(self.stderr))
        self.assertNotEqual(0, len(self.stdout))

        c = Console()
        res = c.command('dpkg -l | grep dhex')
        self.assertFalse(res['error'])
        self.assertNotEqual(0, len(res['stdout']))
        self.assertTrue(res['stdout'][0].strip().startswith('rc'))

    def test_uninstall_package_purge(self):
        self.running = True

        #process uninstall
        res = self.i.uninstall_package('dhex', purge=True)
        self.assertTrue(res)
        self.assertEqual(Install.STATUS_DONE, self.status)
        self.assertEqual(0, len(self.stderr))
        self.assertNotEqual(0, len(self.stdout))

        c = Console()
        res = c.command('dpkg -l | grep dhex')
        self.assertFalse(res['error'])
        self.assertEqual(0, len(res['stdout']))
        self.assertEqual(0, len(res['stderr']))

    def test_install_archive(self):
        self.running = True

        self.archive = 'dummy_archive.tar.gz'
        self.directory = '/tmp/test_install'
        c = Console()
        res = c.command('tar czvf "%s" test*.py' % self.archive)
        self.assertFalse(res['error'])

        #process install
        res = self.i.install_archive(self.archive, self.directory)
        self.assertTrue(res)
        self.assertEqual(Install.STATUS_DONE, self.status)
        self.assertEqual(0, len(self.stderr))
        self.assertTrue(os.path.exists(self.directory))
        path, dirs, files = os.walk(self.directory).next()
        self.assertNotEqual(0, len(files))
