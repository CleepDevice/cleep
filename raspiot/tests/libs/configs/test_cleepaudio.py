#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('/root/cleep/raspiot/libs/configs')
from cleepaudio import CleepAudio
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.utils import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pformat
import io

logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class CleepAudioTest(unittest.TestCase):

    FILE_NAME = 'cleep-audio.conf'
    CONTENT = u'blacklist mymodule\nblacklist a-module\nblacklist the_module'

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        c = CleepAudio
        c.CONF = self.FILE_NAME
        self.c = c(self.fs, False)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_is_module_blacklisted(self):
        self.assertTrue(self.c.is_module_blacklisted('mymodule'), 'mymodule is not blacklisted')
        self.assertTrue(self.c.is_module_blacklisted('a-module'), 'a-module is not blacklisted')
        self.assertTrue(self.c.is_module_blacklisted('the_module'), 'the_module is not blacklisted')
        self.assertFalse(self.c.is_module_blacklisted('test'), 'test is blacklisted')

    def test_blacklist_module(self):
        self.assertTrue(self.c.blacklist_module('new_module'), 'Module not blacklisted')
        self.assertTrue(self.c.is_module_blacklisted('new_module'), 'new_module should be blacklisted')

        self.assertTrue(self.c.blacklist_module('my-new-module'), 'Module not blacklisted')
        self.assertTrue(self.c.is_module_blacklisted('my-new-module'), 'my-new-module should be blacklisted')

    def test_blacklist_module_again(self):
        self.assertTrue(self.c.is_module_blacklisted('mymodule'), 'mymodule should be blacklisted')
        self.assertTrue(self.c.blacklist_module('my_module'), 'Module not blacklisted')
        self.assertTrue(self.c.is_module_blacklisted('mymodule'), 'mymodule should be blacklisted')

    def test_unblacklist_module(self):
        self.assertTrue(self.c.is_module_blacklisted('mymodule'), 'mymodule should be blacklisted')
        self.assertTrue(self.c.unblacklist_module('mymodule'), 'mymodule was not unblacklisted')
        self.assertFalse(self.c.is_module_blacklisted('mymodule'), 'mymodule should be unblacklisted')

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_cleepaudio.py
    #coverage report -m
    unittest.main()

