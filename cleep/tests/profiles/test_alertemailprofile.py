#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from alertemailprofile import AlertEmailProfile
import logging
import unittest

class AlertEmailProfileTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.p = AlertEmailProfile()

    def tearDown(self):
        pass

    def test_members(self):
        for attr in ['subject', 'message', 'recipients', 'attachment']:
            self.assertTrue(hasattr(self.p, attr))

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python*/*","*test_*.py" --concurrency=thread test_alertemailprofile.py; coverage report -m -i
    unittest.main()
