#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from modulesjson import ModulesJson
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.exception import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pprint
import io
from unittest.mock import Mock, patch
import json
import time

class ModulesJsonTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def _init_context(self, download_mock=None, download_content_return_value=None, download_content_side_effect=None,
        read_json_return_value=None):
        default_json = json.dumps({'update': int(time.time()), 'list': {}})

        if download_mock:
            if not download_content_return_value:
                download_content_return_value = (0, default_json)
            if download_content_side_effect is None:
                download_mock.return_value.download_content.return_value = download_content_return_value
            else:
                download_mock.return_value.download_content.side_effect = download_content_side_effect

        self.cleep_filesystem = Mock()
        if read_json_return_value is None:
            read_json_return_value = default_json
        self.cleep_filesystem.read_json.return_value = read_json_return_value

        self.mj = ModulesJson(self.cleep_filesystem)

    def test_get_empty(self):
        self._init_context()

        empty = self.mj.get_empty()
        self.assertTrue('update' in empty)
        self.assertTrue('list' in empty)
        self.assertTrue(isinstance(empty['update'], int))
        self.assertTrue(isinstance(empty['list'], dict))

    @patch('os.path.exists')
    def test_get_json_exception_no_file(self, os_path_exists_mock):
        os_path_exists_mock.return_value = False
        self._init_context()

        with self.assertRaises(Exception) as cm:
            self.mj.get_json()
        self.assertEqual(str(cm.exception), 'File "modules.json" doesn\'t exist. Please update it first.')

    @patch('os.path.exists')
    def test_get_json_exception_invalid_content(self, os_path_exists_mock):
        os_path_exists_mock.return_value = True
        self._init_context(
            read_json_return_value={'update': (int(time.time())-1000), 'modules':{}}
        )

        with self.assertRaises(Exception) as cm:
            self.mj.get_json()
        self.assertEqual(str(cm.exception), 'Invalid "modules.json" file content')

    @patch('os.path.exists')
    def test_exists(self, os_path_exists_mock):
        self._init_context()

        os_path_exists_mock.return_value = True
        self.assertTrue(self.mj.exists())

        os_path_exists_mock.return_value = False
        self.assertFalse(self.mj.exists())

    @patch('modulesjson.Download')
    @patch('os.path.exists')
    def test_update_with_no_file(self, os_path_exists_mock, download_mock):
        os_path_exists_mock.return_value = False
        self._init_context(
            download_mock,
            download_content_return_value=(0, json.dumps({'update': int(time.time()), 'list':{}})),
        )

        # update
        self.assertTrue(self.mj.update())

    @patch('modulesjson.Download')
    @patch('os.path.exists')
    def test_update_without_changes(self, os_path_exists_mock, download_mock):
        os_path_exists_mock.return_value = True
        ts = int(time.time())
        self._init_context(
            download_mock,
            download_content_return_value=(0, json.dumps({'update': ts, 'list':{}})),
            read_json_return_value={'update': ts, 'list':{}}
        )

        # update
        self.assertFalse(self.mj.update())

    @patch('modulesjson.Download')
    @patch('os.path.exists')
    def test_update_with_different_timestamp(self, os_path_exists_mock, download_mock):
        os_path_exists_mock.return_value = True
        self._init_context(
            download_mock,
            download_content_return_value=(0, json.dumps({'update': (int(time.time())-500), 'list':{}})),
            read_json_return_value={'update': (int(time.time())-1000), 'list':{}}
        )

        # update
        self.assertTrue(self.mj.update())

    @patch('modulesjson.Download')
    def test_update_with_invalid_remote_content(self, download_mock):
        self._init_context(
            download_mock,
            download_content_return_value=(0, json.dumps({'update': (int(time.time())-500), 'modules':{}})),
        )

        with self.assertRaises(Exception) as cm:
            self.mj.update()
        self.assertEqual(str(cm.exception), 'Remote "modules.json" file has invalid format')

    @patch('modulesjson.Download')
    def test_update_with_download_failure(self, download_mock):
        self._init_context(
            download_mock,
            download_content_return_value=(3, None)
        )

        with self.assertRaises(Exception) as cm:
            self.mj.update()
        self.assertEqual(str(cm.exception), 'Download of modules.json failed (download status 3)')


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python*/*","*test_*.py" --concurrency=thread test_modulesjson.py; coverage report -m -i
    unittest.main()
