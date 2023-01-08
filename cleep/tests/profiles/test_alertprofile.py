#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from alertprofile import AlertProfile
import logging
import unittest

class AlertProfileTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.p = AlertProfile()

    def tearDown(self):
        pass

    def test_members(self):
        for attr in ['subject', 'message', 'attachment', 'timestamp']:
            self.assertTrue(hasattr(self.p, attr))

if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_alertprofile.py; coverage report -m -i
    unittest.main()
