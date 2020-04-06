#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('%s/../../../libs/internals' % os.getcwd())
from drivers import Drivers
from raspiot.libs.tests.lib import TestLib
from raspiot.exceptions import MissingParameter, InvalidParameter
import unittest
import logging
from mock import Mock


class DummyDriver():
    def __init__(self, driver_name='dummy', driver_type='gpio'):
        self.name = driver_name
        self.type = driver_type


class DriversTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.crash_report = Mock()
        self.fs = Mock()

        self.d = Drivers(debug_enabled=False)
        
    def tearDown(self):
        pass

    def test_enable_debug(self):
        try:
            d = Drivers(debug_enabled=True)
            self.assertEqual(d.logger.getEffectiveLevel(), logging.DEBUG)
        finally:
            d.logger.setLevel(logging.FATAL)

    def test_register(self):
        # no exception raised
        self.d.register(DummyDriver())

    def test_register_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.d.register(None)
        self.assertEqual(cm.exception.message, 'Parameter "driver" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.d.register(DummyDriver(driver_name=None))
        self.assertEqual(cm.exception.message, 'Driver name is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.d.register(DummyDriver(driver_name=''))
        self.assertEqual(cm.exception.message, 'Driver name is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.d.register(DummyDriver(driver_type='test'))
        self.assertEqual(cm.exception.message, 'Driver must be one of existing driver type (found "test")')

    def test_get_all_drivers(self):
        self.d.register(DummyDriver())
        drivers = self.d.get_all_drivers()

        self.assertTrue(isinstance(drivers, dict))
        self.assertTrue('gpio' in drivers)
        self.assertTrue('audio' in drivers)
        #TODO add another driver types
        self.assertEqual(len(drivers['gpio']), 1)
        self.assertEqual(len(drivers['audio']), 0)

    def test_get_drivers(self):
        self.d.register(DummyDriver())
        drivers = self.d.get_drivers('gpio')
        self.assertEqual(len(drivers), 1)
        drivers = self.d.get_drivers('audio')
        self.assertEqual(len(drivers), 0)

    def test_get_drivers_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.d.get_drivers(None)
        self.assertEqual(cm.exception.message, 'Parameter "driver_type" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.d.get_drivers('')
        self.assertEqual(cm.exception.message, 'Parameter "driver_type" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.d.get_drivers('test')
        self.assertEqual(cm.exception.message, 'Driver must be one of existing driver type (found "test")')

    def test_get_driver(self):
        d = DummyDriver()
        self.d.register(d)
        driver = self.d.get_driver(d.type, d.name)
        self.assertIsNotNone(driver)

    def test_get_driver_unknown(self):
        d = DummyDriver()
        self.d.register(d)
        driver = self.d.get_driver(d.type, 'test')
        self.assertIsNone(driver)

    def test_get_driver_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.d.get_driver(None, 'test')
        self.assertEqual(cm.exception.message, 'Parameter "driver_type" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.d.get_driver('', 'test')
        self.assertEqual(cm.exception.message, 'Parameter "driver_type" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.d.get_driver('test', 'test')
        self.assertEqual(cm.exception.message, 'Driver must be one of existing driver type (found "test")')
        with self.assertRaises(MissingParameter) as cm:
            self.d.get_driver('gpio', None)
        self.assertEqual(cm.exception.message, 'Parameter "driver_name" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.d.get_driver('gpio', '')
        self.assertEqual(cm.exception.message, 'Parameter "driver_name" is missing')


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_drivers.py; coverage report -m
    unittest.main()
