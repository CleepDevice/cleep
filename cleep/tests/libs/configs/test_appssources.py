#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from appssources import AppsSources
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.exception import MissingParameter, InvalidParameter, CommandError
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import Mock, patch, MagicMock
from cleep.libs.tests.common import get_log_level
from copy import deepcopy

LOG_LEVEL = get_log_level()

CUSTOM_SOURCE = {
    "filepath": "/opt/cleep/custom.json",
    "remote_url_version": "https://www.cleep.com/custom_%(version)s.json",
    "remote_url_latest": "https://www.cleep.com/custom.json",
}
INVALID_SOURCE_FIELD = {
    "filename": "/opt/cleep/custom.json",
    "remote_url_version": "https://www.cleep.com/custom_%(version)s.json",
    "remote_url_latest": "https://www.cleep.com/custom.json",
}
INVALID_SOURCE_VERSION = {
    "filepath": "/opt/cleep/custom.json",
    "remote_url_version": "https://www.cleep.com/custom_version.json",
    "remote_url_latest": "https://www.cleep.com/custom.json",
}
APPS_EMPTY = {
    "update": 1,
    "list": {},
}
APPS1 = {
    "update": 1,
    "list": {
        "app1": {},
    },
}
APPS2 = {
    "update": 2,
    "list": {
        "app2": {},
    },
}
APPS3 = {
    "update": 3,
    "list": {
        "app1": {},
        "app3": {},
    },
}
INVALID_SOURCES1 = {
    "list": {},
}
INVALID_SOURCES2 = {
    "sources": [
        {
            "filename": "dummy",
            "remote_url": "url",
        }
    ],
}
DEFAULT_SOURCES = [AppsSources.CLEEP_APPS_FREE, AppsSources.CLEEP_APPS_NON_FREE]

class AppsSourcesTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def _init_context(self, os_path_exists_mock, sources=DEFAULT_SOURCES):
        self.cleep_filesystem = Mock()
        self.cleep_filesystem.read_json.return_value = {
            "sources": sources
        }
        os_path_exists_mock.return_value = True

        self.l = AppsSources(self.cleep_filesystem)

    @patch('os.path.exists')
    def test_contructor_create_default_file(self, os_path_exists_mock):
        os_path_exists_mock.return_value = False
        cleep_filesystem = Mock()
        cleep_filesystem.read_json.return_value = {
            "sources": [CUSTOM_SOURCE]
        }
        cleep_filesystem.write_json.return_value = True

        AppsSources(cleep_filesystem)

        cleep_filesystem.write_json.assert_called_with(AppsSources.APP_SOURCES_PATH, {"sources": DEFAULT_SOURCES}, 'utf8')
        self.assertEqual(cleep_filesystem.read_json.call_count, 2)

    @patch('os.path.exists')
    def test_contructor_create_default_file_failed(self, os_path_exists_mock):
        os_path_exists_mock.return_value = False
        cleep_filesystem = Mock()
        cleep_filesystem.read_json.return_value = {
            "sources": [CUSTOM_SOURCE]
        }
        cleep_filesystem.write_json.return_value = False

        with patch('appssources.logging') as logging_mock:
            logger_mock = Mock()
            logging_mock.getLogger.return_value = logger_mock
            
            AppsSources(cleep_filesystem)
            
            logger_mock.exception.assert_called_with('Unable to create default apps.sources file')
            self.assertEqual(cleep_filesystem.write_json.call_count, 1)

    @patch('os.path.exists')
    def test_contructor_create_default_file_because_invalid_sources(self, os_path_exists_mock):
        os_path_exists_mock.return_value = True
        cleep_filesystem = Mock()
        cleep_filesystem.read_json.return_value = INVALID_SOURCES1

        with patch('appssources.logging') as logging_mock:
            logger_mock = Mock()
            logging_mock.getLogger.return_value = logger_mock
            
            AppsSources(cleep_filesystem)
            
            logger_mock.warning.assert_called_with('Invalid "apps.sources" content, generate default content')
            self.assertEqual(cleep_filesystem.write_json.call_count, 1)

    @patch('os.path.exists')
    def test_contructor_create_default_file_because_invalid_app_source(self, os_path_exists_mock):
        os_path_exists_mock.return_value = True
        cleep_filesystem = Mock()
        cleep_filesystem.read_json.return_value = INVALID_SOURCES2

        with patch('appssources.logging') as logging_mock:
            logger_mock = Mock()
            logging_mock.getLogger.return_value = logger_mock
            
            AppsSources(cleep_filesystem)
            
            logger_mock.warning.assert_called_with('Invalid "apps.sources" content, generate default content')
            self.assertEqual(cleep_filesystem.write_json.call_count, 1)

    @patch('os.path.exists')
    def test_get_sources_default_sources(self, os_path_exists_mock):
        self._init_context(os_path_exists_mock)

        sources = self.l.get_sources()
        logging.debug('sources: %s', sources)

        self.assertListEqual(sources, DEFAULT_SOURCES)

    @patch('os.path.exists')
    def test_get_sources_custom_sources(self, os_path_exists_mock):
        custom_sources = [AppsSources.CLEEP_APPS_FREE, AppsSources.CLEEP_APPS_NON_FREE, CUSTOM_SOURCE]
        self._init_context(os_path_exists_mock, custom_sources)

        sources = self.l.get_sources()
        logging.debug('sources: %s', sources)

        self.assertListEqual(sources, custom_sources)

    @patch('os.path.exists')
    def test_add_source(self, os_path_exists_mock):
        self._init_context(os_path_exists_mock)
        self.cleep_filesystem.read_json.return_value = {
            "sources": deepcopy(DEFAULT_SOURCES),
        }
        self.cleep_filesystem.write_json.return_value = True
        
        self.l.add_source(CUSTOM_SOURCE)

        self.cleep_filesystem.write_json.assert_called_with(AppsSources.APP_SOURCES_PATH, {
            "sources": [AppsSources.CLEEP_APPS_FREE, AppsSources.CLEEP_APPS_NON_FREE, CUSTOM_SOURCE],
        }, 'utf8')
        self.assertEqual(self.cleep_filesystem.read_json.call_count, 5)

    @patch('os.path.exists')
    def test_add_source_error_saving_file(self, os_path_exists_mock):
        self._init_context(os_path_exists_mock)
        self.cleep_filesystem.read_json.return_value = {
            "sources": deepcopy(DEFAULT_SOURCES),
        }
        self.cleep_filesystem.write_json.return_value = False
        
        with self.assertRaises(Exception) as cm:
            self.l.add_source(CUSTOM_SOURCE)
        self.assertEqual(str(cm.exception), 'Error saving new source')

    @patch('os.path.exists')
    def test_add_source_invalid_params(self, os_path_exists_mock):
        self._init_context(os_path_exists_mock)

        with self.assertRaises(MissingParameter) as cm:
            self.l.add_source(None)
        self.assertEqual(cm.exception.message, 'Parameter "source" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.l.add_source(INVALID_SOURCE_FIELD)
        self.assertEqual(cm.exception.message, 'Parameter "source" is invalid')

        with self.assertRaises(InvalidParameter) as cm:
            self.l.add_source(INVALID_SOURCE_VERSION)
        self.assertEqual(cm.exception.message, 'Parameter "source" field "remote_url_version" is invalid')

    @patch('os.path.exists')
    def test_delete_source(self, os_path_exists_mock):
        self._init_context(os_path_exists_mock)
        sources = deepcopy(DEFAULT_SOURCES)
        sources.append(CUSTOM_SOURCE)
        self.cleep_filesystem.read_json.return_value = {
            "sources": sources,
        }
        self.cleep_filesystem.write_json.return_value = True
        
        self.l.delete_source(CUSTOM_SOURCE["filepath"])

        self.cleep_filesystem.write_json.assert_called_with(AppsSources.APP_SOURCES_PATH, {
            "sources": [AppsSources.CLEEP_APPS_FREE, AppsSources.CLEEP_APPS_NON_FREE],
        }, 'utf8')
        self.assertEqual(self.cleep_filesystem.read_json.call_count, 5)

    @patch('os.path.exists')
    def test_delete_source_error_saving_file(self, os_path_exists_mock):
        self._init_context(os_path_exists_mock)
        sources = deepcopy(DEFAULT_SOURCES)
        sources.append(CUSTOM_SOURCE)
        self.cleep_filesystem.read_json.return_value = {
            "sources": sources,
        }
        self.cleep_filesystem.write_json.return_value = False
        
        with self.assertRaises(Exception) as cm:
            self.l.delete_source(CUSTOM_SOURCE["filepath"])
        self.assertEqual(str(cm.exception), 'Error saving new source')

    @patch('os.path.exists')
    def test_delete_source_invalid_params(self, os_path_exists_mock):
        self._init_context(os_path_exists_mock)

        with self.assertRaises(MissingParameter) as cm:
            self.l.delete_source(None)
        self.assertEqual(cm.exception.message, 'Parameter "source_filepath" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.l.delete_source(AppsSources.CLEEP_APPS_FREE["filepath"])
        self.assertEqual(cm.exception.message, 'Parameter "source_filepath" must not refer to a Cleep source')

    @patch('os.path.exists')
    def test_get_market_without_update(self, os_path_exists_mock):
        self._init_context(os_path_exists_mock)
        sources = deepcopy(DEFAULT_SOURCES)
        sources.append(CUSTOM_SOURCE)
        self.cleep_filesystem.read_json.return_value = {
            "sources": sources,
        }
        self.cleep_filesystem.write_json.return_value = True
        self.l.apps = deepcopy(APPS1)
        self.l.update = Mock()
        
        apps = self.l.get_market()
        logging.debug('apps: %s', apps)

        self.assertDictEqual(apps, APPS1)
        self.l.update.assert_not_called()

    @patch('os.path.exists')
    def test_get_market_with_update(self, os_path_exists_mock):
        self._init_context(os_path_exists_mock)
        sources = deepcopy(DEFAULT_SOURCES)
        sources.append(CUSTOM_SOURCE)
        self.cleep_filesystem.read_json.return_value = {
            "sources": sources,
        }
        self.cleep_filesystem.write_json.return_value = True
        self.l.apps = deepcopy(APPS1)
        self.l.apps["update"] = 0
        self.l.update_market = Mock()
        
        apps = self.l.get_market()
        logging.debug('apps: %s', apps)

        self.l.update_market.assert_called_with(force_update=False)

    @patch('os.path.exists')
    @patch('appssources.ModulesJson')
    def test_update_market_has_updates(self, modules_json_mock, os_path_exists_mock):
        modulesjson_mock = Mock()
        modules_json_mock.return_value = modulesjson_mock
        modulesjson_mock.exists.return_value = True
        modulesjson_mock.get_content.side_effect = [APPS1, APPS2]
        modulesjson_mock.update.return_value = True
        self._init_context(os_path_exists_mock)

        has_updates = self.l.update_market()
        logging.debug("Has updates: %s", has_updates)

        self.assertTrue(has_updates)
        self.assertEqual(modulesjson_mock.update.call_count, 2)

    @patch('os.path.exists')
    @patch('appssources.ModulesJson')
    def test_update_market_has_no_updates(self, modules_json_mock, os_path_exists_mock):
        modulesjson_mock = Mock()
        modules_json_mock.return_value = modulesjson_mock
        modulesjson_mock.exists.return_value = True
        modulesjson_mock.get_content.side_effect = [APPS1, APPS2, APPS1, APPS2]
        modulesjson_mock.update.side_effect = [True, True, False, False]
        self._init_context(os_path_exists_mock)

        has_updates = self.l.update_market()
        logging.debug("Has updates: %s", has_updates)
        has_updates = self.l.update_market()
        logging.debug("Has updates: %s", has_updates)

        self.assertFalse(has_updates)
        self.assertEqual(modulesjson_mock.update.call_count, 4)

    @patch('os.path.exists')
    @patch('appssources.ModulesJson')
    def test_update_market_available_updates(self, modules_json_mock, os_path_exists_mock):
        modulesjson_mock = Mock()
        modules_json_mock.return_value = modulesjson_mock
        modulesjson_mock.exists.return_value = True
        modulesjson_mock.get_content.side_effect = [APPS1, APPS2, APPS3, APPS2]
        modulesjson_mock.update.side_effect = [True, True, True, False]
        self._init_context(os_path_exists_mock)

        has_updates = self.l.update_market()
        logging.debug("Has updates: %s", has_updates)
        has_updates = self.l.update_market()
        logging.debug("Has updates: %s", has_updates)

        self.assertTrue(has_updates)
        self.assertDictEqual(self.l.apps, {"update": 3, "list": {"app1":{}, "app2":{}, "app3":{}}})
        self.assertEqual(modulesjson_mock.update.call_count, 4)

    @patch('os.path.exists')
    @patch('appssources.ModulesJson')
    def test_update_market_do_not_force_update(self, modules_json_mock, os_path_exists_mock):
        modulesjson_mock = Mock()
        modules_json_mock.return_value = modulesjson_mock
        modulesjson_mock.exists.return_value = True
        modulesjson_mock.get_content.side_effect = [APPS1, APPS2, APPS3, APPS2]
        modulesjson_mock.update.return_value = True
        self._init_context(os_path_exists_mock)

        has_updates = self.l.update_market()
        logging.debug("Has updates: %s", has_updates)
        has_updates = self.l.update_market(force_update=False)
        logging.debug("Has updates: %s", has_updates)

        self.assertEqual(modulesjson_mock.update.call_count, 2)

    @patch('os.path.exists')
    @patch('appssources.ModulesJson')
    def test_update_market_update_failure(self, modules_json_mock, os_path_exists_mock):
        modulesjson_mock = Mock()
        modules_json_mock.return_value = modulesjson_mock
        modulesjson_mock.exists.return_value = True
        modulesjson_mock.get_content.side_effect = [APPS1, APPS2, APPS3, APPS2]
        modulesjson_mock.update.side_effect = Exception('Test exception')
        modulesjson_mock.get_empty.return_value = APPS_EMPTY
        self._init_context(os_path_exists_mock)

        has_updates = self.l.update_market()

        self.assertEqual(modulesjson_mock.update.call_count, 2)



if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_appssources.py; coverage report -m -i
    unittest.main()

