#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from cleep.profiles.alarmprofile import AlarmProfile
import logging
import unittest
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class AlertProfileTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.p = AlarmProfile()

    def tearDown(self):
        pass

    def test_members(self):
        for attr in ['hour', 'minute', 'timeout', 'volume', 'count', 'status', 'repeat', 'shuffle']:
            self.assertTrue(hasattr(self.p, attr))
