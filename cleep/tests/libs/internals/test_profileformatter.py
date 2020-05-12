#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from profileformatter import ProfileFormatter
from cleep.libs.tests.lib import TestLib
from cleep.libs.internals.rendererprofile import RendererProfile
from cleep.exception import InvalidParameter
import unittest
import logging

class DummyClass():
    def __init__(self, *args, **kwargs):
        pass

class DummyProfile(RendererProfile):
    def __init__(self, *args, **kwargs):
        RendererProfile()

class ProfileFormatterTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def test_init(self):
        with self.assertRaises(InvalidParameter) as cm1:
            ProfileFormatter(DummyClass(), 666, DummyProfile())
        self.assertEqual(str(cm1.exception), 'Invalid event_name specified')
        with self.assertRaises(InvalidParameter) as cm2:
            ProfileFormatter(DummyClass(), 'dummy.event', DummyClass())
        self.assertEqual(str(cm2.exception), 'Invalid profile specified. Instance must inherits from RendererProfile')

    def test_format_invalid_parameters(self):
        with self.assertRaises(InvalidParameter) as cm:
            p = ProfileFormatter(DummyClass(), 'dummy.event', DummyProfile())
            p.format({})
        self.assertEqual(str(cm.exception), 'Parameter "event_params" must be a list')

    def test_format_no_fill_profile_implemented(self):
        with self.assertRaises(NotImplementedError) as cm:
            p = ProfileFormatter(DummyClass(), 'dummy.event', DummyProfile())
            p.format([])
        self.assertEqual(str(cm.exception), '_fill_profile method must be implemented in "ProfileFormatter"')


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python*/*","*test_*.py" --concurrency=thread test_profileformatter.py; coverage report -m -i
    unittest.main()

