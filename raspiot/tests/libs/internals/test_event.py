#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from event import Event
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from mock import Mock

class DummyModule():
    def __init__(self, format_output={}, can_render_event_output=True):
        self.format = Mock(return_value=format_output)
        self.can_render_event = Mock(return_value=can_render_event_output)

class EventTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.formatters = {
            'profile1': {
                'module1': DummyModule()
            }
        }

    def tearDown(self):
        pass

    def _init_context(self, event_name='test.dummy', event_params=[], event_chartable=False, get_renderers_formatters=[], bus_push_result={'error':False, 'message':''}, event_chart_params=None):
        self.bus = Mock()
        self.bus.push = Mock(return_value=bus_push_result)
        self.formatters_broker = Mock()
        self.formatters_broker.get_renderers_formatters = Mock(return_value=get_renderers_formatters)

        e = Event
        e.EVENT_NAME = event_name
        e.EVENT_PARAMS = event_params
        e.EVENT_CHARTABLE = event_chartable
        e.EVENT_CHART_PARAMS = event_chart_params
        self.e = e(self.bus, self.formatters_broker)

    def test_invalid_event(self):
        try:
            with self.assertRaises(NotImplementedError) as cm:
                E = Event
                E.EVENT_NAME = ''
                E(Mock(), Mock())
            self.assertEqual(cm.exception.message, 'EVENT_NAME class member declared in "Event" must be a non empty string')
        finally:
            Event.EVENT_NAME = ''

        try:
            with self.assertRaises(NotImplementedError) as cm:
                E = Event
                E.EVENT_NAME = 'dummy1'
                E.EVENT_PARAMS = {}
                E(Mock(), Mock())
            self.assertEqual(cm.exception.message, 'EVENT_PARAMS class member declared in "Event" must be a list')
        finally:
            Event.EVENT_PARAMS = []

        try:
            with self.assertRaises(NotImplementedError) as cm:
                E = Event
                E.EVENT_NAME = 'dummy2'
                E.EVENT_CHARTABLE = 1
                E(Mock(), Mock())
            self.assertEqual(cm.exception.message, 'EVENT_CHARTABLE class member declared in "Event" must be a bool')
        finally:
            Event.EVENT_CHARTABLE = False

    def test_invalid_event_no_member(self):
        try:
            with self.assertRaises(NotImplementedError) as cm:
                E = Event
                del(E.EVENT_NAME)
                E.EVENT_PARAMS = None
                E(Mock(), Mock())
            self.assertEqual(cm.exception.message, 'EVENT_NAME class member must be declared in "Event"')
        finally:
            Event.EVENT_NAME = ''

        try:
            with self.assertRaises(NotImplementedError) as cm:
                E = Event
                E.EVENT_NAME = 'dummy3'
                del(E.EVENT_PARAMS)
                E(Mock(), Mock())
            self.assertEqual(cm.exception.message, 'EVENT_PARAMS class member must be declared in "Event"')
        finally:
            Event.EVENT_PARAMS = []

        try:
            with self.assertRaises(NotImplementedError) as cm:
                E = Event
                E.EVENT_NAME = 'dummy4'
                del(E.EVENT_CHARTABLE)
                E(Mock(), Mock())
            self.assertEqual(cm.exception.message, 'EVENT_CHARTABLE class member must be declared in "Event"')
        finally:
            Event.EVENT_CHARTABLE = False

    def test_send(self):
        self._init_context(event_params=['param1'])
        self.assertTrue(self.e.send({'param1': 'value1'}, device_id=None, to='dummy', render=False))
        self.assertTrue(self.bus.push.called)

    def test_send_and_render(self):
        self._init_context(event_params=['param1'], get_renderers_formatters=self.formatters)
        self.assertTrue(self.e.send({'param1': 'value1'}, device_id=None, to='dummy', render=True))
        self.assertEqual(self.bus.push.call_count, 2)

    def test_send_no_param(self):
        self._init_context(event_params=[])
        self.assertTrue(self.e.send({}, device_id=None, to='dummy', render=False))
        self.assertTrue(self.bus.push.called)

    def test_send_invalid_params(self):
        self._init_context(event_params=['param'])
        with self.assertRaises(Exception) as cm:
            self.e.send({'dummy': 666}, device_id=None, to='dummy', render=False)
        self.assertEqual(cm.exception.message, 'Invalid event parameters specified for "test.dummy": {\'dummy\': 666}')

    def test_send_bus_push_failed(self):
        self._init_context(event_params=['param'], bus_push_result={'error':True, 'message':'test error'})
        self.assertFalse(self.e.send({}, device_id=None, to='dummy', render=False))

    def test_send_and_render_handle_render_exception(self):
        self._init_context(event_params=['param1'], get_renderers_formatters=self.formatters)
        self.e.render = Mock(side_effect=Exception('test exception'))
        self.assertTrue(self.e.send({'param1': 'value1'}, device_id=None, to='dummy', render=True))

    def test_render(self):
        self._init_context(event_params=['param1'], get_renderers_formatters=self.formatters)
        self.assertTrue(self.e.render({'param1': 'value1'}))
        self.assertEqual(self.bus.push.call_count, 1)

    def test_render_no_formatter(self):
        self._init_context(event_params=['param1'], get_renderers_formatters={})
        self.assertFalse(self.e.render({'param1': 'value1'}))
        self.assertEqual(self.bus.push.call_count, 0)

    def test_render_formatter_return_none(self):
        formatters = {
            'profile1': {
                'module1': DummyModule(format_output=None)
            }
        }
        self._init_context(event_params=['param1'], get_renderers_formatters=formatters)
        self.assertTrue(self.e.render({'param1': 'value1'}))
        self.assertEqual(self.bus.push.call_count, 0)
    
    def test_render_one_formatter_return_none(self):
        formatters = {
            'profile1': {
                'module1': DummyModule(format_output=None)
            },
            'profile2': {
                'module1': DummyModule(format_output={'test':'dummy'})
            }
        }
        self._init_context(event_params=['param1'], get_renderers_formatters=formatters)
        self.assertTrue(self.e.render({'param1': 'value1'}))
        self.assertEqual(self.bus.push.call_count, 1)

    def test_render_bus_push_failed(self):
        self._init_context(event_params=['param'], get_renderers_formatters=self.formatters, bus_push_result={'error':True, 'message':'test error'})
        self.assertFalse(self.e.render({}))

    def test_render_can_render_event_return_false(self):
        formatters = {
            'profile1': {
                'module1': DummyModule(format_output=None, can_render_event_output=False)
            }
        }
        self._init_context(event_params=['param1'], get_renderers_formatters=formatters)
        self.assertTrue(self.e.render({'param1': 'value1'}))
        self.assertEqual(self.bus.push.call_count, 0)

    def test_get_chart_values(self):
        self._init_context(event_params=['param1'], event_chartable=True)
        values = self.e.get_chart_values({'param1': 'value1'})
        self.assertTrue(isinstance(values, list))
        self.assertEqual(len(values), 1)
        self.assertTrue('field' in values[0])
        self.assertEqual(values[0]['field'], 'param1')
        self.assertTrue('value' in values[0])
        self.assertEqual(values[0]['value'], 'value1')

    def test_get_chart_values_not_chartable(self):
        self._init_context(event_params=['param1'], event_chartable=False)
        self.assertIsNone(self.e.get_chart_values({'param1': 'value1'}))

    def test_get_chart_values_params_filtered(self):
        self._init_context(event_params=['param1', 'param2', 'param3'], event_chartable=True, event_chart_params=['param1', 'param3'])
        values = self.e.get_chart_values({'param1': 'value1', 'param2':'value2', 'param3':'value3'})
        self.assertEqual(len(values), 2)
        values_as_dict = { value['field']:value['value'] for value in values }
        logging.debug('Values_as_dict=%s' % values_as_dict)
        self.assertTrue('param1' in values_as_dict.keys())
        self.assertTrue('param3' in values_as_dict.keys())
        self.assertFalse('param2' in values_as_dict.keys())
        self.assertEqual(values_as_dict['param1'], 'value1')
        self.assertEqual(values_as_dict['param3'], 'value3')

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","*test_*.py" --concurrency=thread test_event.py; coverage report -m -i
    unittest.main()
