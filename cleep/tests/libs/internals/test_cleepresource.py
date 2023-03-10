#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from cleepresource import CleepResource
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import Mock

class CleepResourceTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.r = CleepResource()

    def tearDown(self):
        pass

    def test_members(self):
        self.assertTrue(hasattr(self.r, 'RESOURCE_NAME'))


if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_cleepresource.py; coverage report -m -i
    unittest.main()

