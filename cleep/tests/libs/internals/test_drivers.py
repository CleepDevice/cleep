#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from drivers import Drivers
from cleep.libs.tests.lib import TestLib
from cleep.exception import MissingParameter, InvalidParameter
import unittest
import logging
from unittest.mock import Mock
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class DummyDriver():
    def __init__(self, driver_name='dummy', driver_type='electronic'):
        self.name = driver_name
        self.type = driver_type


class DriversTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
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
        driver = DummyDriver()
        self.d.register(driver)
        logging.debug('Drivers %s' % self.d.drivers)

        self.assertEqual(len(self.d.drivers[driver.type]), 1)

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

    def test_unregister(self):
        driver = DummyDriver()
        self.d.register(driver)
        self.assertEqual(len(self.d.drivers[driver.type]), 1)

        self.d.unregister(driver)
        self.assertEqual(len(self.d.drivers[driver.type]), 0)

    def test_unregister_invalid_params(self):
        with self.assertRaises(InvalidParameter) as cm:
            self.d.unregister(None)
        self.assertEqual(cm.exception.message, 'Parameter "driver" is invalid')

        with self.assertRaises(InvalidParameter) as cm:
            self.d.unregister(DummyDriver())
        self.assertEqual(cm.exception.message, 'Driver not found')


    def test_get_all_drivers(self):
        self.d.register(DummyDriver())
        drivers = self.d.get_all_drivers()

        self.assertTrue(isinstance(drivers, dict))
        self.assertTrue('electronic' in drivers)
        self.assertTrue('audio' in drivers)
        #TODO add another driver types
        self.assertEqual(len(drivers['electronic']), 1)
        self.assertEqual(len(drivers['audio']), 0)

    def test_get_all_drivers_swallow_copy(self):
        driver1 = DummyDriver('driver1')
        driver2 = DummyDriver('driver2')
        self.d.register(driver1)
        self.d.register(driver2)

        drivers = self.d.get_all_drivers()
        before_len = len(drivers)

        del self.d.drivers[driver1.type][driver1.name]
        after_len = len(drivers)

        self.assertEqual(before_len, after_len)

    def test_get_drivers(self):
        self.d.register(DummyDriver())
        drivers = self.d.get_drivers('electronic')
        self.assertEqual(len(drivers), 1)
        drivers = self.d.get_drivers('audio')
        self.assertEqual(len(drivers), 0)

    def test_get_drivers_swallow_copy(self):
        driver1 = DummyDriver('driver1')
        driver2 = DummyDriver('driver2')
        self.d.register(driver1)
        self.d.register(driver2)

        drivers = self.d.get_drivers('electronic')
        before_len = len(drivers)

        del self.d.drivers[driver1.type][driver1.name]
        after_len = len(drivers)

        self.assertEqual(before_len, after_len)

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
            self.d.get_driver('electronic', None)
        self.assertEqual(cm.exception.message, 'Parameter "driver_name" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.d.get_driver('electronic', '')
        self.assertEqual(cm.exception.message, 'Parameter "driver_name" is missing')


if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_drivers.py; coverage report -m -i
    unittest.main()

