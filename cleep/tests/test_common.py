#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests', ''))
from common import MessageResponse, MessageRequest, ExecutionStep, PeerInfos
from cleep.libs.tests.lib import TestLib
from cleep.exception import InvalidMessage
import unittest
import logging


class TestExecutionStep(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def test_execution_step(self):
        e = ExecutionStep()
        self.assertEqual(e.step, e.BOOT)



class TestPeerInfos(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def test_to_str(self):
        p = PeerInfos(uuid='uuid', ident='ident', hostname='hostname', ip='0.0.0.0', port=123, ssl=True, macs=['0.0.0.0'], cleepdesktop=True)

        self.assertEqual(
            '%s' % p,
            'PeerInfos(uuid:uuid, ident:ident, hostname:hostname, ip:0.0.0.0 port:123, ssl:True, macs:[\'0.0.0.0\'], cleepdesktop:True, online:False)'
        )

    def test_to_dict(self):
        p = PeerInfos(uuid='uuid', ident='ident', hostname='hostname', ip='0.0.0.0', port=123, ssl=True, macs=['0.0.0.0'], cleepdesktop=True, extra={'field': 'value'})
        self.assertDictEqual(
            p.to_dict(),
            {
                'uuid': 'uuid',
                'ident': 'ident',
                'hostname': 'hostname',
                'ip': '0.0.0.0',
                'port': 123,
                'ssl': True,
                'macs': ['0.0.0.0'],
                'cleepdesktop': True,
                'online': False,
            }
        )

    def test_fill_from_dict(self):
        p = PeerInfos()
        p.fill_from_dict({
            'uuid': 'uuid',
            'ident': 'ident',
            'hostname': 'hostname',
            'ip': '0.0.0.0',
            'port': 123,
            'ssl': True,
            'macs': ['0.0.0.0'],
            'cleepdesktop': True,
            'online': False,
        })

        self.assertDictEqual(p.to_dict(), {
            'uuid': 'uuid',
            'ident': 'ident',
            'hostname': 'hostname',
            'ip': '0.0.0.0',
            'port': 123,
            'ssl': True,
            'macs': ['0.0.0.0'],
            'cleepdesktop': True,
            'online': False,
        })

    def test_fill_from_dict_exception(self):
        p = PeerInfos()
        with self.assertRaises(Exception) as cm:
            p.fill_from_dict(123)
        self.assertEqual(str(cm.exception), 'Parameter "peer_infos" must be a dict')


class TestMessageResponse(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def test_message_response(self):
        m = MessageResponse()

        self.assertEqual(m.error, False)
        self.assertEqual(m.message, '')
        self.assertEqual(m.data, None)
        self.assertEqual(m.broadcast, False)

    def test_message_response_to_string(self):
        m = MessageResponse()
        m.error = True
        m.message = 'a message'
        m.data = { 'key': 'value', 'int': 666 }
        m.broadcast = True

        self.assertTrue('error:True' in str(m))
        self.assertTrue('message:"a message"' in str(m))
        self.assertTrue('\'int\': 666' in str(m))
        self.assertTrue('\'key\': \'value\'' in str(m))
        self.assertTrue('broadcast:True' in str(m))

    def test_message_response_to_dict(self):
        m = MessageResponse()
        m.error = True
        m.message = 'a message'
        m.data = { 'key': 'value', 'int': 666 }
        m.broadcast = True

        to_dict = m.to_dict()
        self.assertEqual(to_dict['error'], m.error)
        self.assertEqual(to_dict['message'], m.message)
        self.assertEqual(to_dict['data'], m.data)
        self.assertFalse('broadcast' in to_dict)

    def test_fill_from_response(self):
        m = MessageResponse()
        
        m.fill_from_response(MessageResponse(error=True, message='hello', data=['somedata', 'ola'], broadcast=True))

        self.assertDictEqual(m.to_dict(), {
            'error': True,
            'message': 'hello',
            'data': ['somedata', 'ola'],
        })

    def test_fill_from_response_exception(self):
        m = MessageResponse()

        with self.assertRaises(Exception) as cm:
            m.fill_from_response({})
        self.assertEqual(str(cm.exception), 'Parameter "response" must be a MessageResponse instance')



class TestMessageRequest(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def test_message_request(self):
        m = MessageRequest()

        self.assertEqual(m.command, None)
        self.assertEqual(m.event, None)
        self.assertEqual(m.propagate, False)
        self.assertEqual(m.params, {})
        self.assertEqual(m.to, None)
        self.assertEqual(m.sender, None)
        self.assertEqual(m.device_id, None)
        self.assertEqual(m.peer_infos, None)

    def test_message_request_to_string(self):
        m = MessageRequest()
        m.command = 'acommand'
        m.event = 'event.dummy.test'
        m.propagate = True
        m.params = { 'int': 666, 'key': 'value' }
        m.to = 'dummy'
        m.sender = 'otherdummy'
        m.device_id = '123-456-789'
        m.peer_infos = PeerInfos(ip='0.0.0.0', macs=['00-00-00-00-00-00'])

        self.assertTrue('command:acommand' in str(m))
        self.assertTrue('\'int\': 666' in str(m))
        self.assertTrue('\'key\': \'value\'' in str(m))
        self.assertTrue('to:dummy' in str(m))
        self.assertTrue('sender:otherdummy' in str(m))
        m.command = None
        self.assertTrue('event:event.dummy.test' in str(m))
        self.assertTrue('propagate:True' in str(m))
        self.assertTrue('\'int\': 666' in str(m))
        self.assertTrue('\'key\': \'value\'' in str(m))
        self.assertTrue('to:dummy' in str(m))
        self.assertTrue('device_id:123-456-789' in str(m))
        self.assertTrue('\'ip\': \'0.0.0.0\'' in str(m))
        self.assertTrue('\'macs\': [\'00-00-00-00-00-00\']' in str(m))
        m.event = None
        self.assertEqual('%s' % m, 'MessageRequest(Invalid message)')

    def test_is_broadcast(self):
        m = MessageRequest()
        m.to = 'dummy'

        self.assertFalse(m.is_broadcast())
        m.to = None
        self.assertTrue(m.is_broadcast())

    def test_is_command(self):
        m = MessageRequest()
        m.command = 'acommand'
        m.to = 'dummy'

        self.assertTrue(m.is_command())
        m.command = None
        m.event = 'anevent'
        self.assertFalse(m.is_command())

    def test_is_external_event(self):
        m = MessageRequest()
        m.peer_infos = None

        self.assertFalse(m.is_external_event())
        m.peer_infos = {}
        self.assertTrue(m.is_external_event())

    def test_message_request_to_dict(self):
        m = MessageRequest()
        m.command = 'acommand'
        m.event = 'event.dummy.test'
        m.propagate = True
        m.params = { 'key': 'value', 'int': 666 }
        m.to = 'dummy'
        m.sender = 'otherdummy'
        m.device_id = '123-456-789'
        m.peer_infos = PeerInfos(ip='0.0.0.0', macs=['00-00-00-00-00-00'])

        # external command
        to_dict = m.to_dict()
        self.assertEqual(to_dict['command'], m.command)
        self.assertEqual(to_dict['params'], m.params)
        self.assertEqual(to_dict['to'], m.to)
        self.assertEqual(to_dict['sender'], None)
        self.assertEqual(to_dict['broadcast'], False)

        # external event
        m.command = None
        to_dict = m.to_dict()
        self.assertEqual(to_dict['event'], m.event)
        self.assertEqual(to_dict['params'], m.params)
        self.assertEqual(to_dict['startup'], False)
        self.assertEqual(to_dict['device_id'], None)
        self.assertEqual(to_dict['sender'], None)
        self.assertEqual(to_dict['peer_infos'], m.peer_infos.to_dict())

        m.peer_infos = None
        to_dict = m.to_dict()
        self.assertEqual(to_dict['event'], m.event)
        self.assertEqual(to_dict['params'], m.params)
        self.assertEqual(to_dict['startup'], False)
        self.assertEqual(to_dict['device_id'], m.device_id)
        self.assertEqual(to_dict['sender'], m.sender)

        with self.assertRaises(InvalidMessage) as cm:
            m.event = None
            m.to_dict()

    def test_fill_from_dict_internal_event(self):
        m = MessageRequest()
        m.fill_from_dict({
            'event': 'anevent',
            'propagate': False,
            'params': {'key': 'value', 'int': 666},
            'to': 'dummy',
            'sender': 'asender',
            'device_id': 'device_id',
            'peer_infos': None,
        })

        self.assertEqual(m.to_dict(), {
            'device_id': 'device_id',
            'event': 'anevent',
            'params': {
                'key': 'value',
                'int': 666,
            },
            'sender': 'asender',
            'startup': False,
            'to': 'dummy',
        })

    def test_fill_from_dict_external_event(self):
        m = MessageRequest()
        m.fill_from_dict({
            'event': 'anevent',
            'propagate': False,
            'params': {'key': 'value', 'int': 666},
            'to': 'dummy',
            'sender': 'asender',
            'device_id': 'device_id',
            'peer_infos': PeerInfos(ip='0.0.0.0', macs=['00-00-00-00-00-00']).to_dict(),
            'command_uuid': '1234567890',
        })

        self.assertEqual(m.to_dict(), {
            'command_uuid': '1234567890',
            'device_id': None,
            'event': 'anevent',
            'params': {
                'key': 'value',
                'int': 666,
            },
            'peer_infos': {
                'cleepdesktop': False,
                'hostname': None,
                'ident': None,
                'ip': '0.0.0.0',
                'macs': ['00-00-00-00-00-00'],
                'online': False,
                'port': 80,
                'ssl': False,
                'uuid': None
            },
            'sender': None,
            'startup': False
        })

    def test_fill_from_dict_internal_command(self):
        m = MessageRequest()
        m.fill_from_dict({
            'command': 'acommand',
            'propagate': False,
            'params': {'key': 'value', 'int': 666},
            'to': 'dummy',
            'sender': 'asender',
            'device_id': 'device_id',
            'peer_infos': None,
        })

        self.assertEqual(m.to_dict(), {
            'broadcast': False,
            'command': 'acommand',
            'params': {
                'key': 'value',
                'int': 666,
            },
            'sender': 'asender',
            'to': 'dummy',
        })

    def test_fill_from_dict_external_command(self):
        m = MessageRequest()
        m.fill_from_dict({
            'command': 'acommand',
            'propagate': False,
            'params': {'key': 'value', 'int': 666},
            'to': 'dummy',
            'sender': 'asender',
            'device_id': 'device_id',
            'peer_infos': PeerInfos(ip='0.0.0.0', macs=['00-00-00-00-00-00']).to_dict(),
            'command_uuid': '1234567890',
        })

        self.assertEqual(m.to_dict(), {
            'broadcast': False,
            'command_uuid': '1234567890',
            'command': 'acommand',
            'params': {
                'key': 'value',
                'int': 666,
            },
            'to': 'dummy',
            'peer_infos': {
                'cleepdesktop': False,
                'hostname': None,
                'ident': None,
                'ip': '0.0.0.0',
                'macs': ['00-00-00-00-00-00'],
                'online': False,
                'port': 80,
                'ssl': False,
                'uuid': None
            },
            'sender': None,
            'timeout': 5.0,
        })

    def test_fill_from_dict_exception(self):
        c = MessageRequest()

        with self.assertRaises(Exception) as cm:
            c.fill_from_dict(123)
        self.assertEqual(str(cm.exception), 'Parameter "request" must be a dict')

    def test_fill_from_request(self):
        c = MessageRequest(command='command', to='to', params={'param': 'value'})
        c.propagate = True
        c.timeout = 123.0
        c.peer_infos = PeerInfos(ip='0.0.0.0', macs=['00-00-00-00-00-00'], extra={'extra': 'value'})

        m = MessageRequest()
        m.fill_from_request(c)
        logging.debug('Filled: %s' % m.to_dict())

        self.assertEqual(m.command, 'command')
        self.assertEqual(m.to, 'to')
        self.assertEqual(m.params, {'param': 'value'})
        self.assertDictEqual(m.peer_infos.to_dict(True), {
            'ip': '0.0.0.0',
            'macs': ['00-00-00-00-00-00'],
            'ident': None,
            'uuid': None,
            'hostname': None,
            'online': False,
            'port': 80,
            'ssl': False,
            'extra': {'extra': 'value'},
            'cleepdesktop': False,
        })

    def test_fill_from_request_exception(self):
        c = MessageRequest()

        with self.assertRaises(Exception) as cm:
            c.fill_from_request({})
        self.assertEqual(str(cm.exception), 'Parameter "request" must be a MessageRequest instance')


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python*/*","*test_*.py" --concurrency=thread test_common.py; coverage report -m -i
    unittest.main()

