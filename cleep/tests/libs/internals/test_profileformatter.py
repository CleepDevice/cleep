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
from unittest.mock import Mock
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class DummyProfile(RendererProfile):
    def __init__(self, *args, **kwargs):
        RendererProfile()

class DummyFormatter(ProfileFormatter):
    def __init__(self, *args, **kwargs):
        ProfileFormatter.__init__(self, {'events_broker': Mock()}, 'dummy.event.test', DummyProfile())

    def _fill_profile(self, event_params, profile):
        pass


class ProfileFormatterTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        TestLib()

    def test_init(self):
        with self.assertRaises(InvalidParameter) as cm1:
            ProfileFormatter({'events_broker': Mock()}, 666, Mock())
        self.assertEqual(str(cm1.exception), 'Invalid event_name specified')
        with self.assertRaises(InvalidParameter) as cm2:
            ProfileFormatter({'events_broker': Mock()}, 'dummy.event', Mock())
        self.assertEqual(str(cm2.exception), 'Invalid profile specified. Instance must inherits from RendererProfile')

    def test_format_invalid_parameters(self):
        with self.assertRaises(InvalidParameter) as cm:
            p = DummyFormatter({'events_broker': Mock()}, 'dummy.event', DummyProfile())
            p.format([])
        self.assertEqual(str(cm.exception), 'Parameter "event_params" must be a dict not list and not empty')

    def test_format_no_fill_profile_implemented(self):
        with self.assertRaises(NotImplementedError) as cm:
            p = ProfileFormatter({'events_broker': Mock()}, 'dummy.event', DummyProfile())
            p.format({'test':'test'})
        self.assertEqual(str(cm.exception), '_fill_profile method must be implemented in "ProfileFormatter"')


if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_profileformatter.py; coverage report -m -i
    unittest.main()

