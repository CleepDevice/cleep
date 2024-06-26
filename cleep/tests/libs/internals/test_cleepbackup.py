#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from cleepbackup import CleepBackup
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import Mock
import subprocess
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class CleepBackupTests(unittest.TestCase):

    CLEEP_PATH = '/tmp/etc/cleep'
    FILENAMES = ['test1.json', 'test2.txt']

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.crash_report = Mock()
        self.fs = Mock()

        if not os.path.exists(self.CLEEP_PATH):
            os.makedirs(self.CLEEP_PATH)

        for filename in self.FILENAMES:
            open(os.path.join(self.CLEEP_PATH, filename), 'a').close()

        self.c = CleepBackup(self.fs, self.crash_report)
        self.c.CLEEP_PATH = self.CLEEP_PATH

    def tearDown(self):
        for filename in self.FILENAMES:
            try:
                os.remove(os.path.join(self.CLEEP_PATH, filename))
            except:
                pass

    def test_generate_archive(self):
        archive = None
        try:
            archive = self.c.generate_archive()
            self.assertTrue(os.path.exists(archive))
            # check it is a zip archive
            returned_output = subprocess.check_output('file "%s"' % archive, shell=True)
            logging.debug('Output: %s' % returned_output)
            self.assertNotEqual(returned_output.lower().find(b'zip archive data'), -1)
        finally:
            if archive and os.path.exists(archive):
                os.remove(archive)

if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_cleepbackup.py; coverage report -m -i
    unittest.main()

