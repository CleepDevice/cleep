#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from audioplaybackresource import AudioPlaybackResource
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import Mock
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class AudioPlaybackResourceTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.r = AudioPlaybackResource()

    def tearDown(self):
        pass

    def test_members(self):
        self.assertTrue(hasattr(self.r, 'RESOURCE_NAME'))
        self.assertEqual(self.r.RESOURCE_NAME, 'audio.playback')


if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_audioplaybackresource.py; coverage report -m -i
    unittest.main()

