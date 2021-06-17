#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from externalbus import ExternalBus
from cleep.libs.tests.lib import TestLib
from cleep.exception import MissingParameter, InvalidParameter
from cleep.common import MessageRequest, MessageResponse, PeerInfos
from threading import Event
import unittest
import logging
from unittest.mock import Mock, patch


class ExternalBusTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        pass

    def init_lib(self, on_message_received=None, on_peer_connected=None, on_peer_disconnected=None, debug=None):
        self.crash_report = Mock()
        self.on_message_received = on_message_received or Mock(return_value=None)
        self.on_peer_connected = on_peer_connected or Mock()
        self.on_peer_disconnected = on_peer_disconnected or Mock()

        if debug is None:
            debug = logging.getLogger().getEffectiveLevel() == logging.DEBUG

        self.bus = ExternalBus(
            on_message_received=self.on_message_received,
            on_peer_connected=self.on_peer_connected,
            on_peer_disconnected=self.on_peer_disconnected,
            debug_enabled=debug,
            crash_report=self.crash_report,
        )
        
    def test_debug_enabled(self):
        self.init_lib(debug=True)

        self.assertEqual(self.bus.logger.getEffectiveLevel(), logging.DEBUG)

    def test_debug_disabled(self):
        self.init_lib(debug=False)

        self.assertEqual(self.bus.logger.getEffectiveLevel(), logging.INFO)

    def test_run(self):
        self.init_lib()

        with self.assertRaises(NotImplementedError) as cm:
            self.bus.run()
        self.assertEqual(str(cm.exception), 'run function must be implemented in "ExternalBus"')

    def test_run_once(self):
        self.init_lib()

        with self.assertRaises(NotImplementedError) as cm:
            self.bus.run_once()
        self.assertEqual(str(cm.exception), 'run_once function must be implemented in "ExternalBus"')

    def test_on_message_received(self):
        self.init_lib()
        request = MessageRequest(command='mycommand', params={'param':'value'})

        self.bus.on_message_received('123-456-789', request)

        self.on_message_received.assert_called_with('123-456-789', request)    

    def test_on_message_received_ack_command(self):
        self.init_lib()
        manual_response = Mock()
        self.bus._ExternalBus__manual_responses = {
            '1234567890': {
                'manual_response': manual_response
            },
        }
        request = MessageRequest(event=ExternalBus.COMMAND_RESPONSE_EVENT, params={'data': 'command response'})
        request.command_uuid = '1234567890'

        self.bus.on_message_received('123-456-789', request)

        self.assertFalse(self.on_message_received.called)
        self.assertTrue(manual_response.called)
        call_arg = manual_response.call_args[0]
        logging.debug('Call arg: %s' % call_arg)
        self.assertDictEqual(call_arg[0].to_dict(), {
            'error': False,
            'message': '',
            'data': 'command response',
        })
        self.assertEqual(len(self.bus._ExternalBus__manual_responses), 0)

    def test_on_message_received_ack_command_invalid_command_uuid(self):
        self.init_lib()
        manual_response = Mock()
        self.bus._ExternalBus__manual_responses = {}
        request = MessageRequest(event=ExternalBus.COMMAND_RESPONSE_EVENT, params={'data': 'command response'})
        request.command_uuid = '1234567890'

        self.bus.on_message_received('123-456-789', request)

        self.assertFalse(self.on_message_received.called)
        self.assertFalse(manual_response.called)

    def test_on_message_received_process_event(self):
        self.init_lib()
        
        request = MessageRequest(event='my.dummy.event')
        self.bus.on_message_received('123-456-789', request)
        
        self.on_message_received.assert_called_with('123-456-789', request)

    def test_on_message_received_process_command(self):
        response = MessageResponse(data='command response')
        on_message_received = Mock(return_value=response)
        self.init_lib(on_message_received=on_message_received)
        self.bus._send_command_response_to_peer = Mock()
        
        request = MessageRequest(command='mycommand')
        request.command_uuid = '666'
        self.bus.on_message_received('123-456-789', request)
        
        on_message_received.assert_called_with('123-456-789', request)
        self.bus._send_command_response_to_peer.assert_called_with(request, response)

    def test_on_message_received_process_command_invalid_response(self):
        response = 'command response'
        on_message_received = Mock(return_value=response)
        self.init_lib(on_message_received=on_message_received)
        self.bus._send_command_response_to_peer = Mock()
        
        request = MessageRequest(command='mycommand')
        request.command_uuid = '666'
        with self.assertRaises(Exception) as cm:
            self.bus.on_message_received('123-456-789', request)
        self.assertEqual(str(cm.exception), 'Command response must be a MessageResponse instance not "str"')

    def test_on_message_received_process_command_no_command_uuid(self):
        response = 'command response'
        on_message_received = Mock(return_value=response)
        self.init_lib(on_message_received=on_message_received)
        self.bus._send_command_response_to_peer = Mock()
        
        request = MessageRequest(command='mycommand')
        self.bus.on_message_received('123-456-789', request)

        self.assertFalse(self.bus._send_command_response_to_peer.called)

    def test_send_command_response_to_peer(self):
        self.init_lib()
        request = MessageRequest(command='mycommand')
        request.command_uuid = '666'
        response = MessageResponse(data='command response')
        self.bus._send_message = Mock()

        self.bus._send_command_response_to_peer(request, response)

        self.assertTrue(self.bus._send_message.called)
        call_arg = self.bus._send_message.call_args[0]
        logging.debug('Call arg: %s' % call_arg)
        self.assertDictEqual(call_arg[0].to_dict(), {
            'device_id': None,
            'event': ExternalBus.COMMAND_RESPONSE_EVENT,
            'params': {
                'error': False,
                'message': '',
                'data': 'command response',
            },
            'sender': None,
            'startup': False,
            'propagate': False,
            'to': None,
        })

    def test_send_message_command(self):
        self.init_lib()
        request = MessageRequest(command='mycommand')
        self.bus._send_message = Mock()
        self.bus._broadcast_message = Mock()
        manual_response = Mock()

        self.bus.send_message(request, manual_response=manual_response)

        self.bus._send_message.assert_called_with(request)
        self.assertFalse(self.bus._broadcast_message.called)
        call_arg = self.bus._send_message.call_args[0]
        logging.debug('Call arg: %s' % call_arg)
        self.assertIsNotNone(call_arg[0].command_uuid)
        self.assertEqual(len(self.bus._ExternalBus__manual_responses), 1)
        self.assertEqual(list(self.bus._ExternalBus__manual_responses.keys())[0], call_arg[0].command_uuid)
        
    def test_send_message_event(self):
        self.init_lib()
        request = MessageRequest(event='my.dummy.event')
        request.peer_infos = PeerInfos(uuid='666')
        self.bus._send_message = Mock()
        self.bus._broadcast_message = Mock()
        manual_response = Mock()

        self.bus.send_message(request)

        self.bus._send_message.assert_called_with(request)
        self.assertFalse(self.bus._broadcast_message.called)

    def test_send_message_event_broadcast(self):
        self.init_lib()
        request = MessageRequest(event='my.dummy.event')
        self.bus._send_message = Mock()
        self.bus._broadcast_message = Mock()
        manual_response = Mock()

        self.bus.send_message(request)

        self.assertFalse(self.bus._send_message.called)
        self.bus._broadcast_message.assert_called_with(request)

    def test_broadcast_message(self):
        self.init_lib()

        with self.assertRaises(NotImplementedError) as cm:
            self.bus._broadcast_message(MessageRequest())
        self.assertEqual(str(cm.exception), 'broadcast_message function is not implemented "ExternalBus"')

    def test_send_message(self):
        self.init_lib()

        with self.assertRaises(NotImplementedError) as cm:
            self.bus._send_message(MessageRequest())
        self.assertEqual(str(cm.exception), 'send_message function is not implemented "ExternalBus"')
        


if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_externalbus.py; coverage report -m -i
    unittest.main()

