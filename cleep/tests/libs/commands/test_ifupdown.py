#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from ifupdown import Ifupdown
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import Mock


class IfupdownTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')
        self.i = Ifupdown()

    def tearDown(self):
        pass

    def test_stop_interface(self):
        self.i.command = Mock(return_value='command_fake')

        self.i.get_last_return_code = Mock(return_value=0)
        self.assertTrue(self.i.stop_interface('test'), 'Stop interface should return True')

        self.i.get_last_return_code = Mock(return_value=1)
        self.assertFalse(self.i.stop_interface('test'), 'Stop interface should return False')

    def test_start_interface(self):
        self.i.command = Mock(return_value='command_fake')

        self.i.get_last_return_code = Mock(return_value=0)
        self.assertTrue(self.i.start_interface('test'), 'Start interface should return True')

        self.i.get_last_return_code = Mock(return_value=1)
        self.assertFalse(self.i.start_interface('test'), 'Start interface should return False')

    def test_restart_interface(self):
        self.i.command = Mock(return_value='command_fake')

        self.i.stop_interface = Mock(return_value=True)
        self.i.start_interface = Mock(return_value=True)
        self.assertTrue(self.i.restart_interface('test'), 'Restart interface should return True')

        self.i.stop_interface = Mock(return_value=False)
        self.i.start_interface = Mock(return_value=True)
        self.assertFalse(self.i.restart_interface('test'), 'Restart interface should return False')

        self.i.stop_interface = Mock(return_value=True)
        self.i.start_interface = Mock(return_value=False)
        self.assertFalse(self.i.restart_interface('test'), 'Restart interface should return False')

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","*test_*.py" --concurrency=thread test_ifupdown.py; coverage report -m -i
    unittest.main()
