#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests', ''))
from bus import MessageBus, BusClient, deque, inspect
from cleep.libs.tests.lib import TestLib
from cleep.common import MessageRequest, MessageResponse
from cleep.exception import NoResponse, InvalidParameter, InvalidModule, NoMessageAvailable, BusError, CommandInfo, CommandError, InvalidMessage, NotReady
import unittest
import logging
from unittest.mock import Mock, patch
import time
from threading import Event, Thread

class DummyModule(Thread):
    def __init__(self, bus, response=None, name='dummy', manual_pull=False):
        """
        Params:
            bud (Bus): bus instance
            response (MessageResponse): message response instance
            name (string): module name
        """
        Thread.__init__(self, daemon=True)
        self.name = name
        self.bus = bus
        self.running = True
        self.response = response
        self._received_messages = []
        self._messages_to_send = []
        self._pulled_messages = 0
        self._last_exception = None
        self.manual_pull = manual_pull

    def stop(self):
        self.running = False

    def push(self, msg, timeout=3.0):
        msg.sender = self.name
        self._messages_to_send.append({
            'message': msg,
            'timeout': timeout
        })

    def pull(self, timeout=0.5):
        self.__pull(timeout)

    def last_response(self):
        if len(self._received_messages)==0:
            return None
        return self._received_messages.pop()

    def __pull(self, timeout=0.5):
        msg = self.bus.pull(self.name, timeout)
        self._pulled_messages += 1
        msg['response'] = self.response.to_dict() if self.response is not None else None
        logging.debug('DummyModule pulled %s' % msg)
        msg['event'].set()

    def run(self):
        while self.running:
            if len(self._messages_to_send)>0:
                try:
                    msg = self._messages_to_send.pop()
                    resp = self.bus.push(msg['message'], timeout=msg['timeout'])
                    logging.debug('DummyModule "%s" receive response %s' % (self.name, resp))
                    self._received_messages.append(resp)
                except Exception as e:
                    logging.exception('Exception pushing on DummyModule "%s": %s' % (self.name, e.__class__.__name__))
                    self._last_exception = e

            if not self.manual_pull:
                try:
                    self.__pull()
                except Exception as e:
                    if not isinstance(e, NoMessageAvailable):
                        logging.debug('Exception pulling on DummyModule "%s": %s' % (self.name, e.__class__.__name__))

            time.sleep(0.10)

    def pulled_messages(self):
        return self._pulled_messages

    def last_exception(self):
        return self._last_exception

class MessageBusTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.DEBUG, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.b = None
        self.mod1 = None
        self.mod2 = None

        self.dummy_response = MessageResponse()
        self.dummy_response.data = 'dummy test response'
        self.dummy_response.message = 'dummy message'
        self.dummy_response.error = True

    def tearDown(self):
        if self.b:
            self.b.STARTUP_TIMEOUT = self.STARTUP_TIMEOUT
            self.b.SUBSCRIPTION_LIFETIME = self.SUBSCRIPTION_LIFETIME
            self.b.stop()
        if self.mod1:
            self.mod1.stop()
        if self.mod2:
            self.mod2.stop()

    def _init_context(self):
        self.crash_report = Mock()
        self.b = MessageBus(self.crash_report, debug_enabled=False)
        self.STARTUP_TIMEOUT = self.b.STARTUP_TIMEOUT
        self.SUBSCRIPTION_LIFETIME = self.b.SUBSCRIPTION_LIFETIME

    def _get_message_request(self, command='dummycommand', params={}, to=None):
        msg = MessageRequest()
        msg.command = command
        msg.params = params
        msg.to = to
        return msg

    def test_debug_enabled(self):
        try:
            b = MessageBus(Mock(), debug_enabled=True)
            self.assertEqual(b.logger.getEffectiveLevel(), logging.DEBUG)
            b.stop()
        finally:
            # restore original log level
            b.logger.setLevel(logging.FATAL)

    def test_subscription(self):
        self._init_context()

        self.assertFalse(self.b.is_subscribed('dummy'))
        self.b.add_subscription('dummy')
        self.assertTrue(self.b.is_subscribed('dummy'))
        self.b.remove_subscription('dummy')
        self.assertFalse(self.b.is_subscribed('dummy'))

        with self.assertRaises(InvalidModule) as cm:
            self.b.remove_subscription('otherdummy')
        self.assertEqual(str(cm.exception), 'Invalid module "otherdummy" (not loaded or unknown)')

        self.b.SUBSCRIPTION_LIFETIME = 0
        self.b.add_subscription('dummy')
        self.b.add_subscription('otherdummy')
        self.assertTrue(self.b.is_subscribed('dummy'))
        self.assertTrue(self.b.is_subscribed('otherdummy'))
        time.sleep(1)
        self.b.purge_subscriptions()
        self.assertFalse(self.b.is_subscribed('dummy'))
        self.assertFalse(self.b.is_subscribed('otherdummy'))

    def test_push_to_recipient(self):
        self._init_context()
        self.mod1 = DummyModule(self.b, name='dummy')
        self.mod1.start()
        self.mod2 = DummyModule(self.b, name='otherdummy', response=self.dummy_response)
        self.mod2.start()

        self.b.add_subscription(self.mod1.name)
        self.b.add_subscription(self.mod2.name)
        self.b.app_configured()
        self.mod1.push(self._get_message_request(to='otherdummy'))
        time.sleep(0.5)

        self.assertEqual(self.mod2.pulled_messages(), 1)
        
    def test_push_to_rpc(self):
        self._init_context()
        self.mod1 = DummyModule(self.b, name='rpc-123456789')
        self.mod1.start()
        self.mod2 = DummyModule(self.b, name='rpc-987654321')
        self.mod2.start()

        self.b.add_subscription(self.mod1.name)
        self.b.add_subscription(self.mod2.name)
        self.b.app_configured()
        self.b.push(self._get_message_request(to='rpc'))
        time.sleep(0.5)
       
        self.assertEqual(self.mod1.pulled_messages(), 1)
        self.assertEqual(self.mod2.pulled_messages(), 1)

    def test_push_broadcast(self):
        self._init_context()

        self.b.add_subscription('dummy')
        self.b.app_configured()
        self.assertIsNone(self.b.push(self._get_message_request()))
        self.b.push(self._get_message_request())

        try:
            # 2 messages should be in queue
            self.b._queues['dummy'].pop()
            self.b._queues['dummy'].pop()
        except:
            self.fail('Should not trigger exception')

    def test_push_broadcast_do_not_send_to_myself(self):
        self._init_context()

        self.mod1 = DummyModule(self.b, name='dummy')
        self.mod1.start()
        self.mod2 = DummyModule(self.b, name='otherdummy')
        self.mod2.start()
        self.b.add_subscription(self.mod1.name)
        self.b.add_subscription(self.mod2.name)
        self.b.app_configured()

        self.mod1.push(self._get_message_request(to=None))
        time.sleep(0.75)
        
        self.assertEqual(self.mod1.pulled_messages(), 0)
        self.assertEqual(self.mod2.pulled_messages(), 1)

    def test_push_to_myself(self):
        self._init_context()
        
        self.mod1 = DummyModule(self.b, name='myself')
        self.mod1.start()
        self.b.add_subscription(self.mod1.name)
        self.b.app_configured()

        self.mod1.push(self._get_message_request(to='myself'))
        
        with self.assertRaises(Exception) as cm:
            self.b._queues['myself'].pop()
        self.assertEqual(self.mod1.pulled_messages(), 0)

    def test_push_to_rpc_when_app_not_configured(self):
        self._init_context()
        self.mod1 = DummyModule(self.b, name='rpc-123456789')
        self.mod1.start()

        self.b.add_subscription(self.mod1.name)
        self.assertIsNone(self.b.push(self._get_message_request(to='rpc')))
        time.sleep(0.5)
       
        self.assertEqual(self.mod1.pulled_messages(), 0)

    def test_push_deferred_broadcasted_messages(self):
        self._init_context()

        self.b.add_subscription('dummy')
        self.b.push(self._get_message_request())
        self.b.push(self._get_message_request())
        self.b.push(self._get_message_request())
        self.b.app_configured()
        time.sleep(0.25)

        try:
            # 3 messages should be in queue
            self.b._queues['dummy'].pop()
            self.b._queues['dummy'].pop()
            self.b._queues['dummy'].pop()
        except:
            self.fail('Should not trigger exception')

    def test_push_timeout(self):
        self._init_context()

        self.b.add_subscription('dummy')
        self.b.app_configured()
        with self.assertRaises(NoResponse) as cm:
            self.b.push(self._get_message_request(to='dummy'), timeout=0.25)

    def test_push_no_command_specified(self):
        self._init_context()

        self.b.add_subscription('dummy')
        self.b.app_configured()
        with self.assertRaises(InvalidMessage) as cm:
            self.b.push(self._get_message_request(command=None, to='dummy'))
        self.assertEqual(str(cm.exception), 'Invalid message')

    def test_push_no_timeout(self):
        self._init_context()
        
        self.mod1 = DummyModule(self.b, name='dummy')
        self.mod1.start()
        self.mod2 = DummyModule(self.b, name='otherdummy')
        self.mod2.start()
        self.b.add_subscription(self.mod1.name)
        self.b.add_subscription(self.mod2.name)

        self.mod1.push(self._get_message_request(to='otherdummy'), timeout=0.0)
        time.sleep(0.5)
        
        self.assertIsNone(self.mod1.last_response())
        self.assertEqual(self.mod2.pulled_messages(), 1)

    def test_push_to_unsubscribed_module_before_app_configured_with_timeout(self):
        self._init_context()

        self.mod1 = DummyModule(self.b, name='dummy')
        self.mod1.start()
        self.b.add_subscription(self.mod1.name)
        self.mod2 = DummyModule(self.b, name='otherdummy', response=self.dummy_response)
        self.mod2.start()
        
        self.mod1.push(self._get_message_request(to='otherdummy'))
        time.sleep(0.25)
        self.b.add_subscription(self.mod2.name)
        self.b.app_configured()
        
        time.sleep(0.5)
        last_response = self.mod1.last_response()
        logging.debug('Last response mod1: %s' % last_response)
        #self.assertEqual(last_response['data'], self.dummy_response.data)
        #self.assertEqual(last_response['error'], self.dummy_response.error)
        #self.assertEqual(last_response['message'], self.dummy_response.message)
        #logging.debug('Pulled messages mod2: %s' % self.mod2.pulled_messages())
        #self.assertEqual(self.mod2.pulled_messages(), 1)

    def test_push_to_unsubscribed_module_before_app_configured_without_timeout(self):
        self._init_context()

        self.mod1 = DummyModule(self.b, name='dummy')
        self.mod1.start()
        self.b.add_subscription(self.mod1.name)
        self.mod2 = DummyModule(self.b, name='otherdummy', response=self.dummy_response)
        self.mod2.start()
        
        self.mod1.push(self._get_message_request(to='otherdummy'), timeout=None)
        time.sleep(0.5)
        self.b.add_subscription(self.mod2.name)
        self.b.app_configured()
        
        time.sleep(0.5)
        last_response = self.mod1.last_response()
        logging.debug('Last response mod1: %s' % last_response)
        self.assertEqual(last_response, None)
        logging.debug('Pulled messages mod2: %s' % self.mod2.pulled_messages())
        self.assertEqual(self.mod2.pulled_messages(), 1)

    def test_push_to_unsubscribed_module_before_app_configured_timeout(self):
        self._init_context()
        self.b.STARTUP_TIMEOUT = 0.1

        self.mod1 = DummyModule(self.b, name='dummy')
        self.mod1.start()
        self.b.add_subscription(self.mod1.name)
        self.mod1.push(self._get_message_request(to='otherdummy'))

        time.sleep(0.5)
        self.mod2 = DummyModule(self.b, name='otherdummy', response=self.dummy_response)
        self.mod2.start()
        self.b.add_subscription(self.mod2.name)
        self.b.app_configured()
        
        time.sleep(0.5)
        last_response = self.mod1.last_response()
        logging.debug('Last response mod1: %s' % last_response)
        self.assertEqual(last_response, None)
        last_exception = self.mod1.last_exception()
        logging.debug('Last exception: "%s"' % last_exception)
        self.assertTrue(isinstance(last_exception, NoResponse))
        self.assertTrue(str(last_exception).startswith('No response from %s (%.1f seconds)' % (self.mod2.name, self.b.STARTUP_TIMEOUT)))

    def test_push_while_stopped(self):
        self._init_context()

        self.b.add_subscription('dummy')
        self.b.app_configured()
        self.b.stop()
        
        # broadcast message
        with self.assertRaises(Exception) as cm:
            self.b.push(self._get_message_request())
        self.assertEqual(str(cm.exception), 'Bus stopped')

        # message with recipient
        with self.assertRaises(Exception) as cm:
            self.b.push(self._get_message_request(to='dummy'))
        self.assertEqual(str(cm.exception), 'Bus stopped')

    def test_push_invalid_parameters(self):
        self._init_context()

        self.b.add_subscription('dummy')
        self.b.app_configured()

        with self.assertRaises(InvalidParameter) as cm:
            self.b.push({'dummy': 666})
        logging.debug('Exception: %s' % str(cm.exception))
        self.assertEqual(str(cm.exception), 'Parameter "request" must be MessageRequest instance')

    def test_push_invalid_module(self):
        self._init_context()

        self.b.add_subscription('dummy')
        self.b.app_configured()

        with self.assertRaises(InvalidModule) as cm:
            self.b.push(self._get_message_request(to='otherdummy'))
        self.assertEqual(str(cm.exception), 'Invalid module "otherdummy" (not loaded or unknown)')

    def test_stop_broadcasted_messages(self):
        self._init_context()

        self.b.add_subscription('dummy')
        self.b.app_configured()
        self.b.push(self._get_message_request())
        self.b.push(self._get_message_request())
        time.sleep(0.25)
        self.b.stop()

        with self.assertRaises(IndexError) as cm:
            self.b._queues['dummy'].pop()

    def test_pull_with_timeout(self):
        self._init_context()

        self.mod1 = DummyModule(self.b, name='dummy')
        self.mod1.start()
        self.mod2 = DummyModule(self.b, name='otherdummy')
        self.mod2.start()
        self.b.add_subscription(self.mod1.name)
        self.b.add_subscription(self.mod2.name)
        self.b.app_configured()

        self.mod1.push(self._get_message_request(to=self.mod2.name))
        time.sleep(0.5)
        
        self.assertEqual(self.mod1.pulled_messages(), 0)
        self.assertEqual(self.mod2.pulled_messages(), 1)

    @patch('bus.deque')
    def test_pull_with_timeout_exception(self, deque_mock):
        deque_mock.return_value.pop = Mock(side_effect=Exception('Test exception'))
        self._init_context()

        self.mod1 = DummyModule(self.b, name='dummy')
        self.mod1.start()
        self.mod2 = DummyModule(self.b, name='otherdummy')
        self.mod2.start()
        self.b.add_subscription(self.mod1.name)
        self.b.add_subscription(self.mod2.name)
        self.b.app_configured()

        self.mod1.push(self._get_message_request(to=self.mod2.name))
        time.sleep(0.25)
        
        with self.assertRaises(BusError) as cm:
            self.mod2.pull(None)

    def test_pull_with_timeout_no_message(self):
        self._init_context()

        self.mod1 = DummyModule(self.b, name='dummy')
        self.mod1.start()
        self.mod2 = DummyModule(self.b, name='otherdummy')
        self.mod2.start()
        self.b.add_subscription(self.mod1.name)
        self.b.add_subscription(self.mod2.name)
        self.b.app_configured()

        with self.assertRaises(NoMessageAvailable) as cm:
            self.mod2.pull(timeout=0.1)

    def test_pull_without_timeout(self):
        self._init_context()

        self.mod1 = DummyModule(self.b, name='dummy')
        self.mod1.start()
        self.mod2 = DummyModule(self.b, name='otherdummy', manual_pull=True, response=self.dummy_response)
        self.mod2.start()
        self.b.add_subscription(self.mod1.name)
        self.b.add_subscription(self.mod2.name)
        self.b.app_configured()

        self.mod1.push(self._get_message_request(to=self.mod2.name))
        time.sleep(0.25)
        self.mod2.pull(None)
        time.sleep(0.25)
        
        self.assertEqual(self.mod2.pulled_messages(), 1)
        last_response = self.mod1.last_response()
        logging.debug(last_response)
        self.assertEqual(last_response['data'], self.dummy_response.data)

    def test_pull_without_timeout_no_message(self):
        self._init_context()

        self.mod1 = DummyModule(self.b, name='dummy')
        self.mod1.start()
        self.mod2 = DummyModule(self.b, name='otherdummy', manual_pull=True, response=self.dummy_response)
        self.mod2.start()
        self.b.add_subscription(self.mod1.name)
        self.b.add_subscription(self.mod2.name)
        self.b.app_configured()
    
        with self.assertRaises(NoMessageAvailable) as cm:
            self.mod2.pull(None)
        with self.assertRaises(NoMessageAvailable) as cm:
            self.mod2.pull(0.0)

    @patch('bus.deque')
    def test_pull_without_timeout_exception(self, deque_mock):
        deque_mock.return_value.pop = Mock(side_effect=Exception('Test exception'))
        self._init_context()

        self.mod1 = DummyModule(self.b, name='dummy')
        self.mod1.start()
        self.mod2 = DummyModule(self.b, name='otherdummy', manual_pull=True, response=self.dummy_response)
        self.mod2.start()
        self.b.add_subscription(self.mod1.name)
        self.b.add_subscription(self.mod2.name)
        self.b.app_configured()

        with self.assertRaises(BusError) as cm:
            self.mod2.pull(None)





class TestProcess1(BusClient):
    def __init__(self, bus, custom_process=None, configure=None):
        BusClient.__init__(self, bus)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.__command_calls = {}
        self.custom_process = custom_process
        self.configure = configure

    def _custom_process(self):
        if self.custom_process:
            self.custom_process()

    def _configure(self):
        if self.configure:
            self.configure()

    def __command_call(self, command):
        if command not in self.__command_calls:
            self.__command_calls[command] = 0
        self.__command_calls[command] += 1

    def _get_command_calls(self, command):
        if command in self.__command_calls:
            return self.__command_calls[command]
        return 0

    def command_without_params(self):
        self.__command_call('command_without_params')
        return 'command without params'
  
    def command_with_params(self, p1, p2):
        self.__command_call('command_with_params')
        return 'command with params: %s %s' % (p1, p2)

    def command_broadcast(self, param):
        self.__command_call('command_broadcast')
        return 'command broadcast wih param=%s' % (unicode(param))

    def _event_received(self, event):
        self.__command_call('event_received')
        self.logger.debug('Event received: %s' % event)


class TestProcess2(BusClient):
    def __init__(self, bus):
        BusClient.__init__(self, bus)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.__command_calls = {}

    def __command_call(self, command):
        if command not in self.__command_calls:
            self.__command_calls[command] = 0
        self.__command_calls[command] += 1

    def _get_command_calls(self, command):
        if command in self.__command_calls:
            return self.__command_calls[command]
        return 0

    def command_timeout(self):
        self.__command_call('command_timeout')
        time.sleep(3.5)
        return 'command_timeout'

    def command_broadcast(self, param):
        self.__command_call('command_broadcast')
        return 'command broadcast wih param=%s' % (unicode(param))

    def command_exception(self):
        raise Exception('Test exception')

    def command_info(self):
        raise CommandInfo('Command info')

    def command_error(self):
        raise CommandError('Command error')

    def command_sender(self, command_sender):
        return 'command_sender=%s' % command_sender

    def command_default_params(self, param1, param2='default'):
        return {
            'param1': param1,
            'param2': param2,
        }

    def _event_received(self, event):
        self.__command_call('event_received')
        self.logger.debug('Event received: %s' % event)

class TestProcess3(BusClient):
    def __init__(self, bus):
        BusClient.__init__(self, bus)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.__command_calls = {}

    def __command_call(self, command):
        if command not in self.__command_calls:
            self.__command_calls[command] = 0
        self.__command_calls[command] += 1

    def _get_command_calls(self, command):
        if command in self.__command_calls:
            return self.__command_calls[command]
        return 0

    def _event_received(self, event):
        self.__command_call('event_received')
        raise Exception('Test exception')

class BusClientTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        if self.p1:
            self.p1.stop()
        if self.p2:
            self.p2.stop()
        if self.bus:
            self.bus.stop()
        if self.p3:
            self.p3.stop()

    def _init_context(self, p1_custom_process=None, p1_configure=None):
        self.crash_report = Mock()
        self.bus = MessageBus(self.crash_report, debug_enabled=False)
        self.bootstrap = {
            'message_bus': self.bus,
            'module_join_event': Mock(),
            'core_join_event': Mock(),
            'crash_report': self.crash_report,
        }

        self.p1 = TestProcess1(self.bootstrap, custom_process=p1_custom_process, configure=p1_configure)
        self.p1.start()
        self.p2 = TestProcess2(self.bootstrap)
        self.p2.start()
        self.p3 = None

        time.sleep(0.25)
        self.bus.app_configured()

    def _get_message_request(self, command='dummycommand', params={}, to=None):
        msg = MessageRequest()
        msg.command = command
        msg.params = params
        msg.to = to
        return msg

    def test_send_command_with_result(self):
        self._init_context()

        resp = self.p2.send_command(command='command_with_params', params={'p1':'hello', 'p2':'world'}, to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, dict))
        self.assertIsNotNone(resp)
        self.assertEqual(resp['data'], 'command with params: hello world')
        self.assertFalse(resp['error'])

    def test_send_command_with_invalid_command_parameters(self):
        self._init_context()

        resp = self.p2.send_command(command='command_with_params', params={'p1':'hello'}, to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, dict))
        self.assertIsNotNone(resp)
        self.assertTrue(resp['error'])
        self.assertEqual(resp['message'], 'Some command parameters are missing')

    def test_send_command_to_unknown_module(self):
        self._init_context()

        with self.assertRaises(InvalidModule) as cm:
            self.p1.send_command(command='command_with_params', params={'param1':'hello'}, to='dummy')
        self.assertEqual(str(cm.exception), 'Invalid module "dummy" (not loaded or unknown)')

    def test_send_command_invalid_command(self):
        self._init_context()

        resp = self.p1.send_command(command='command_unknown', params={'p1':'hello', 'p2':'world'}, to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, dict))
        self.assertIsNotNone(resp)
        self.assertEqual(resp['data'], None)
        self.assertTrue(resp['error'])
        self.assertEqual(resp['message'], 'Command "command_unknown" doesn\'t exist in "testprocess2" module')

    def test_send_broadcast_command(self):
        self._init_context()

        resp = self.p2.send_command(command='command_broadcast', params={'param':'hello'}, to=None)
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        time.sleep(0.5)

        self.assertTrue(isinstance(resp, dict))
        self.assertIsNone(resp['data'])
        self.assertEqual(self.p1._get_command_calls('command_broadcast'), 1)
        self.assertEqual(self.p2._get_command_calls('command_broadcast'), 0)

    def test_send_command_to_myself(self):
        self._init_context()

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, dict))
        self.assertIsNotNone(resp['data'])
        self.assertEqual(resp['data'], 'command without params')

    def test_send_command_with_exception(self):
        self._init_context()

        resp = self.p1.send_command(command='command_exception', to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, dict))
        self.assertTrue(resp['error'])
        self.assertEqual(resp['message'], 'Test exception')
        self.assertIsNone(resp['data'])

    def test_send_command_to_myself_with_exception(self):
        self._init_context()

        resp = self.p2.send_command(command='command_exception', to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, dict))
        self.assertTrue(resp['error'])
        self.assertEqual(resp['message'], 'Test exception')
        self.assertIsNone(resp['data'])

    def test_send_command_to_myself_with_invalid_command_parameters(self):
        self._init_context()

        resp = self.p1.send_command(command='command_with_params', params={'p1':'hello'}, to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, dict))
        self.assertIsNotNone(resp)
        self.assertTrue(resp['error'])
        self.assertEqual(resp['message'], 'Some command parameters are missing')

    def test_send_command_to_myself_invalid_command(self):
        self._init_context()

        resp = self.p1.send_command(command='command_unknown', params={'p1':'hello', 'p2':'world'}, to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, dict))
        self.assertIsNotNone(resp)
        self.assertEqual(resp['data'], None)
        self.assertTrue(resp['error'])
        self.assertEqual(resp['message'], 'Command "command_unknown" doesn\'t exist in "testprocess1" module')

    @patch('inspect.signature')
    def test_send_command_to_myself_exception(self, signature_mock):
        signature_mock.side_effect = Exception('Test exception')
        self._init_context()

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, dict))
        self.assertIsNone(resp['data'])
        self.assertTrue(resp['error'])
        self.assertEqual(resp['message'], 'Internal error')

    def test_send_command_with_commanderror(self):
        self._init_context()

        resp = self.p1.send_command(command='command_error', to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, dict))
        self.assertTrue(resp['error'])
        self.assertEqual(resp['message'], 'Command error')
        self.assertIsNone(resp['data'])

    def test_send_command_with_commandinfo(self):
        self._init_context()

        resp = self.p1.send_command(command='command_info', to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, dict))
        self.assertFalse(resp['error'])
        self.assertEqual(resp['message'], 'Command info')
        self.assertIsNone(resp['data'])

    def test_custom_process_called(self):
        class Context():
            call_count = 0

        def custom_process():
            Context.call_count += 1

        self._init_context(p1_custom_process=custom_process)

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertEqual(Context.call_count, 1)

    def test_custom_process_exception(self):
        def custom_process():
            raise Exception('Test exception')

        self._init_context(p1_custom_process=custom_process)

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(self.crash_report.report_exception.called)
        self.assertEqual(self.crash_report.report_exception.call_count, 1)

    def test_configure_called(self):
        class Context():
            call_count = 0

        def configure():
            Context.call_count += 1

        self._init_context(p1_configure=configure)

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertEqual(Context.call_count, 1)

    def test_configure_exception(self):
        def configure():
            raise Exception('Test exception')

        self._init_context(p1_configure=configure)

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(self.crash_report.report_exception.called)
        self.assertEqual(self.crash_report.report_exception.call_count, 1)

    def test_push_invalid_parameters(self):
        self._init_context()

        with self.assertRaises(InvalidParameter) as cm:
            self.p1.push({})
        self.assertEqual(str(cm.exception), 'Request parameter must be MessageRequest instance')

        with self.assertRaises(InvalidParameter) as cm:
            self.p1.push(123)
        self.assertEqual(str(cm.exception), 'Request parameter must be MessageRequest instance')

        with self.assertRaises(InvalidParameter) as cm:
            self.p1.push('hello')
        self.assertEqual(str(cm.exception), 'Request parameter must be MessageRequest instance')

    def test_push_to_myself(self):
        self._init_context()

        with self.assertRaises(Exception) as cm:
            self.p1.push(self._get_message_request(to='testprocess1'))
        self.assertEqual(str(cm.exception), 'Unable to send message to same module')

    def test_command_sender_filled(self):
        self._init_context()

        resp = self.p1.send_command(command='command_sender', to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertEqual(resp['data'], 'command_sender=testprocess1')

    def test_send_command_default_params(self):
        self._init_context()

        resp = self.p1.send_command(command='command_default_params', params={'param1': 123}, to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        self.assertEqual(resp['data']['param1'], 123)
        self.assertEqual(resp['data']['param2'], 'default')

        resp = self.p1.send_command(command='command_default_params', params={'param1': 123, 'param2': 789}, to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        self.assertEqual(resp['data']['param1'], 123)
        self.assertEqual(resp['data']['param2'], 789)

    def test_send_event(self):
        self._init_context()
        event = 'event.dummy.test'

        resp = self.p2.send_event(event, {'p1': 'event'})
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        time.sleep(0.5)

        self.assertTrue(isinstance(resp, dict))
        self.assertIsNone(resp['data'])
        self.assertEqual(self.p1._get_command_calls('event_received'), 1)
        self.assertEqual(self.p2._get_command_calls('event_received'), 0)

    def test_send_external_event(self):
        self._init_context()
        event = 'event.dummy.test'

        resp = self.p2.send_external_event(event, {'p1': 'event'}, peer_infos={'ip':'1.2.3.4'})
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        time.sleep(0.5)

        self.assertTrue(isinstance(resp, dict))
        self.assertIsNone(resp['data'])
        self.assertEqual(self.p1._get_command_calls('event_received'), 1)
        self.assertEqual(self.p2._get_command_calls('event_received'), 0)

    def test_send_event_with_exception(self):
        self._init_context()
        self.p3 = TestProcess3(self.bootstrap)
        self.p3.start()
        time.sleep(0.5)
        event = 'event.dummy.test'

        resp = self.p2.send_event(event, {'p1': 'event'}, to='testprocess3')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        time.sleep(0.5)

        self.assertTrue(isinstance(resp, dict))
        self.assertIsNone(resp['data'])
        


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python*/*","*test_*.py" --concurrency=thread test_bus.py; coverage report -m -i
    unittest.main()

