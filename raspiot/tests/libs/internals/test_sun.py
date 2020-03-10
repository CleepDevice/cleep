#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('%s/../../../libs/internals' % os.getcwd())
from sun import Sun
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
import datetime
from dateutil.tz import gettz
from mock import Mock

class SunTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.s = Sun()
        self.s.set_position(48.1113, -1.6800)
        self.utcoffset = self._get_timezone()
        logging.debug('Current UTC offset %s' % self.utcoffset)

    def tearDown(self):
        pass

    def _get_timezone(self, dt=None):
        if not dt:
            return datetime.datetime.now(gettz('Europe/Paris')).strftime('%z')
        else:
            return dt.strftime('%z')

    def test_sunrise(self):
        sunrise = self.s.sunrise()
        self.assertTrue(isinstance(sunrise, datetime.datetime))
        self.assertIsNotNone(sunrise.utcoffset())
        self.assertEqual(self._get_timezone(sunrise), self.utcoffset)

    def test_sunrise_exception(self):
        self.s.set_position(85.0, 21.00)
        d = datetime.date(2014, 1, 3)
        with self.assertRaises(Exception) as cm:
            self.s.get_local_sunrise_time(date=d)
        self.assertEqual(cm.exception.message, 'The sun never rises on this location (on the specified date)')

    def test_get_sunrise_time(self):
        sunrise = self.s.get_sunrise_time()
        self.assertTrue(isinstance(sunrise, datetime.datetime))
        self.assertIsNotNone(sunrise.utcoffset())
        self.assertEqual(self._get_timezone(sunrise), '+0000')

    def test_get_sunrise_time_exception(self):
        self.s.set_position(85.0, 21.00)
        d = datetime.date(2014, 1, 3)
        with self.assertRaises(Exception) as cm:
            self.s.get_sunrise_time(date=d)
        self.assertEqual(cm.exception.message, 'The sun never rises on this location (on the specified date)')

    def test_sunset(self):
        sunset = self.s.sunset()
        self.assertTrue(isinstance(sunset, datetime.datetime))
        self.assertIsNotNone(sunset.utcoffset())
        self.assertEqual(self._get_timezone(sunset), self.utcoffset)

    def test_sunset_exception(self):
        self.s.set_position(85.0, 21.00)
        d = datetime.date(2014, 1, 3)
        with self.assertRaises(Exception) as cm:
            self.s.get_local_sunset_time(date=d)
        self.assertEqual(cm.exception.message, 'The sun never sets on this location (on the specified date)')

    def test_get_sunset_time(self):
        sunset = self.s.get_sunset_time()
        self.assertTrue(isinstance(sunset, datetime.datetime))
        self.assertIsNotNone(sunset.utcoffset())
        self.assertEqual(self._get_timezone(sunset), '+0000')

    def test_get_sunset_time_exception(self):
        self.s.set_position(85.0, 21.00)
        d = datetime.date(2014, 1, 3)
        with self.assertRaises(Exception) as cm:
            self.s.get_sunset_time(date=d)
        self.assertEqual(cm.exception.message, 'The sun never sets on this location (on the specified date)')

    def test_check_corner_case(self):
        # check case 9 (minute==60)
        self.s._force_range = Mock(return_value=0.992)
        self.s.sunrise()
        
        # check case 10 (hour==24)
        self.s._force_range = Mock(return_value=24)
        d = datetime.date(2020, 12, 31)
        self.s.get_local_sunset_time(date=d)

    def test_functional_with_some_positions(self):
        positions = [ 
            (48.1113, -1.6800, 'rennes'),
            (35.681820, 139.767543, 'tokyo'),
            (29.759195, -95.369816, 'houston'),
            (37.779322, -122.419282, 'san francisco'),
            (-34.604155, -58.370411, 'buenos aires'),
            (-33.927286, 18.428338, 'le cap'),
            (-36.858852, 174.756565, 'oakland'),
            (85.0, 21.00, 'lost in the sea'),
        ]

        #valid positions
        for position in positions[:-1]:
            self.s.set_position(position[0], position[1])
            self.s.sunrise()
            self.s.sunset()

        #invalid position
        self.s.set_position(positions[-1][0], positions[-1][1])
        with self.assertRaises(Exception) as cm:
            self.s.sunrise()
        self.assertEqual(cm.exception.message, 'The sun never rises on this location (on the specified date)')


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_sun.py; coverage report -m
    unittest.main()
