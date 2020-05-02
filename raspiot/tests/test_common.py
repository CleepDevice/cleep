#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests', ''))
from common import MessageResponse, MessageRequest, ExecutionStep
from raspiot.libs.tests.lib import TestLib
from raspiot.exception import InvalidMessage
import unittest
import logging


class ExecutionStepTest(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def test_execution_step(self):
        e = ExecutionStep()
        self.assertEqual(e.step, e.BOOT)



class MessageResponseTests(unittest.TestCase):

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

        self.assertEqual('%s' % m, '{error:True, message:"a message", data:{\'int\': 666, \'key\': \'value\'}, broadcast:True}')

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




class MessageRequestTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def test_message_request(self):
        m = MessageRequest()

        self.assertEqual(m.command, None)
        self.assertEqual(m.event, None)
        self.assertEqual(m.core_event, False)
        self.assertEqual(m.params, {})
        self.assertEqual(m.to, None)
        self.assertEqual(m.sender, None)
        self.assertEqual(m.device_id, None)
        self.assertEqual(m.peer_infos, None)

    def test_message_request_to_string(self):
        m = MessageRequest()
        m.command = 'acommand'
        m.event = 'event.dummy.test'
        m.core_event = True
        m.params = { 'key': 'value', 'int': 666 }
        m.to = 'dummy'
        m.sender = 'otherdummy'
        m.device_id = '123-456-789'
        m.peer_infos = { 'ip': '0.0.0.0', 'mac': '00-00-00-00-00-00' }

        self.assertEqual('%s' % m, '{command:acommand, params:{\'int\': 666, \'key\': \'value\'}, to:dummy, sender:otherdummy}')
        m.command = None
        self.assertEqual('%s' % m, '{event:event.dummy.test, core_event:True, params:{\'int\': 666, \'key\': \'value\'}, to:dummy, device_id:123-456-789, peer_infos:{\'ip\': \'0.0.0.0\', \'mac\': \'00-00-00-00-00-00\'}}')
        m.event = None
        self.assertEqual('%s' % m, 'Invalid message')

    def test_is_broadcast(self):
        m = MessageRequest()
        m.to = 'dummy'

        self.assertFalse(m.is_broadcast())
        m.to = None
        self.assertTrue(m.is_broadcast())

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
        m.core_event = True
        m.params = { 'key': 'value', 'int': 666 }
        m.to = 'dummy'
        m.sender = 'otherdummy'
        m.device_id = '123-456-789'
        m.peer_infos = { 'ip': '0.0.0.0', 'mac': '00-00-00-00-00-00' }

        #m.command = None
        #m.event = None

        to_dict = m.to_dict()
        self.assertEqual(to_dict['command'], m.command)
        self.assertEqual(to_dict['params'], m.params)
        self.assertEqual(to_dict['to'], m.to)
        self.assertEqual(to_dict['sender'], m.sender)
        self.assertEqual(to_dict['broadcast'], False)

        m.command = None
        to_dict = m.to_dict()
        self.assertEqual(to_dict['event'], m.event)
        self.assertEqual(to_dict['params'], m.params)
        self.assertEqual(to_dict['startup'], False)
        self.assertEqual(to_dict['device_id'], None)
        self.assertEqual(to_dict['sender'], 'PEER')
        self.assertEqual(to_dict['peer_infos'], m.peer_infos)

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

if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python2.7/*","*test_*.py" --concurrency=thread test_common.py; coverage report -m -i
    unittest.main()

