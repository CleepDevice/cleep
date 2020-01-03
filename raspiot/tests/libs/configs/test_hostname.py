#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys 
sys.path.append('/root/cleep/raspiot/libs/configs')
from hostname import Hostname
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.utils import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pprint
import io
from mock import Mock


class HostnameTests(unittest.TestCase):

    FILE_NAME = 'hostname'
    CONTENT = u"""myraspi"""

    def setUp(self):
      	TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')
        
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        h = Hostname
        h.CONF = self.FILE_NAME
        self.h = h(self.fs, False)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_get_hostname(self):
        self.assertEqual(self.h.get_hostname(), 'myraspi')

    def test_set_hostname(self):
        self.assertTrue(self.h.set_hostname('helloworld'))
        self.assertEqual(self.h.get_hostname(), 'helloworld')

    def test_set_hostname_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.h.set_hostname(None)
        self.assertEqual(cm.exception.message, 'Parameter "hostname" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.h.set_hostname('')
        self.assertEqual(cm.exception.message, 'Parameter "hostname" is missing')

    def test_set_hostname_invalid_file(self):
        self.h.cleep_filesystem = Mock()
        self.h.cleep_filesystem.open.side_effect = Exception
        self.assertFalse(self.h.set_hostname('helloworld'))

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_hostname.py
    #coverage report -m
    unittest.main()
