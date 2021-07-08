#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from cleepwificonf import CleepWifiConf
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.exception import MissingParameter, InvalidParameter, CommandError
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pformat
import io
import json
import time


class CleepWifiConfTest(unittest.TestCase):

    FILE_NAME = 'cleepwifi.conf'
    CONTENT = u"""{
    "network": "mynetwork",
    "password": "mypassword",
    "encryption": "wpa2",
    "hidden": "true"
}"""

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

        self.fs = CleepFilesystem()
        self.fs.enable_write()
        # self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        self.path = os.path.join('/tmp', self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        c = CleepWifiConf
        # c.CONF = self.FILE_NAME
        c.CONF = self.path
        self.c = c()

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_exists(self):
        self.assertTrue(self.c.exists(), 'Conf file should exists')

    def test_exists_file_not_found(self):
        os.remove(self.path)
        self.assertFalse(self.c.exists(), 'Conf file should not exists')

    def test_get_configuration(self):
        config = self.c.get_configuration()
        self.assertTrue('network' in config, 'Missing field')
        self.assertTrue('password' in config, 'Missing field')
        self.assertTrue('encryption' in config, 'Missing field')
        self.assertTrue('hidden' in config, 'Missing field')

    def test_get_configuration_file_not_exists(self):
        os.remove(self.path)
        self.assertIsNone(self.c.get_configuration(), 'Config should returns None if no file found')

    def test_delete(self):
        self.assertTrue(self.c.delete(self.fs), 'config file should be deleted')
        self.assertFalse(os.path.exists(self.c.CONF), 'config file should already be deleted')

    def test_create_content(self):
        string = self.c.create_content('thenetwork', 'thepassword', 'wpa2', False)
        self.assertEqual(type(string), str, 'Returned content as invalid type')

        parsed = json.loads(string)
        self.assertTrue('network' in parsed, 'Missing field')
        self.assertTrue('password' in parsed, 'Missing field')
        self.assertTrue('encryption' in parsed, 'Missing field')
        self.assertTrue('hidden' in parsed, 'Missing field')
        self.assertEqual(parsed['network'], 'thenetwork')
        self.assertNotEqual(parsed['password'], 'thepassword')
        self.assertEqual(parsed['encryption'], 'wpa2')
        self.assertEqual(parsed['hidden'], False)

    def test_create_content_password_encrypted(self):
        string = self.c.create_content('thenetwork', 'thepassword', 'wpa2', False)
        parsed = json.loads(string)
        self.assertNotEqual(parsed['password'], 'thepassword')

        string = self.c.create_content('thenetwork', 'thepassword', 'wpa', False)
        parsed = json.loads(string)
        self.assertNotEqual(parsed['password'], 'thepassword')

        string = self.c.create_content('thenetwork', 'thepassword', 'wep', False)
        parsed = json.loads(string)
        self.assertEqual(parsed['password'], 'thepassword')

        string = self.c.create_content('thenetwork', 'thepassword', 'unsecured', False)
        parsed = json.loads(string)
        self.assertEqual(parsed['password'], 'thepassword')

    def test_create_content_invalid_encryption(self):
        string = self.c.create_content('thenetwork', 'thepassword', 'test', False)
        parsed = json.loads(string)
        self.assertEqual(parsed['encryption'], 'wpa2', 'Invalid default encryption')

if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_cleepwificonf.py; coverage report -m -i
    unittest.main()

