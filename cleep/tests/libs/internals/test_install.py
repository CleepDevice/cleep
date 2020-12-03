#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from install import Install
from cleep.libs.tests.lib import TestLib
from cleep.exception import MissingParameter, InvalidParameter
import unittest
import logging
from unittest.mock import Mock, patch


class InstallTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass


if __name__ == '__main__':
    # coverage run --omit="/usr/local/lib/python*/*","*test_*.py" --concurrency=thread test_install.py; coverage report -m -i
    unittest.main()

