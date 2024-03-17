#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from coredevicedeletedevent import CoreDeviceDeletedEvent
import logging
import unittest
from unittest.mock import Mock
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()

class CoreDeviceDeletedEventTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        params = { 
            'internal_bus': Mock(),
            'formatters_broker': Mock(),
            'get_external_bus_name': None,
        }   
        self.event = CoreDeviceDeletedEvent(params)

    def test_event_params(self):
        self.assertEqual(self.event.EVENT_PARAMS, [])

if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_coredevicedeletedevent.py; coverage report -m -i
    unittest.main()

