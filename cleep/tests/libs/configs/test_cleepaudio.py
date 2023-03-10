#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from cleepaudio import CleepAudio
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.exception import MissingParameter, InvalidParameter, CommandError
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pformat
import io
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class CleepAudioTest(unittest.TestCase):

    FILE_NAME = 'cleep-audio.conf'
    CONTENT = u'blacklist mymodule\nblacklist a-module\nblacklist the_module'

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

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
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_cleepaudio.py; coverage report -m -i
    unittest.main()

