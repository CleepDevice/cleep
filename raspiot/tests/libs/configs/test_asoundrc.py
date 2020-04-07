#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('/root/cleep/raspiot/libs/configs')
from asoundrc import Asoundrc
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.exception import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pformat
import io

logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class AsoundrcTest(unittest.TestCase):

    FILE_NAME = 'asoundrc'
    CONTENT = u"""pcm.!default {
            type hw
                    card 0
                    }

ctl.!default {
            type hw           
                        card 0
}"""

    def setUp(self):
        TestLib()
        self.fs = CleepFilesystem()
        self.fs.enable_write()
        self.path = os.path.join(os.getcwd(), self.FILE_NAME)
        logging.debug('Using conf file "%s"' % self.path)

        #fill with default content
        with io.open(self.path, 'w') as f:
            f.write(self.CONTENT)

        a = Asoundrc
        a.CONF = self.FILE_NAME
        self.a = a(self.fs)

    def tearDown(self):
        if os.path.exists('%s' % self.FILE_NAME):
            os.remove('%s' % self.FILE_NAME)

    def test_get_raw_configuration(self):
        raw = self.a.get_raw_configuration()
        logging.debug(raw)

        self.assertTrue('pcm.!default' in raw)
        self.assertTrue('ctl.!default' in raw)

        self.assertTrue('section' in raw['pcm.!default'])
        self.assertTrue('type' in raw['pcm.!default'])
        self.assertTrue('cardid' in raw['pcm.!default'])
        self.assertTrue('deviceid' in raw['pcm.!default'])
        self.assertEqual(raw['pcm.!default']['section'], 'pcm.!default')
        self.assertEqual(raw['pcm.!default']['type'], 'hw')
        self.assertEqual(raw['pcm.!default']['cardid'], 0)
        self.assertEqual(raw['pcm.!default']['deviceid'], None)

        self.assertTrue('section' in raw['ctl.!default'])
        self.assertTrue('type' in raw['ctl.!default'])
        self.assertTrue('cardid' in raw['ctl.!default'])
        self.assertTrue('deviceid' in raw['ctl.!default'])
        self.assertEqual(raw['ctl.!default']['section'], 'ctl.!default')
        self.assertEqual(raw['ctl.!default']['type'], 'hw')
        self.assertEqual(raw['ctl.!default']['cardid'], 0)
        self.assertEqual(raw['ctl.!default']['deviceid'], None)

    def test_get_configuration(self):
        config = self.a.get_configuration()
        logging.debug(config)
        self.assertTrue('section' in config)
        self.assertTrue('type' in config)
        self.assertTrue('cardid' in config)
        self.assertTrue('deviceid' in config)
        self.assertEqual(config['section'], 'pcm.!default')
        self.assertEqual(config['type'], 'hw')
        self.assertEqual(config['cardid'], 0)
        self.assertEqual(config['deviceid'], None)

    def test_set_default_device(self):
        self.assertTrue(self.a.set_default_device(1,2), 'Set default device failed')
        config = self.a.get_configuration()
        self.assertEqual(config['section'], 'pcm.!default')
        self.assertEqual(config['type'], 'hw')
        self.assertEqual(config['cardid'], 1)
        self.assertEqual(config['deviceid'], 2)


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_asoundrc.py
    #coverage report -m
    unittest.main()

