#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from cmdlinetxt import CmdlineTxt
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.exception import MissingParameter, InvalidParameter, CommandError
from cleep.libs.tests.lib import TestLib, TRACE
import unittest
import logging
from pprint import pformat
import io

logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class CmdlineTxtTestAllDisabled(unittest.TestCase):

    FILE_NAME = 'cmdline.txt'
    BACKUP_FILENAME = 'cmdline.backup.txt'
    CONTENT = u'dwc_otg.lpm_enable=0 console=tty1 root=PARTUUID=c7cb7e34-02 rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait quiet fastboot noswap ro'
    #           dwc_otg.lpm_enable=0                                        rootfstype=ext4 fastboot rootwait quiet elevator=deadline fsck.repair=yes noswap ro root=PARTUUID=c7cb7e34-02

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        c = CmdlineTxt
        c.CONF = self.FILE_NAME
        self.c = c(self.fs)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)
        if os.path.exists('%s' % self.BACKUP_FILENAME):
            os.remove(self.BACKUP_FILENAME)

    def test_is_console_enabled(self):
        self.assertFalse(self.c.is_console_enabled(), 'Console should be disabled')

    def test_enable_console(self):
        self.assertTrue(self.c.enable_console(), 'Console not enabled')
        self.assertFalse(self.c.enable_console(), 'Console not already enabled')

    def test_disable_console(self):
        self.assertFalse(self.c.disable_console(), 'Console not disabled')
        self.c.enable_console()
        self.assertTrue(self.c.disable_console(), 'Console not disabled')

    def test_file_content(self):
        self.c.enable_console()
        with io.open(self.path, 'r') as f:
            content = f.read()
        logging.debug('Modified content: %s' % content)
        self.assertNotEqual(content.find('console'), -1, 'Console key not found')
        self.assertNotEqual(content.find('serial0,115200'), -1, 'Console value not found')

        self.c.disable_console()

        with io.open(self.path, 'r') as f:
            content = f.read()
        logging.debug('Original content: %s' % self.CONTENT)
        logging.debug('Altered content : %s' % content)

        self.assertEqual(self.CONTENT.strip(), content.strip(), 'File not properly written')




class CmdlineTxtTestAllEnabled(unittest.TestCase):

    FILE_NAME = 'cmdline.txt'
    BACKUP_FILENAME = 'cmdline.backup.txt'
    CONTENT = u'dwc_otg.lpm_enable=0 console=serial0,115200 console=tty1 root=PARTUUID=c7cb7e34-02 rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait quiet fastboot noswap ro'

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        c = CmdlineTxt
        c.CONF = self.FILE_NAME
        self.c = c(self.fs)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)
        if os.path.exists('%s' % self.BACKUP_FILENAME):
            os.remove(self.BACKUP_FILENAME)

    def test_is_console_enabled(self):
        self.assertTrue(self.c.is_console_enabled(), 'Console should be disabled')


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python*/*","*test_*.py" --concurrency=thread test_cmdlinetxt.py; coverage report -m -i
    unittest.main()

