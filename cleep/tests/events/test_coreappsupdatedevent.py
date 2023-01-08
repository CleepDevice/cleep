#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from coreappsupdatedevent import CoreAppsUpdatedEvent
import logging
import unittest
from mock import Mock

class CoreAppsUpdatedEventTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        params = { 
            'internal_bus': Mock(),
            'formatters_broker': Mock(),
            'get_external_bus_name': None,
        }   
        self.event = CoreAppsUpdatedEvent(params)

    def test_event_params(self):
        self.assertEqual(self.event.EVENT_PARAMS, [])

if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_coreappsupdatedevent.py; coverage report -m -i
    unittest.main()

