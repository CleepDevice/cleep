#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from modulesjson import ModulesJson
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.exception import MissingParameter, InvalidParameter, CommandError
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pprint
import io
from unittest.mock import Mock, patch, MagicMock
import json
import time
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()

CUSTOM_MODULES_JSON = {
    "filepath": "/opt/cleep/custom.json",
    "remote_url_version": "https://www.cleep.com/custom_version.json",
    "remote_url_latest": "https://www.cleep.com/custom.json",
}

class ModulesJsonTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def _init_context(self, download_mock=None, download_content_return_value=None, download_content_side_effect=None,
        read_json_return_value=None, custom_file=None):
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

        self.mj = ModulesJson(self.cleep_filesystem, custom_file)

    def test_constructor_valid_custom_file(self):
        self._init_context(custom_file=CUSTOM_MODULES_JSON)

        self.assertDictEqual(self.mj.modulesjson, CUSTOM_MODULES_JSON)

    def test_constructor_invalid_custom_file(self):
        self._init_context(custom_file='dummy.json')
        logging.debug('modulesjson: %s', self.mj.modulesjson)
        logging.debug('default modulesjson: %s', ModulesJson.DEFAULT_MODULES_JSON)

        self.assertDictEqual(self.mj.modulesjson, ModulesJson.DEFAULT_MODULES_JSON)

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
        self.assertEqual(str(cm.exception), 'File "/etc/cleep/modules.json" doesn\'t exist. Please update it first.')

    @patch('os.path.exists')
    def test_get_json_exception_invalid_content(self, os_path_exists_mock):
        os_path_exists_mock.return_value = True
        self._init_context(
            read_json_return_value={'update': (int(time.time())-1000), 'dummy':{}}
        )

        with self.assertRaises(Exception) as cm:
            self.mj.get_json()
        self.assertEqual(str(cm.exception), 'Invalid "/etc/cleep/modules.json" file content')

    @patch('os.path.exists')
    def test_get_json_custom_file(self, os_path_exists_mock):
        os_path_exists_mock.return_value = True
        self._init_context(
            read_json_return_value={'update': (int(time.time())-1000), 'list':{}},
            custom_file=CUSTOM_MODULES_JSON
        )

        self.mj.get_json()

        self.cleep_filesystem.read_json.assert_called_with(CUSTOM_MODULES_JSON['filepath'])

    @patch('os.path.exists')
    def test_exists(self, os_path_exists_mock):
        self._init_context()

        os_path_exists_mock.return_value = True
        self.assertTrue(self.mj.exists())

        os_path_exists_mock.return_value = False
        self.assertFalse(self.mj.exists())

    @patch('os.path.exists')
    def test_exists_custom_file(self, os_path_exists_mock):
        self._init_context(custom_file=CUSTOM_MODULES_JSON)

        os_path_exists_mock.return_value = True
        self.assertTrue(self.mj.exists())

        os_path_exists_mock.return_value = False
        self.assertFalse(self.mj.exists())

    @patch('modulesjson.requests')
    @patch('modulesjson.CLEEP_VERSION', '0.0.666')
    def test_get_remote_url_return_version_url(self, requests_mock):
        geturl_mock = MagicMock()
        geturl_mock.status_code = 200
        requests_mock.get.return_value = geturl_mock
        self._init_context(
            read_json_return_value={'update': (int(time.time())-1000), 'list':{}}
        )
    
        url = self.mj._ModulesJson__get_remote_url()
        self.assertEqual(url, self.mj.DEFAULT_MODULES_JSON["remote_url_version"] % {'version': '0.0.666'})

    @patch('modulesjson.requests')
    @patch('modulesjson.CLEEP_VERSION', '0.0.666')
    def test_get_remote_url_return_latest_url(self, requests_mock):
        geturl_mock = MagicMock()
        geturl_mock.status_code = 404
        requests_mock.get.return_value = geturl_mock
        self._init_context(
            read_json_return_value={'update': (int(time.time())-1000), 'list':{}}
        )
    
        url = self.mj._ModulesJson__get_remote_url()
        self.assertEqual(url, self.mj.DEFAULT_MODULES_JSON["remote_url_latest"])

    @patch('modulesjson.requests')
    @patch('modulesjson.CLEEP_VERSION', '0.0.666')
    def test_get_remote_url_exception_should_return_latest_url(self, requests_mock):
        requests_mock.urlopen.side_effect = Exception('Test exception')
        self._init_context(
            read_json_return_value={'update': (int(time.time())-1000), 'list':{}}
        )
    
        url = self.mj._ModulesJson__get_remote_url()
        self.assertEqual(url, self.mj.DEFAULT_MODULES_JSON["remote_url_latest"])

    @patch('modulesjson.requests')
    @patch('modulesjson.CLEEP_VERSION', '0.0.666')
    def test_get_remote_url_custom_file(self, requests_mock):
        geturl_mock = MagicMock()
        geturl_mock.status_code = 200
        requests_mock.get.return_value = geturl_mock
        self._init_context(
            read_json_return_value={'update': (int(time.time())-1000), 'list':{}},
            custom_file=CUSTOM_MODULES_JSON
        )
    
        url = self.mj._ModulesJson__get_remote_url()

        requests_mock.get.assert_called_with(CUSTOM_MODULES_JSON['remote_url_version'])

    @patch('modulesjson.requests')
    @patch('modulesjson.CLEEP_VERSION', '0.0.666')
    def test_get_remote_url_custom_file_should_return_latest_url(self, requests_mock):
        requests_mock.urlopen.side_effect = Exception('Test exception')
        self._init_context(
            read_json_return_value={'update': (int(time.time())-1000), 'list':{}},
            custom_file=CUSTOM_MODULES_JSON
        )
    
        url = self.mj._ModulesJson__get_remote_url()

        self.assertEqual(url, CUSTOM_MODULES_JSON['remote_url_latest'])

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
    @patch('modulesjson.requests')
    def test_update_without_changes(self, requests_mock, os_path_exists_mock, download_mock):
        geturl_mock = MagicMock()
        geturl_mock.status_code = 200
        requests_mock.get.return_value = geturl_mock
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
    @patch('modulesjson.requests')
    def test_update_with_different_timestamp(self, requests_mock, os_path_exists_mock, download_mock):
        geturl_mock = MagicMock()
        geturl_mock.status_code = 200
        requests_mock.get.return_value = geturl_mock
        os_path_exists_mock.return_value = True
        self._init_context(
            download_mock,
            download_content_return_value=(0, json.dumps({'update': (int(time.time())-500), 'list':{}})),
            read_json_return_value={'update': (int(time.time())-1000), 'list':{}}
        )

        # update
        self.assertTrue(self.mj.update())

    @patch('modulesjson.Download')
    @patch('modulesjson.requests')
    def test_update_with_invalid_remote_content(self, requests_mock, download_mock):
        geturl_mock = MagicMock()
        geturl_mock.status_code = 200
        requests_mock.get.return_value = geturl_mock
        self._init_context(
            download_mock,
            download_content_return_value=(0, json.dumps({'update': (int(time.time())-500), 'dummy':{}})),
        )

        with self.assertRaises(Exception) as cm:
            self.mj.update()
        self.assertEqual(str(cm.exception), 'Remote "/etc/cleep/modules.json" file has invalid format')

    @patch('modulesjson.Download')
    @patch('modulesjson.requests')
    def test_update_with_download_failure(self, requests_mock, download_mock):
        geturl_mock = MagicMock()
        geturl_mock.status_code = 200
        requests_mock.get.return_value = geturl_mock
        self._init_context(
            download_mock,
            download_content_return_value=(3, None)
        )

        with self.assertRaises(Exception) as cm:
            self.mj.update()
        self.assertEqual(str(cm.exception), 'Download of "/etc/cleep/modules.json" failed (download status 3)')


if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_modulesjson.py; coverage report -m -i
    unittest.main()

