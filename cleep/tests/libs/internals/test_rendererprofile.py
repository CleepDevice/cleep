#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from rendererprofile import RendererProfile
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import Mock

class DummyProfile(RendererProfile):
    def __init__(self):
        RendererProfile.__init__(self)
        self.dummy_number = 666
        self.dummy_string = 'roxanne'
        self.dummy_dict = {
            'd1': 'dv1',
            'd2': 'dv2'
        }
        self.dummy_list = ['l1', 'l2']
        self._invisible = 'queen'
        self.__very_invisible = 'man'

class RendererProfileTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.r = DummyProfile()

    def tearDown(self):
        pass

    def test_to_string(self):
        string = '%s' % self.r
        logging.debug('to string=%s' % string)
        self.assertTrue('dummy_number' in string)
        self.assertTrue('666' in string)
        self.assertTrue('dummy_string' in string)
        self.assertTrue('roxanne' in string)
        self.assertTrue('d1' in string)
        self.assertTrue('dv1' in string)
        self.assertTrue('d2' in string)
        self.assertTrue('dv2' in string)
        self.assertTrue('l1' in string)
        self.assertTrue('l2' in string)
        self.assertFalse('invisible' in string)

    def test_to_dict(self):
        d = self.r.to_dict()
        logging.debug('to dict=%s' % d)
        self.assertTrue('dummy_number' in d)
        self.assertEqual(d['dummy_number'], 666)
        self.assertTrue('dummy_string' in d)
        self.assertEqual(d['dummy_string'], 'roxanne')
        self.assertTrue('dummy_dict' in d)
        self.assertTrue(isinstance(d['dummy_dict'], dict))
        self.assertTrue('d1' in d['dummy_dict'])
        self.assertEqual(d['dummy_dict']['d1'], 'dv1')
        self.assertTrue('d2' in d['dummy_dict'])
        self.assertEqual(d['dummy_dict']['d2'], 'dv2')
        self.assertTrue('dummy_list' in d)
        self.assertTrue(isinstance(d['dummy_list'], list))
        self.assertTrue('l1' in d['dummy_list'])
        self.assertTrue('l2' in d['dummy_list'])
        self.assertFalse('_invisible' in d)
        self.assertFalse('__very_invisible' in d)
    

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python*/*","*test_*.py" --concurrency=thread test_rendererprofile.py; coverage report -m -i
    unittest.main()

