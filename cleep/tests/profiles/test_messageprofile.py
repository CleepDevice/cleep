#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from messageprofile import MessageProfile
import logging
import unittest
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class MessageProfileTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.p = MessageProfile()

    def tearDown(self):
        pass

    def test_members(self):
        for attr in ['message']:
            self.assertTrue(hasattr(self.p, attr))

if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_messageprofile.py; coverage report -m -i
    unittest.main()

