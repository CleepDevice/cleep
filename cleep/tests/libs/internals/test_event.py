#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from event import Event
from cleep.libs.tests.lib import TestLib
from cleep.common import MessageResponse
import unittest
import logging
from unittest.mock import Mock

class DummyModule():
    def __init__(self, format_output={}, can_render_event_output=True):
        self.format = Mock(return_value=format_output)
        self.can_render_event = Mock(return_value=can_render_event_output)

class EventTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.module1_formatter = Mock()
        self.formatters = {
            'event1': {
                'module1': self.module1_formatter
            }
        }

    def tearDown(self):
        pass

    def init_lib(self, event_name='test.dummy', event_params=[], event_chartable=False, get_renderers_formatters=[],
            bus_push_result=None, event_chart_params=None, invalid_constructor_params=False):
        bus_push_result = MessageResponse(error=False, message='') if bus_push_result is None else bus_push_result
        self.internal_bus = Mock()
        self.internal_bus.push = Mock(return_value=bus_push_result)
        self.formatters_broker = Mock()
        self.formatters_broker.get_renderers_formatters = Mock(return_value=get_renderers_formatters)
        self.events_broker = Mock()
        self.events_broker.is_event_renderable.return_value = True

        e = Event
        e.EVENT_NAME = event_name
        e.EVENT_PARAMS = event_params
        e.EVENT_CHARTABLE = event_chartable
        if event_chart_params:
            e.EVENT_CHART_PARAMS = event_chart_params

        if not invalid_constructor_params:
            self.e = e({
                'internal_bus': self.internal_bus,
                'formatters_broker': self.formatters_broker,
                'events_broker': self.events_broker,
                'get_external_bus_name': lambda: 'externalbus'
            })
        else:
            self.e = e({'internal_bus': self.internal_bus})

    def test_invalid_constructor_params(self):
        with self.assertRaises(Exception) as cm:
            self.init_lib(invalid_constructor_params=True)
        self.assertEqual(str(cm.exception), 'Invalid "test.dummy" event, please check constructor parameters')

    def test_invalid_event(self):
        try:
            with self.assertRaises(NotImplementedError) as cm:
                E = Event
                E.EVENT_NAME = ''
                E({'internal_bus': Mock(), 'formatters_broker': Mock(), 'get_external_bus_name': Mock(return_value='externalbus')})
            self.assertEqual(str(cm.exception), 'EVENT_NAME class member declared in "Event" must be a non empty string')
        finally:
            Event.EVENT_NAME = ''

        try:
            with self.assertRaises(NotImplementedError) as cm:
                E = Event
                E.EVENT_NAME = 'dummy1'
                E.EVENT_PARAMS = {}
                E({'internal_bus': Mock(), 'formatters_broker': Mock(), 'get_external_bus_name': Mock(return_value='externalbus')})
            self.assertEqual(str(cm.exception), 'EVENT_PARAMS class member declared in "Event" must be a list')
        finally:
            Event.EVENT_PARAMS = []

        try:
            with self.assertRaises(NotImplementedError) as cm:
                E = Event
                E.EVENT_NAME = 'dummy2'
                E.EVENT_CHARTABLE = 1
                E({'internal_bus': Mock(), 'formatters_broker': Mock(), 'get_external_bus_name': Mock(return_value='externalbus')})
            self.assertEqual(str(cm.exception), 'EVENT_CHARTABLE class member declared in "Event" must be a bool')
        finally:
            Event.EVENT_CHARTABLE = False

    def test_invalid_event_no_member(self):
        try:
            with self.assertRaises(NotImplementedError) as cm:
                E = Event
                del(E.EVENT_NAME)
                E.EVENT_PARAMS = None
                E({'internal_bus': Mock(), 'formatters_broker': Mock(), 'get_external_bus_name': Mock(return_value='externalbus')})
            self.assertEqual(str(cm.exception), 'EVENT_NAME class member must be declared in "Event"')
        finally:
            Event.EVENT_NAME = ''

        try:
            with self.assertRaises(NotImplementedError) as cm:
                E = Event
                E.EVENT_NAME = 'dummy3'
                del(E.EVENT_PARAMS)
                E({'internal_bus': Mock(), 'formatters_broker': Mock(), 'get_external_bus_name': Mock(return_value='externalbus')})
            self.assertEqual(str(cm.exception), 'EVENT_PARAMS class member must be declared in "Event"')
        finally:
            Event.EVENT_PARAMS = []

        try:
            with self.assertRaises(NotImplementedError) as cm:
                E = Event
                E.EVENT_NAME = 'dummy4'
                del(E.EVENT_CHARTABLE)
                E({'internal_bus': Mock(), 'formatters_broker': Mock(), 'get_external_bus_name': Mock(return_value='externalbus')})
            self.assertEqual(str(cm.exception), 'EVENT_CHARTABLE class member must be declared in "Event"')
        finally:
            Event.EVENT_CHARTABLE = False

    def test_send(self):
        self.init_lib(event_params=['param1'])
        self.assertIsNone(self.e.send({'param1': 'value1'}, device_id=None, to='dummy', render=False))
        self.assertTrue(self.internal_bus.push.called)
        call_args = self.internal_bus.push.call_args[0]
        logging.debug('Call args: %s' % call_args[0])
        self.assertDictEqual(call_args[0].to_dict(), {
            'event': 'test.dummy',
            'params': {'param1': 'value1'},
            'sender': 'eventtests',
            'startup': False,
            'device_id': None,
            'to': 'dummy',
            'propagate': False,
        })

    def test_send_and_render(self):
        self.init_lib(event_params=['param1'], get_renderers_formatters=self.formatters['event1'])
        self.assertIsNone(self.e.send({'param1': 'value1'}, device_id=None, to='dummy', render=True))
        self.assertEqual(self.internal_bus.push.call_count, 2)

    def test_send_no_param(self):
        self.init_lib(event_params=[])
        self.assertIsNone(self.e.send({}, device_id=None, to='dummy', render=False))
        self.assertTrue(self.internal_bus.push.called)
        call_args = self.internal_bus.push.call_args[0]
        logging.debug('Call args: %s' % call_args[0])
        self.assertDictEqual(call_args[0].to_dict(), {
            'event': 'test.dummy',
            'params': {},
            'sender': 'eventtests',
            'startup': False,
            'device_id': None,
            'to': 'dummy',
            'propagate': False,
        })

    def test_send_invalid_params(self):
        self.init_lib(event_params=['param'])
        with self.assertRaises(Exception) as cm:
            self.e.send({'dummy': 666}, device_id=None, to='dummy', render=False)
        self.assertEqual(str(cm.exception), 'Invalid event parameters specified for "test.dummy": {\'dummy\': 666}')

    def test_send_and_render_handle_render_exception(self):
        self.init_lib(event_params=['param1'], get_renderers_formatters=self.formatters)
        self.e.render = Mock(side_effect=Exception('Test exception'))
        self.assertIsNone(self.e.send({'param1': 'value1'}, device_id=None, to='dummy', render=True))

    def test_send_to_peer(self):
        self.init_lib(event_params=['param'])
        self.e.send_to_peer('123-456-789', {'param': 'value'}, device_id='987-654-321')
        self.assertTrue(self.internal_bus.push.called)
        call_args = self.internal_bus.push.call_args[0]
        logging.debug('Call args: %s' % call_args[0])
        self.assertDictEqual(call_args[0].to_dict(), {
            'event': 'test.dummy',
            'params': {'param': 'value'},
            'sender': 'eventtests',
            'startup': False,
            'device_id': '987-654-321',
            'to': 'externalbus',
            'propagate': False,
        })

    def test_send_to_peer_invalid_params(self):
        self.init_lib(event_params=['param'])
        with self.assertRaises(Exception) as cm:
            self.e.send_to_peer('123-456-789', {'dummy': 666})
        self.assertEqual(str(cm.exception), 'Invalid event parameters specified for "test.dummy": {\'dummy\': 666}')

    def test_render(self):
        self.init_lib(event_params=['param1'], get_renderers_formatters=self.formatters['event1'])
        self.assertTrue(self.e.render({'param1': 'value1'}))
        self.assertEqual(self.internal_bus.push.call_count, 1)

    def test_render_rendering_disabled(self):
        self.init_lib(event_params=['param1'], get_renderers_formatters=self.formatters['event1'])
        self.events_broker.is_event_renderable.return_value = False

        self.assertTrue(self.e.render({'param1': 'value1'}))
        self.assertEqual(self.internal_bus.push.call_count, 0)

    def test_render_no_formatter(self):
        self.init_lib(event_params=['param1'], get_renderers_formatters={})
        self.assertFalse(self.e.render({'param1': 'value1'}))
        self.assertEqual(self.internal_bus.push.call_count, 0)

    def test_render_formatter_return_none(self):
        formatter_mock = Mock()
        formatter_mock.format.return_value = None
        formatters = {
            'event1': {
                'module1': formatter_mock
            }
        }
        self.init_lib(event_params=['param1'], get_renderers_formatters=formatters['event1'])
        self.assertTrue(self.e.render({'param1': 'value1'}))
        self.assertEqual(self.internal_bus.push.call_count, 0)
    
    def test_render_one_formatter_return_none(self):
        formatter1 = Mock()
        formatter1.format.return_value = None
        formatter2 = Mock()
        formatter2.format.return_value = Mock()
        formatters = {
            'module1': formatter1,
            'module2': formatter2,
        }
        self.init_lib(event_params=['param1'], get_renderers_formatters=formatters)
        self.assertTrue(self.e.render({'param1': 'value1'}))
        self.assertEqual(self.internal_bus.push.call_count, 1)

    def test_render_bus_push_failed(self):
        self.init_lib(event_params=['param'], get_renderers_formatters=self.formatters['event1'], bus_push_result=MessageResponse(error=True, message='test error'))
        self.assertFalse(self.e.render({}))

    def test_get_chart_values(self):
        self.init_lib(event_params=['param1'], event_chartable=True)
        values = self.e.get_chart_values({'param1': 'value1'})
        self.assertTrue(isinstance(values, list))
        self.assertEqual(len(values), 1)
        self.assertTrue('field' in values[0])
        self.assertEqual(values[0]['field'], 'param1')
        self.assertTrue('value' in values[0])
        self.assertEqual(values[0]['value'], 'value1')

    def test_get_chart_values_not_chartable(self):
        self.init_lib(event_params=['param1'], event_chartable=False)
        self.assertIsNone(self.e.get_chart_values({'param1': 'value1'}))

    def test_get_chart_values_params_filtered(self):
        self.init_lib(event_params=['param1', 'param2', 'param3'], event_chartable=True, event_chart_params=['param1', 'param3'])
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
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_event.py; coverage report -m -i
    unittest.main()

