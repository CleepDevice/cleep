#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('%s/../' % os.getcwd())
from exception import CommandError, CommandInfo, NoResponse, NoMessageAvailable, ResourceNotAvailable, InvalidParameter, MissingParameter, InvalidMessage, InvalidModule, Unauthorized, BusError, ForcedException
from raspiot.libs.tests.lib import TestLib
import unittest
import logging


class ExceptionTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def test_commanderror(self):
        e = CommandError('message')
        self.assertNotEqual(e.message, 0)
        self.assertEqual('%s' % e, 'message')

    def test_commandinfo(self):
        e = CommandInfo('message')
        self.assertNotEqual(e.message, 0)
        self.assertEqual('%s' % e, 'message')

    def test_noresponse(self):
        e = NoResponse('dummy', 3.0, 123)
        self.assertNotEqual(e.message, 0)
        self.assertEqual('%s' % e, 'No response from dummy (3.0 seconds) for request: 123')

    def test_nomessageavailable(self):
        e = NoMessageAvailable()
        self.assertNotEqual(e.message, 0)
        self.assertEqual('%s' % e, 'No message available')

    def test_resourcenotavailable(self):
        e = ResourceNotAvailable('dummy')
        self.assertNotEqual(e.message, 0)
        self.assertEqual('%s' % e, 'Resource dummy not available')

    def test_invalidparameter(self):
        e = InvalidParameter('message')
        self.assertNotEqual(e.message, 0)
        self.assertEqual('%s' % e, 'message')

    def test_missingparameter(self):
        e = MissingParameter('message')
        self.assertNotEqual(e.message, 0)
        self.assertEqual('%s' % e, 'message')

    def test_invalidmessage(self):
        e = InvalidMessage()
        self.assertNotEqual(e.message, 0)
        self.assertEqual('%s' % e, 'Invalid message')

    def test_invalidmodule(self):
        e = InvalidModule('dummy')
        self.assertNotEqual(e.message, 0)
        self.assertEqual('%s' % e, 'Invalid module "dummy" (not loaded or unknown)')

    def test_unauthorized(self):
        e = Unauthorized('message')
        self.assertNotEqual(e.message, 0)
        self.assertEqual('%s' % e, 'message')

    def test_buserror(self):
        e = BusError('message')
        self.assertNotEqual(e.message, 0)
        self.assertEqual('%s' % e, 'message')

    def test_forcedexception(self):
        e = ForcedException('message')
        self.assertNotEqual(e.message, 0)
        self.assertEqual('%s' % e, 'ForcedException(message)')


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_exception.py; coverage report -m
    unittest.main()

