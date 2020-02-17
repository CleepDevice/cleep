#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('/root/cleep/raspiot/libs/internals')
from cleepbackup import CleepBackup
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from mock import Mock
import subprocess

class CleepBackupTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.crash_report = Mock()
        self.fs = Mock()

        self.c = CleepBackup(self.fs, self.crash_report)

    def tearDown(self):
        pass

    def test_generate_archive(self):
        archive = None
        try:
            archive = self.c.generate_archive()
            self.assertTrue(os.path.exists(archive))
            # check it is a zip archive
            returned_output = subprocess.check_output('file "%s"' % archive, shell=True)
            self.assertNotEqual(returned_output.lower().find('zip archive data'), -1)
        finally:
            if archive and os.path.exists(archive):
                os.remove(archive)

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_cleepbackup.py; coverage report -m
    unittest.main()