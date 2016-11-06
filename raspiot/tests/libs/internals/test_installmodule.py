#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('%s/../../../libs/internals' % os.getcwd())
from installmodule import InstallModule, UninstallModule, UpdateModule, Download
import raspiot.libs.internals.download
from raspiot.libs.internals.installdeb import InstallDeb
from raspiot.libs.tests.lib import TestLib
from raspiot.exception import MissingParameter, InvalidParameter
import unittest
import logging
import time
from mock import Mock, patch
import subprocess
import tempfile
from threading import Timer


class InstallModuleTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.TRACE, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def callback(self, status):
        logging.debug('Received status: %s' % status)

    def _init_context(self, download_mock, module_name, module_infos, update_process=False):
        self.crash_report = Mock()
        self.cleep_filesystem = Mock()

        download_mock.return_value.download_file.return_value = '/tmp/dummy'

        self.i = InstallModule(module_name, module_infos, update_process, self.callback, self.cleep_filesystem, self.crash_report)

    def _get_module_infos(self):
        return {
            "category": "APPLICATION",
            "description": "description",
            "tags": ["tag1", "tag2"],
            "country": None,
            "price": 0,
            "author": "Cleep",
            "changelog": "First official release",
            "deps": [],
            "longdescription": "long description",
            "version": "1.0.0",
            "urls": {
                "info": None,
                "bugs": None,
                "site": None,
                "help": None
            },
            "icon": "icon",
            "certified": True,
            "note": -1,
            "download": "https://www.google.com",
            "sha256": "f5723bae112c217f6b1be26445ce5ffda9ad7701276bcb1ea1ae9bc7232e1926"
        }

    @patch('installmodule.Download')
    def test_install(self, download_mock):
        module_infos = self._get_module_infos()
        self._init_context(download_mock, 'module', module_infos)

        self.i.run()
        while self.i.is_installing():
            time.sleep(0.25)
        status = self.i.get_status()
        logging.debug('Status: %s' % status)

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_installmodule.py; coverage report -i -m
    unittest.main()

