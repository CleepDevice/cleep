#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.tests.lib import TestLib
import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from modulesjson import ModulesJson
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.exception import MissingParameter, InvalidParameter, CommandError
import unittest
import logging
from pprint import pprint
import io
from unittest.mock import Mock, patch, MagicMock
import json
import time
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


CUSTOM_SOURCE = {
    "filename": "custom.json",
    "remote_url_version": "https://www.cleep.com/custom_version.json",
    "remote_url_latest": "https://www.cleep.com/custom.json",
}
DEFAULT_SOURCE = {
    "filename": "test.json",
    "remote_url_version": "https://www.cleep.com/cleep.%(version)s.json",
    "remote_url_latest": "https://www.cleep.com/cleep.latest.json",
}
SOURCES_PATH = '/tmp/sources'

class ModulesJsonTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def _init_context(self, download_mock=None, download_content_return_value=None, download_content_side_effect=None,
        read_json_return_value=None, custom_source=DEFAULT_SOURCE):
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
        self.task_factory = Mock()

        self.mj = ModulesJson(self.cleep_filesystem, self.task_factory, SOURCES_PATH, custom_source)

    def test_constructor_valid_custom_source(self):
        self._init_context(custom_source=CUSTOM_SOURCE)

        self.assertDictEqual(self.mj.source, CUSTOM_SOURCE)

    def test_get_source_filepath(self):
        self._init_context()

        filepath = self.mj.get_source_filepath()
        logging.debug('Filepath: %s', filepath)

        self.assertEqual(filepath, os.path.join(SOURCES_PATH, DEFAULT_SOURCE["filename"]))

    def test_get_empty(self):
        self._init_context()

        empty = self.mj.get_empty()
        self.assertTrue('update' in empty)
        self.assertTrue('list' in empty)
        self.assertTrue(isinstance(empty['update'], int))
        self.assertTrue(isinstance(empty['list'], dict))

    @patch('os.path.exists')
    def test_get_content_exception_no_file(self, os_path_exists_mock):
        os_path_exists_mock.return_value = False
        self._init_context()

        with self.assertRaises(Exception) as cm:
            self.mj.get_content()
        self.assertEqual(str(cm.exception), 'File "/tmp/sources/test.json" doesn\'t exist. Please update it first.')

    @patch('os.path.exists')
    def test_get_content_exception_invalid_content(self, os_path_exists_mock):
        os_path_exists_mock.return_value = True
        self._init_context(
            read_json_return_value={'update': (int(time.time())-1000), 'dummy':{}}
        )

        with self.assertRaises(Exception) as cm:
            self.mj.get_content()
        self.assertEqual(str(cm.exception), 'Invalid "/tmp/sources/test.json" file content')

    @patch('os.path.exists')
    def test_get_content_custom_source(self, os_path_exists_mock):
        os_path_exists_mock.return_value = True
        self._init_context(
            read_json_return_value={'update': (int(time.time())-1000), 'list':{}},
            custom_source=CUSTOM_SOURCE
        )
        source_path = os.path.join(SOURCES_PATH, CUSTOM_SOURCE['filename'])

        self.mj.get_content()

        self.cleep_filesystem.read_json.assert_called_with(source_path, 'utf8')

    @patch('os.path.exists')
    def test_exists(self, os_path_exists_mock):
        self._init_context()

        os_path_exists_mock.return_value = True
        self.assertTrue(self.mj.exists())

        os_path_exists_mock.return_value = False
        self.assertFalse(self.mj.exists())

    @patch('os.path.exists')
    def test_exists_custom_source(self, os_path_exists_mock):
        self._init_context(custom_source=CUSTOM_SOURCE)

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
        self.assertEqual(url, DEFAULT_SOURCE["remote_url_version"] % {'version': '0.0.666'})

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
        self.assertEqual(url, DEFAULT_SOURCE["remote_url_latest"])

    @patch('modulesjson.requests')
    @patch('modulesjson.CLEEP_VERSION', '0.0.666')
    def test_get_remote_url_exception_should_return_latest_url(self, requests_mock):
        requests_mock.urlopen.side_effect = Exception('Test exception')
        self._init_context(
            read_json_return_value={'update': (int(time.time())-1000), 'list':{}}
        )
    
        url = self.mj._ModulesJson__get_remote_url()
        self.assertEqual(url, DEFAULT_SOURCE["remote_url_latest"])

    @patch('modulesjson.requests')
    @patch('modulesjson.CLEEP_VERSION', '0.0.666')
    def test_get_remote_url_custom_source(self, requests_mock):
        geturl_mock = MagicMock()
        geturl_mock.status_code = 200
        requests_mock.get.return_value = geturl_mock
        self._init_context(
            read_json_return_value={'update': (int(time.time())-1000), 'list':{}},
            custom_source=CUSTOM_SOURCE
        )
    
        url = self.mj._ModulesJson__get_remote_url()

        requests_mock.get.assert_called_with(CUSTOM_SOURCE['remote_url_version'])

    @patch('modulesjson.requests')
    @patch('modulesjson.CLEEP_VERSION', '0.0.666')
    def test_get_remote_url_custom_source_should_return_latest_url(self, requests_mock):
        requests_mock.urlopen.side_effect = Exception('Test exception')
        self._init_context(
            read_json_return_value={'update': (int(time.time())-1000), 'list':{}},
            custom_source=CUSTOM_SOURCE
        )
    
        url = self.mj._ModulesJson__get_remote_url()

        self.assertEqual(url, CUSTOM_SOURCE['remote_url_latest'])

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
        self.assertEqual(str(cm.exception), 'Remote "/tmp/sources/test.json" file has invalid format')

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
        self.assertEqual(str(cm.exception), 'Download of "/tmp/sources/test.json" failed (download status 3)')

    def test_update_invalid_source_str_instead_of_dict(self):
        custom_source = "dummy.json"
        self._init_context(custom_source=custom_source)

        with self.assertRaises(Exception) as cm:
            self.mj.update()
        self.assertEqual(str(cm.exception), 'Source is invalid: %s' % custom_source)

    def test_update_invalid_source_missing_key(self):
        custom_source = {
            "filename": "something",
            "remote_url_latest": "https://something",
        }
        self._init_context(custom_source=custom_source)

        with self.assertRaises(Exception) as cm:
            self.mj.update()
        self.assertEqual(str(cm.exception), 'Source is invalid: %s' % custom_source)

    def test_update_invalid_source_no_version_pattern(self):
        custom_source = {
            "filename": "something",
            "remote_url_latest": "https://something",
            "remote_url_version": "https://something",
        }
        self._init_context(custom_source=custom_source)

        with self.assertRaises(Exception) as cm:
            self.mj.update()
        self.assertEqual(str(cm.exception), 'Source is invalid: %s' % custom_source)


if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_modulesjson.py; coverage report -m -i
    unittest.main()

