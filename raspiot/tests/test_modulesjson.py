#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.utils import InvalidParameter, MissingParameter
from raspiot.libs.modulesjson import ModulesJson
from raspiot.libs.cleepfilesystem import CleepFilesystem
import unittest
import os
import io
import json

class ModulesJsonTests(unittest.TestCase):

    def setUp(self):
        fs = CleepFilesystem()
        self.mj = ModulesJson(fs)
        self.mj.CONF = 'modules.local.json'

    def tearDown(self):
        if os.path.exists('modules.local.json'):
            os.remove('modules.local.json')

    def test_exists_without_file(self):
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
