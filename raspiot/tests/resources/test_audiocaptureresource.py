#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from audiocaptureresource import AudioCaptureResource
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import Mock

class AudioCaptureResourceTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.r = AudioCaptureResource()

    def tearDown(self):
        pass

    def test_members(self):
        self.assertTrue(hasattr(self.r, 'RESOURCE_NAME'))
        self.assertEqual(self.r.RESOURCE_NAME, 'audio.capture')


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","*test_*.py" --concurrency=thread test_audiocaptureresource.py; coverage report -m -i
    unittest.main()
