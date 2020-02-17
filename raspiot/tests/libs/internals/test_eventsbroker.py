#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('/root/cleep/raspiot/libs/internals')
from eventsbroker import EventsBroker
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from mock import Mock

class EventsBrokerTests(unittest.TestCase):

    EVENT_DIR = 'test'
    EVENT_NAME1 = 'event1'
    EVENT_NAME2 = 'event2'

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.TRACE, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.crash_report = Mock()
        self.bus = Mock()
        self.formatters_broker = Mock()

        self.e = EventsBroker(debug_enabled=False)
        self.bootstrap = {
            'message_bus': self.bus,
            'formatters_broker': self.formatters_broker,
            'crash_report': self.crash_report,
        }

    def tearDown(self):
        pass

    def _init_context(self, no_event=False):
        self.e.EVENTS_DIR_MODULES = '../../tests/libs/internals/%s' % self.EVENT_DIR
        # if not self.no_event:
        #     os.mkdir('test')
        #     with io.open('test/%s' % self.FILE, 'w') as fd:
        #         fd.write(u'test')

    def test_configure_no_event(self):
        self._init_context()
        self.e.configure(self.bootstrap)

    def test_enable_debug(self):
        e = EventsBroker(debug_enabled=True)
        self.assertEqual(e.logger.getEffectiveLevel(), logging.DEBUG)


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_eventsbroker.py; coverage report -m
    unittest.main()
