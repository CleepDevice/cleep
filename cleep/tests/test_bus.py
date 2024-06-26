#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.tests.lib import TestLib
import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests', ''))
from bus import MessageBus, BusClient, deque, inspect
from cleep.common import MessageRequest, MessageResponse
from cleep.exception import NoResponse, InvalidParameter, InvalidModule, NoMessageAvailable, BusError, CommandInfo, CommandError, InvalidMessage, NotReady
from cleep.libs.internals.taskfactory import TaskFactory
import unittest
import logging
from unittest.mock import Mock, patch
from gevent import sleep
from threading import Event, Thread
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()

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
        self.internal_bus = bus
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
        msg = self.internal_bus.pull(self.name, timeout)
        self._pulled_messages += 1
        msg['response'] = self.response.to_dict() if self.response is not None else None
        logging.debug('DummyModule pulled %s' % msg)
        msg['event'].set()

    def run(self):
        while self.running:
            if len(self._messages_to_send)>0:
                try:
                    msg = self._messages_to_send.pop()
                    resp = self.internal_bus.push(msg['message'], timeout=msg['timeout'])
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

            sleep(0.10)

    def pulled_messages(self):
        return self._pulled_messages

    def last_exception(self):
        return self._last_exception

class MessageBusTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
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
        self.task_factory = TaskFactory({
            "app_stop_event": Event()
        })

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
        self.assertEqual(str(cm.exception), 'Invalid application "otherdummy" (not loaded or unknown)')

        self.b.SUBSCRIPTION_LIFETIME = 0
        self.b.add_subscription('dummy')
        self.b.add_subscription('otherdummy')
        self.assertTrue(self.b.is_subscribed('dummy'))
        self.assertTrue(self.b.is_subscribed('otherdummy'))
        sleep(1)
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
        self.b.app_configured(self.task_factory)
        self.mod1.push(self._get_message_request(to='otherdummy'))
        sleep(0.5)

        self.assertEqual(self.mod2.pulled_messages(), 1)
        
    def test_push_to_rpc(self):
        self._init_context()
        self.mod1 = DummyModule(self.b, name='rpc-123456789')
        self.mod1.start()
        self.mod2 = DummyModule(self.b, name='rpc-987654321')
        self.mod2.start()

        self.b.add_subscription(self.mod1.name)
        self.b.add_subscription(self.mod2.name)
        self.b.app_configured(self.task_factory)
        self.b.push(self._get_message_request(to='rpc'))
        sleep(0.5)
       
        self.assertEqual(self.mod1.pulled_messages(), 1)
        self.assertEqual(self.mod2.pulled_messages(), 1)

    def test_push_broadcast(self):
        self._init_context()

        self.b.add_subscription('dummy')
        self.b.app_configured(self.task_factory)
        resp = self.b.push(self._get_message_request())
        self.b.push(self._get_message_request())
        self.assertTrue(isinstance(resp, MessageResponse))

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
        self.b.app_configured(self.task_factory)

        self.mod1.push(self._get_message_request(to=None))
        sleep(0.75)
        
        self.assertEqual(self.mod1.pulled_messages(), 0)
        self.assertEqual(self.mod2.pulled_messages(), 1)

    def test_push_to_myself(self):
        self._init_context()
        
        self.mod1 = DummyModule(self.b, name='myself')
        self.mod1.start()
        self.b.add_subscription(self.mod1.name)
        self.b.app_configured(self.task_factory)

        self.mod1.push(self._get_message_request(to='myself'))
        
        with self.assertRaises(Exception) as cm:
            self.b._queues['myself'].pop()
        self.assertEqual(self.mod1.pulled_messages(), 0)

    def test_push_timeout(self):
        self._init_context()

        self.b.add_subscription('dummy')
        self.b.app_configured(self.task_factory)
        with self.assertRaises(NoResponse) as cm:
            self.b.push(self._get_message_request(to='dummy'), timeout=0.25)

    def test_push_no_command_specified(self):
        self._init_context()

        self.b.add_subscription('dummy')
        self.b.app_configured(self.task_factory)
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
        self.b.app_configured(self.task_factory)
        sleep(0.5)
        
        self.assertTrue(isinstance(self.mod1.last_response(), MessageResponse))
        self.assertEqual(self.mod2.pulled_messages(), 1)

    def test_push_to_unsubscribed_module_before_app_configured_timeout(self):
        self._init_context()
        self.b.STARTUP_TIMEOUT = 0.1

        self.mod1 = DummyModule(self.b, name='dummy')
        self.mod1.start()
        self.b.add_subscription(self.mod1.name)
        self.mod1.push(self._get_message_request(to='otherdummy'))

        sleep(0.5)
        self.mod2 = DummyModule(self.b, name='otherdummy', response=self.dummy_response)
        self.mod2.start()
        self.b.add_subscription(self.mod2.name)

        self.b.app_configured(self.task_factory)
        sleep(0.5)

        last_response = self.mod1.last_response()
        logging.debug('Last response mod1: %s' % last_response)
        self.assertEqual(last_response, None)
        last_exception = self.mod1.last_exception()
        logging.debug('Last exception: "%s"' % last_exception)
        self.assertTrue(isinstance(last_exception, Exception))
        self.assertEqual(
            str(last_exception),
            'Pushing messages to internal bus is possible only when application is running. If this message appears during Cleep startup it means you try to send a message from module constructor or _configure method, if that is the case prefer using _on_start method.'
        )

    def test_push_while_stopped(self):
        self._init_context()

        self.b.add_subscription('dummy')
        self.b.app_configured(self.task_factory)
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
        self.b.app_configured(self.task_factory)

        with self.assertRaises(InvalidParameter) as cm:
            self.b.push({'dummy': 666})
        logging.debug('Exception: %s' % str(cm.exception))
        self.assertEqual(str(cm.exception), 'Parameter "request" must be MessageRequest instance')

    def test_push_invalid_module(self):
        self._init_context()

        self.b.add_subscription('dummy')
        self.b.app_configured(self.task_factory)

        with self.assertRaises(InvalidModule) as cm:
            self.b.push(self._get_message_request(to='otherdummy'))
        self.assertEqual(str(cm.exception), 'Invalid application "otherdummy" (not loaded or unknown)')

    def test_stop_broadcasted_messages(self):
        self._init_context()

        self.b.add_subscription('dummy')
        self.b.app_configured(self.task_factory)
        self.b.push(self._get_message_request())
        self.b.push(self._get_message_request())
        sleep(0.25)
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
        self.b.app_configured(self.task_factory)

        self.mod1.push(self._get_message_request(to=self.mod2.name))
        sleep(0.5)
        
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
        self.b.app_configured(self.task_factory)

        self.mod1.push(self._get_message_request(to=self.mod2.name))
        sleep(0.25)
        
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
        self.b.app_configured(self.task_factory)

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
        self.b.app_configured(self.task_factory)

        self.mod1.push(self._get_message_request(to=self.mod2.name))
        sleep(0.25)
        self.mod2.pull(None)
        sleep(0.25)
        
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
        self.b.app_configured(self.task_factory)
    
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
        self.b.app_configured(self.task_factory)

        with self.assertRaises(BusError) as cm:
            self.mod2.pull(None)





class TestProcess1(BusClient):
    def __init__(self, bootstrap, on_process=None, on_configure=None, on_stop=None, on_start=None):
        BusClient.__init__(self, 'testprocess1', bootstrap)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.__command_calls = {}
        self.on_process = on_process
        self.on_configure = on_configure
        self.on_stop = on_stop
        self.on_start = on_start

    def _on_process(self):
        logging.debug('TestProcess1: on_process')
        if self.on_process:
            self.on_process()

    def _on_start(self):
        logging.debug('TestProcess1: on_start')
        if self.on_start:
            self.on_start()

    def _on_stop(self):
        logging.debug('TestProcess1: on_stop')
        if self.on_stop:
            self.on_stop()

    def _configure(self):
        logging.debug('TestProcess1: configure')
        if self.on_configure:
            self.on_configure()

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
        return 'command broadcast wih param=%s' % param

    def _on_event(self, event):
        self.logger.debug('Event received: %s' % event)
        self.__command_call('on_event')


class TestProcess2(BusClient):
    def __init__(self, bootstrap):
        BusClient.__init__(self, 'testprocess2', bootstrap)
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
        sleep(3.5)
        return 'command_timeout'

    def command_broadcast(self, param):
        self.__command_call('command_broadcast')
        return 'command broadcast wih param=%s' % param

    def command_exception(self):
        raise Exception('Test exception')

    def command_info(self):
        raise CommandInfo('Command info')

    def command_error(self):
        raise CommandError('Command error')

    def command_sender(self, command_sender):
        return 'command_sender=%s' % command_sender

    def manual_response(self, manual_response, response=None, exception=None):
        if exception:
            raise Exception('Test exception in manual_response')
        if response:
            manual_response(response)

    def command_default_params(self, param1, param2='default'):
        return {
            'param1': param1,
            'param2': param2,
        }

    def _on_event(self, event):
        self.__command_call('on_event')
        self.logger.debug('Event received: %s' % event)

class TestProcess3(BusClient):
    def __init__(self, bootstrap):
        BusClient.__init__(self, 'testprocess3', bootstrap)
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

    def _on_event(self, event):
        self.__command_call('on_event')
        raise Exception('Test exception')

class BusClientTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        if self.p1:
            self.p1.stop()
        if self.p2:
            self.p2.stop()
        if self.internal_bus:
            self.internal_bus.stop()
        if self.p3:
            self.p3.stop()

    def _init_context(self, p1_on_process=None, p1_on_configure=None, p1_on_stop=None, p1_on_start=None):
        self.crash_report = Mock()
        self.task_factory = TaskFactory({
            "app_stop_event": Event()
        })
        self.internal_bus = MessageBus(self.crash_report, debug_enabled=False)
        self.bootstrap = {
            'internal_bus': self.internal_bus,
            'module_join_event': Mock(),
            'core_join_event': Mock(),
            'crash_report': self.crash_report,
            'task_factory': self.task_factory,
        }

        self.p1 = TestProcess1(self.bootstrap, on_process=p1_on_process, on_configure=p1_on_configure, on_stop=p1_on_stop, on_start=p1_on_start)
        self.p1.start()
        self.p2 = TestProcess2(self.bootstrap)
        self.p2.start()
        self.p3 = None

        sleep(0.25)
        self.internal_bus.app_configured(self.task_factory)

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

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertIsNotNone(resp)
        self.assertEqual(resp.data, 'command with params: hello world')
        self.assertFalse(resp.error)

    def test_send_command_with_invalid_command_parameters(self):
        self._init_context()

        resp = self.p2.send_command(command='command_with_params', params={'p1':'hello'}, to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertIsNotNone(resp)
        self.assertTrue(resp.error)
        self.assertEqual(resp.message, 'Some command parameters are missing')

    def test_send_command_to_unknown_module(self):
        self._init_context()

        resp = self.p1.send_command(command='command_with_params', params={'param1':'hello'}, to='dummy')
        logging.debug('Response: %s' % resp)
        
        self.assertTrue(resp.error)
        self.assertEqual(resp.message, 'Invalid application "dummy" (not loaded or unknown)')

    def test_send_command_invalid_command(self):
        self._init_context()

        resp = self.p1.send_command(command='command_unknown', params={'p1':'hello', 'p2':'world'}, to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertIsNotNone(resp)
        self.assertEqual(resp.data, None)
        self.assertTrue(resp.error)
        self.assertEqual(resp.message, 'Command "command_unknown" doesn\'t exist in "testprocess2" module')

    def test_send_broadcast_command(self):
        self._init_context()

        resp = self.p2.send_command(command='command_broadcast', params={'param':'hello'}, to=None)
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        sleep(0.5)

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertIsNone(resp.data)
        self.assertEqual(self.p1._get_command_calls('command_broadcast'), 1)
        self.assertEqual(self.p2._get_command_calls('command_broadcast'), 0)

    def test_send_command_to_myself(self):
        self._init_context()

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertIsNotNone(resp.data)
        self.assertEqual(resp.data, 'command without params')

    def test_send_command_with_exception(self):
        self._init_context()

        resp = self.p1.send_command(command='command_exception', to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertTrue(resp.error)
        self.assertEqual(resp.message, 'Test exception')
        self.assertIsNone(resp.data)

    def test_send_command_to_myself_with_exception(self):
        self._init_context()

        resp = self.p2.send_command(command='command_exception', to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertTrue(resp.error)
        self.assertEqual(resp.message, 'Test exception')
        self.assertIsNone(resp.data)

    def test_send_command_to_myself_with_invalid_command_parameters(self):
        self._init_context()

        resp = self.p1.send_command(command='command_with_params', params={'p1':'hello'}, to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertIsNotNone(resp)
        self.assertTrue(resp.error)
        self.assertEqual(resp.message, 'Some command parameters are missing')

    def test_send_command_to_myself_invalid_command(self):
        self._init_context()

        resp = self.p1.send_command(command='command_unknown', params={'p1':'hello', 'p2':'world'}, to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertIsNotNone(resp)
        self.assertEqual(resp.data, None)
        self.assertTrue(resp.error)
        self.assertEqual(resp.message, 'Command "command_unknown" doesn\'t exist in "testprocess1" module')

    @patch('inspect.signature')
    def test_send_command_to_myself_exception(self, signature_mock):
        signature_mock.side_effect = Exception('Test exception')
        self._init_context()

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertIsNone(resp.data)
        self.assertTrue(resp.error)
        self.assertEqual(resp.message, 'Internal error')

    def test_send_command_with_commanderror(self):
        self._init_context()

        resp = self.p1.send_command(command='command_error', to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertTrue(resp.error)
        self.assertEqual(resp.message, 'Command error')
        self.assertIsNone(resp.data)

    def test_send_command_with_commandinfo(self):
        self._init_context()

        resp = self.p1.send_command(command='command_info', to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertFalse(resp.error)
        self.assertEqual(resp.message, 'Command info')
        self.assertIsNone(resp.data)

    def test_on_process_called(self):
        class Context():
            call_count = 0

        def on_process():
            Context.call_count += 1

        self._init_context(p1_on_process=on_process)

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertEqual(Context.call_count, 1)

    def test_on_process_exception(self):
        def on_process():
            raise Exception('Test exception')

        self._init_context(p1_on_process=on_process)

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(self.crash_report.report_exception.called)
        self.assertEqual(self.crash_report.report_exception.call_count, 1)

    def test_on_configure_called(self):
        class Context():
            call_count = 0

        def configure():
            Context.call_count += 1

        self._init_context(p1_on_configure=configure)

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertEqual(Context.call_count, 1)

    def test_on_configure_exception(self):
        def configure():
            raise Exception('Test exception')

        self._init_context(p1_on_configure=configure)

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(self.crash_report.report_exception.called)
        self.assertEqual(self.crash_report.report_exception.call_count, 1)

    def test_get_module_name(self):
        self._init_context()

        module_name = self.p1._get_module_name()
        logging.debug('module_name=%s' % module_name)

        self.assertEqual(module_name, 'testprocess1')

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

    def test_command_sender_specified(self):
        self._init_context()

        resp = self.p1.send_command(command='command_sender', to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertEqual(resp.data, 'command_sender=testprocess1')

    def test_manual_response_specified(self):
        self._init_context()

        response = MessageResponse(data='async response')
        resp = self.p1.send_command(command='manual_response', to='testprocess2', params={'response': response}, timeout=1.0)
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertFalse(resp.error)
        self.assertEqual(resp.data, 'async response')

    def test_manual_response_specified_and_invalid_response(self):
        self._init_context()

        response = 'async response'
        resp = self.p1.send_command(command='manual_response', to='testprocess2', params={'response': response}, timeout=1.0)
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(resp.error)
        self.assertEqual(resp.message, 'Parameter "response" must be a MessageResponse instance')

    def test_manual_response_specified_with_exception_during_manual_response(self):
        self._init_context()

        response = MessageResponse(data='async response')
        resp = self.p1.send_command(command='manual_response', to='testprocess2', params={'response': response, 'exception':True}, timeout=1.0)
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(resp.error)
        self.assertEqual(resp.message, 'Test exception in manual_response')

    def test_manual_response_specified_timeout(self):
        self._init_context()

        resp = self.p1.send_command(command='manual_response', to='testprocess2', params={'ack': False}, timeout=1.0)
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        self.assertTrue(resp.error)
        self.assertTrue(resp.message.startswith('No response from testprocess2'))

    def test_send_command_default_params(self):
        self._init_context()

        resp = self.p1.send_command(command='command_default_params', params={'param1': 123}, to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        self.assertEqual(resp.data['param1'], 123)
        self.assertEqual(resp.data['param2'], 'default')

        resp = self.p1.send_command(command='command_default_params', params={'param1': 123, 'param2': 789}, to='testprocess2')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        self.assertEqual(resp.data['param1'], 123)
        self.assertEqual(resp.data['param2'], 789)

    def test_send_command_from_request(self):
        self._init_context()
        req = MessageRequest(command='command_with_params', params={'p1':'hello', 'p2':'world'}, to='testprocess1')

        resp = self.p2.send_command_from_request(req)
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertIsNotNone(resp)
        self.assertEqual(resp.data, 'command with params: hello world')
        self.assertFalse(resp.error)

    def test_send_command_from_request_same_module(self):
        self._init_context()
        self.p1.push = Mock()
        req = MessageRequest(command='command_with_params', params={'p1':'hello', 'p2':'world'}, to='testprocess1')

        resp = self.p1.send_command_from_request(req)
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertIsNotNone(resp)
        self.assertEqual(resp.data, 'command with params: hello world')
        self.assertFalse(resp.error)
        self.assertFalse(self.p1.push.called)

    def test_send_command_from_request_invalid_param(self):
        self._init_context()

        with self.assertRaises(Exception) as cm:
            self.p2.send_command_from_request({})
        self.assertEqual(str(cm.exception), 'Parameter "request" must be MessageRequest instance')

    def test_send_event(self):
        self._init_context()
        event = 'event.dummy.test'

        resp = self.p2.send_event(event, {'p1': 'event'})
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        sleep(0.5)

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertIsNone(resp.data)
        self.assertEqual(self.p1._get_command_calls('on_event'), 1)
        self.assertEqual(self.p2._get_command_calls('on_event'), 0)

    def test_send_event_with_exception(self):
        self._init_context()
        self.p3 = TestProcess3(self.bootstrap)
        self.p3.start()
        sleep(0.5)
        event = 'event.dummy.test'

        resp = self.p2.send_event(event, {'p1': 'event'}, to='testprocess3')
        sleep(0.5)
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertFalse(resp.error) # can't handle event errors on multiple apps
        self.assertIsNone(resp.data)

    def test_send_event_from_request(self):
        self._init_context()
        self.p2 = TestProcess3(self.bootstrap)
        self.p2.start()
        sleep(0.5)
        
        req = MessageRequest(event='event.dummy.test', params={'param': 'value'})
        resp =self.p2.send_event_from_request(req)
        sleep(0.5)
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))

        self.assertTrue(isinstance(resp, MessageResponse))
        self.assertFalse(resp.error)
        self.assertIsNone(resp.data)

    def test_send_event_from_request_invalid_param(self):
        self._init_context()

        with self.assertRaises(Exception) as cm:
            self.p2.send_event_from_request({})
        self.assertEqual(str(cm.exception), 'Parameter "request" must be MessageRequest instance')
        
    def test_on_stop_called(self):
        class Context():
            call_count = 0

        def on_stop():
            Context.call_count += 1

        self._init_context(p1_on_stop=on_stop)

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        self.p1.stop()
        sleep(1.0)

        self.assertEqual(Context.call_count, 1)

    def test_on_stop_called_exception(self):
        def on_stop():
            raise Exception('Test exception')

        self._init_context(p1_on_stop=on_stop)

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        self.p1.stop()
        sleep(1.0)

        self.assertTrue(self.crash_report.report_exception.called)
        self.assertEqual(self.crash_report.report_exception.call_count, 1)

    def test_on_start_called(self):
        class Context():
            call_count = 0

        def on_start():
            Context.call_count += 1

        self._init_context(p1_on_start=on_start)

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        sleep(1.0)
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        self.p1.stop()
        sleep(1.0)

        self.assertEqual(Context.call_count, 1)

    def test_on_start_called_exception(self):
        def on_start():
            raise Exception('Test exception')

        self._init_context(p1_on_start=on_start)

        resp = self.p1.send_command(command='command_without_params', to='testprocess1')
        logging.debug('Response [%s]: %s' % (resp.__class__.__name__, resp))
        self.p1._wait_is_started()
        self.p1.stop()
        sleep(1.0)

        self.assertFalse(self.crash_report.report_exception.called)



if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_bus.py; coverage report -m -i
    unittest.main()

