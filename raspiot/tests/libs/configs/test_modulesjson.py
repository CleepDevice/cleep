#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys 
sys.path.append('/root/cleep/raspiot/libs/configs')
from modulesjson import ModulesJson
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.libs.internals.download import Download
from raspiot.exceptions import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pprint
import io
from mock import Mock
import json
import time

class ModulesJsonTests(unittest.TestCase):

    FILE_NAME = 'modules.json'

    def setUp(self):
      	TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        mj = ModulesJson
        mj.CONF = self.FILE_NAME
        self.mj = mj(self.fs)

        #fill with default content
        with io.open(self.FILE_NAME, 'w') as f:
            #python2 issue with json and unicode: https://stackoverflow.com/a/18337754
            content = json.dumps(self.mj.get_empty())
            f.write(unicode(content))

        #monkeypatch download class
        Download.download_file = Mock(return_value=u"""{"update": %d, "list": {}}""" % (int(time.time())+300))

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_exists_without_file(self):
        os.remove('%s' % self.FILE_NAME)
        #test file doesn't exist
        self.assertFalse(self.mj.exists())

    def test_exists_with_file(self):
        #update file first
        self.mj.update()
        #test file presence
        self.assertTrue(self.mj.exists())

    def test_update(self):
        #test update that returns True (local file updated)
        self.assertTrue(self.mj.update())

    def test_update_without_changes(self):
        #first update
        self.mj.update()
        #second update without changes
        self.assertFalse(self.mj.update())

    def test_update_with_different_timestamp(self):
        #update file
        self.mj.update()

        #change timestamp
        fd = io.open(self.mj.CONF, 'r')
        raw = fd.readlines()
        fd.close()
        modules_json = json.loads(u'\n'.join(raw))
        modules_json['update'] = modules_json['update'] - 1000
        fd = io.open(self.mj.CONF, 'w')
        fd.write(unicode(json.dumps(modules_json)))
        fd.close()

        #new update with update 
        self.assertTrue(self.mj.update())

    def test_update_with_invalid_remote_content(self):
        #monkeypatch download class
        Download.download_file = Mock(return_value=u"""{"update": %d, "modules": {}}""" % (int(time.time())+300))
        with self.assertRaises(Exception) as cm:
            self.mj.update()
        self.assertEqual(cm.exception.message, 'Remote "modules.json" file has invalid format')

    def test_get_json(self):
        #update file
        self.mj.update()
        #check get_json output
        content = self.mj.get_json()
        self.assertIsInstance(content, dict)
        self.assertTrue('list' in content)
        self.assertTrue('update' in content)

    def test_get_json_with_invalid_content(self):
        #update file
        self.mj.update()
        #test invalid file content raises exception
        fd = io.open(self.mj.CONF, u'w')
        fd.write(u'{}')
        fd.close()

        self.assertRaises(Exception, self.mj.get_json)

    def test_get_json_without_file(self):
        os.remove('%s' % self.FILE_NAME)
        with self.assertRaises(Exception) as cm:
            self.mj.get_json()
        self.assertEqual(cm.exception.message, 'File "modules.json" doesn\'t exist. Please update it first.')

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_modulesjson.py; coverage report -m
    unittest.main()
