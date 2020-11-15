#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import threading
import uptime
import time
import math
import inspect
from collections import deque
from threading import Event
from cleep.libs.internals.task import Task
from queue import Queue
from cleep.common import MessageResponse, MessageRequest
from cleep.exception import (NoMessageAvailable, InvalidParameter, MissingParameter,
     BusError, NoResponse, CommandError, CommandInfo, InvalidModule, NotReady)

__all__ = [u'MessageBus', u'BusClient']

class MessageBus():

    STARTUP_TIMEOUT = 30.0
    DEQUE_MAX_LEN = 100
    SUBSCRIPTION_LIFETIME = 600 # in seconds

    """
    Message bus
    Used to send messages to subscribed clients
    A pushed message can have recipient to directly send message to specific client. In that case
    a response is awaited. If there is no response before end of timeout, an exception is throwed.
    A message without recipient is broadcasted to all subscribers. No response is awaited.
    Only broadcasted messages can be sent before all clients have subscribed (during init phase)
    """
    def __init__(self, crash_report, debug_enabled):
        """
        Constructor

        Args:
            crash_report (CrashReport): CrashReport instance
            debug_enabled (bool): True if debug is enabled on bus
        """
        # init
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)

        # members
        self.crash_report = crash_report
        self.__stopped = False
        # module message queues
        self._queues = {}
        # module queue activities
        self.__activities = {}
        # purge task
        self.__purge = None
        # configured flag
        self.__app_configured = False

    def stop(self):
        """
        Stop bus
        """
        # set flag
        self.__stopped = True

        # clear all queues
        for q in self._queues:
            continu = True
            while continu:
                try:
                    msg = self._queues[q].pop()
                    self.logger.debug('Purging %s queue message: %s' % (q, msg))
                    if msg[u'event']:
                        msg[u'event'].set()
                except:
                    continu = False

        # stop purge thread
        if self.__purge:
            self.__purge.stop()

    def app_configured(self):
        """
        Say to message bus application is configured and ready to run.
        /!\ This way of proceed is dangerous if clients always broadcast messages, the bus may always stay
        blocked in "app not configured" state. But in small system like cleep, it should be fine.
        """
        # then set app is configured
        self.__app_configured = True

        # and finally launch purge subscriptions task
        self.__purge = Task(60.0, self.purge_subscriptions, self.logger)
        self.__purge.start()

        # now push function will handle new messages

    def push(self, request, timeout=3.0):
        """
        Push message to specified module and wait for response until timeout.
        By default it is blocking but with timeout=0.0 the function returns instantly
        without result, but command is sent.

        Args:
            request (MessageRequest): message to push.
            timeout (float): time to wait for response. If not specified, function returns None.

        Returns:
            dict: message response
            None: if no response awaited (request is an event or a broadcast command or if timeout is None)

        Raises:
            InvalidParameter: if request is not a MessageRequest instance.
            NoResponse: if no response is received from module.
            InvalidModule: if specified recipient is unknown.
        """
        # do not push request if bus is stopped
        if self.__stopped:
            raise Exception('Bus stopped')
        if not self.__app_configured:
            raise NotReady('Pushing messages to internal bus is possible only when application is running. '
                'If this message appears during Cleep startup it means you try to send a message from module '
                'constructor or _configure method, if that is the case prefer using _on_start method.')
        if not isinstance(request, MessageRequest):
            raise InvalidParameter(u'Parameter "request" must be MessageRequest instance')

        # get request as dict
        request_dict = request.to_dict(not self.__app_configured)
        self.logger.trace(u'Received message %s to push to "%s" module with timeout %s' % (
            request_dict,
            request.to,
            timeout
        ))

        # push message according to context
        if request.to in self._queues:
            # recipient exists and has queue
            return self.__push_to_recipient(request, request_dict, timeout)
        elif request.to==u'rpc':
            # recipient is rpc
            return self.__push_to_rpc(request, request_dict, timeout)
        elif request.to is None:
            # no recipient specified, broadcast message
            return self.__push_to_broadcast(request, request_dict, timeout)
        elif not self.__app_configured and request.to is not None:
            # last chance case, recipient may not exists but app is not configured yet
            return self.__push_to_unknown_module(request, request_dict, timeout)
        else:
            # App is configured but recipient is not subscribed, raise exception
            raise InvalidModule(request.to)

    def __push_to_recipient(self, request, request_dict, timeout):
        """
        Push message to specified recipient
        """
        # Send message to specified subscribed recipient
        event = None
        if timeout:
            event = Event()

        # prepare message
        msg = {
            u'message': request_dict,
            u'event': event,
            u'response': None
        }
        self.logger.debug(u'Push to recipient "%s" message %s' % (request.to, str(msg)))

        # log module activity to avoid purge
        self.__activities[request.to] = int(uptime.uptime())
            
        # append message to queue
        self._queues[request.to].appendleft(msg)

        if not event:
            # no timeout given, do not wait response and return None
            return None

        # wait for response
        self.logger.trace(u'Push wait for response (%s seconds)....' % str(timeout))
        if event.wait(timeout):
            # response received
            self.logger.trace(u' - resp received %s' % str(msg))
            return msg[u'response']
        else:
            # no response in time
            self.logger.trace(u' - timeout')
            raise NoResponse(request.to, timeout, request_dict)

    def __push_to_rpc(self, request, request_dict, timeout):
        """
        Send message to all subscribed frontends
        If application is not configured, messages are dropped
        """
        if not self.__app_configured:
            return None

        # broadcast message to every rpc subcribers (no response awaited)
        msg = {
            u'message': request_dict,
            u'event': None,
            u'response': None
        }
        self.logger.debug(u'Broadcast to RPC clients message %s' % str(msg))

        # append message to rpc queues
        for q in self._queues.keys():
            if q.startswith(u'rpc-'):
                self._queues[q].appendleft(msg)

        return None

    def __push_to_broadcast(self, request, request_dict, timeout):
        """
        No recipient to request, broadcast message to all subscribed modules
        Broadcast message does not reply with a response (return None)
        """
        msg = {
            u'message': request_dict,
            u'event': None,
            u'response':None
        }
        self.logger.debug(u'Broadcast message %s' % str(msg))

        # append message to queues
        for q in self._queues:
            # do not send command to message sender
            if q==request.sender:
                continue

            # enqueue message
            self._queues[q].appendleft(msg)

        return None

    def __push_to_unknown_module(self, request, request_dict, timeout):
        """
        Handle message sent before app is configured and recipient queue doesn't exist yet
        This part of code will create queue for specified recipient and increase request timeout
        This is only a hack, a best practice is to wait startup event to send request to recipient
        """
        self.logger.debug(u'Handle startup message')

        # prepare sync event
        event = None
        if timeout:
            # force timeout to wait for cleep is completely started
            timeout = self.STARTUP_TIMEOUT
            event = Event()

        # prepare message
        msg = {
            u'message': request_dict,
            u'event': event,
            u'response': None
        }
        self.logger.debug(u'Push to "%s" delayed message %s (timeout=%s)' % (request.to, str(msg), timeout))

        # append message to queue
        self._queues[request.to] = deque(maxlen=self.DEQUE_MAX_LEN)
        self._queues[request.to].appendleft(msg)

        # wait for response
        if not timeout:
            return None
        self.logger.trace(u'Wait for startup message response (%s seconds)...' % str(self.STARTUP_TIMEOUT))
        if event.wait(self.STARTUP_TIMEOUT):
            # response received
            self.logger.trace(u' - resp received %s' % str(msg))
            return msg[u'response']
        else:
            # no reponse in time
            self.logger.trace(u' - timeout')
            raise NoResponse(request.to, timeout, request_dict)

    def pull(self, module, timeout=0.5):
        """
        Pull message from specified module queue.

        Args:
            module (string): module name
            timeout (float): time to wait, default is blocking (0.5s)

        Returns:
            dict: received message::

                {
                    message (dict): MessageRequest as dict
                    event (Event): sync event or None if no response awaited (broadcast, event message)
                    response (MessageResponse): request response or None if no response
                }

        Raises:
            InvalidModule: if module is unknown.
            BusError: if fatal error occured during message pulling.
            NoMessageAvailable: if no message is available.
        """
        module_lc = module.lower()
        if module_lc in self._queues:

            # log module activity
            self.__activities[module_lc] = int(uptime.uptime())

            if not timeout:
                return self.__pull_without_timeout(module, module_lc, timeout)
            else:
                return self.__pull_with_timeout(module, module_lc, timeout)

        else:
            # subscriber not found
            self.logger.error(u'Module %s not found' % module_lc)
            raise InvalidModule(module_lc)

    def __pull_without_timeout(self, module, module_lc, timeout):
        """
        Pull message without timeout
        """
        try:
            msg = self._queues[module_lc].pop()
            self.logger.trace(u'"%s" pulled without timeout: %s' % (module_lc, msg))
            return msg

        except IndexError:
            # no message available
            raise NoMessageAvailable()

        except:
            self.logger.exception(u'Error when pulling message:')
            self.crash_report.report_exception({
                u'message': u'Error when pulling message',
                u'module': module
            })
            raise BusError(u'Error when pulling message')

    def __pull_with_timeout(self, module, module_lc, timeout):
        """
        Pull message with timeout
        Timeout specified, try to read each 0.1 seconds a message until specified timeout
        """
        loop = math.floor(timeout / 0.10)
        i = 0
        while i<loop:
            try:
                msg = self._queues[module_lc].pop()
                self.logger.trace(u'"%s" pulled with timeout %s' % (module_lc, msg))
                return msg

            except IndexError:
                # no message available
                pass

            except:
                # unhandled error
                self.logger.exception(u'Error when pulling message:')
                self.crash_report.report_exception({
                    u'message': u'Error when pulling message',
                    u'module': module
                })
                raise BusError(u'Error when pulling message')

            time.sleep(0.10)
            i += 1

        # end of loop and no message found
        raise NoMessageAvailable()

    def add_subscription(self, module):
        """
        Add new subscription.

        Args:
            module (string): module name
        """
        module_lc = module.lower()
        self.logger.trace(u'Add subscription for module "%s"' % module_lc)
        self._queues[module_lc] = deque(maxlen=self.DEQUE_MAX_LEN)
        self.__activities[module_lc] = int(uptime.uptime())

    def remove_subscription(self, module):
        """
        Remove existing subscription;

        Args:
            module (string): module name.

        Raises:
            InvalidParameter: if module is unknown.
        """
        module_lc = module.lower()
        self.logger.debug(u'Remove subscription for module "%s"' % module_lc)
        if module_lc in self._queues:
            del self._queues[module_lc]
            del self.__activities[module_lc]
        else:
            # uuid does not exists
            self.logger.error(u'Subscriber "%s" not found' % module_lc)
            raise InvalidModule(module_lc)

    def is_subscribed(self, module):
        """
        Check if module is subscribed.

        Args:
            module (string): module name.

        Returns:
            bool: True if module is subscribed.
        """
        return module.lower() in self._queues

    def purge_subscriptions(self):
        """
        Purge old subscriptions.
        """
        now = int(uptime.uptime())
        copy = self.__activities.copy()
        for module, last_pull in copy.items():
            if now>(last_pull + self.SUBSCRIPTION_LIFETIME):
                # remove inactive subscription
                self.logger.debug(u'Remove obsolete subscription "%s"' % module)
                self.remove_subscription(module)




class BusClient(threading.Thread):
    """
    BusClient class must be inherited to handle message from MessageBus.
    It reads module message, read command and execute module command.
    Finally it returns command response to message originator.
    """

    CORE_SYNC_TIMEOUT = 60.0

    def __init__(self, bootstrap):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
        """
        threading.Thread.__init__(
            self,
            daemon=True,
            name='module-%s' % self.__class__.__name__.lower()
        )

        # members
        self.__continue = True
        self.__bus = bootstrap['message_bus']
        self.__bootstrap_crash_report = bootstrap['crash_report']
        self.__name = self.__class__.__name__
        self.__module_name = self.__name.lower()
        self.__module_join_event = bootstrap['module_join_event']
        self.__module_join_event.clear()
        self.__core_join_event = bootstrap['core_join_event']
        self.__on_start_event = Event()
        self.__bootstrap = bootstrap

        # subscribe module to bus
        self.__bus.add_subscription(self.__module_name)

    def stop(self):
        self.__continue = False

    def __get_crash_report(self):
        """
        Get crash report

        Returns:
            instance (CrashReport): Crash report instance
        """
        return self.crash_report if self.crash_report else self.__bootstrap_crash_report

    def __check_params(self, function, message, sender):
        """
        Check if message contains all necessary function parameters.

        Args:
            function (function): function reference.
            message (dict): current message content (contains all command parameters).
            sender (string): message sender ("from" item from MessageRequest).

        Returns:
            tuple: parameters check response::
    
                (
                    bool: True if parameters are valid otherwise False,
                    dict: args to pass during command call or None
                )

        """
        args = {}
        params_with_default = {}

        # get function parameters
        func_signature = inspect.signature(function)
        params = func_signature.parameters

        # get params with default value
        for param in func_signature.parameters:
            params_with_default[param] = False if func_signature.parameters[param].default == func_signature.empty else True

        # fill parameters list
        for param in params:
            if param==u'self':
                # drop self param
                pass
            elif param==u'command_sender':
                # function needs request sender value
                args[u'command_sender'] = sender
            elif not isinstance(message, dict) or (param not in message and not params_with_default[param]):
                # missing parameter
                return False, None
            else:
                # update function arguments list
                if param in message:
                    args[param] = message[param]

        return True, args

    def push(self, request, timeout=3.0):
        """
        Push message to specified module and wait for response until timeout.
        By default it is blocking but with timeout=0.0 the function returns instantly
        without result, but command is sent.

        Args:
            request (MessageRequest): message to push.
            timeout (float): time to wait for response. If not specified, function returns None.

        Returns:
            dict: MessageResponse as dict or None if no response awaited (event or broadcast)

        Raises:
            InvalidParameter: if request is not a MessageRequest instance.
        """
        if not isinstance(request, MessageRequest):
            raise InvalidParameter(u'Request parameter must be MessageRequest instance')
        
        # fill sender
        request.sender = self.__module_name

        # drop message send to the same module
        if request.to is not None and request.to == self.__module_name:
            raise Exception(u'Unable to send message to same module')

        # push message
        if request.is_broadcast() or timeout is None or timeout==0.0:
            # broadcast message or no timeout, so no response
            self.__bus.push(request, timeout)

            # broadcast response
            resp = MessageResponse()
            resp.broadcast = True
            return resp.to_dict()

        else:
            # response awaited
            resp = self.__bus.push(request, timeout)
            return resp

    def send_event(self, event, params=None, device_id=None, to=None):
        """
        Helper function to push event message to bus.

        Args:
            event (string): event name.
            params (dict): event parameters.
            device_id (string): device id that send event. If not specified event cannot be monitored.
            to (string): event recipient. If not specified, event will be broadcasted.
        """
        request = MessageRequest()
        request.to = to
        request.event = event
        request.device_id = device_id
        request.params = params

        self.push(request, None)

    def send_event_from_message(self, message):
        """
        Directly push event message to bus.
        
        Use this function instead of send_command to fill more data in message like peer infos.

        Args:
            message (MessageRequest): message request

        Returns:
            None: event always returns None.
        """
        if not isinstance(message, MessageRequest):
            raise Exception('Parameter "message" must be MessageRequest instance')

        self.push(message, None)

    def __execute_command(self, command, params=None):
        """
        Execute command from myself

        Args:
            command (string): command name
            params (dict): command parameters

        Returns:
            dict: MessageResponse as dict or None if no response waited
        """
        resp = MessageResponse()
        try:
            # get command reference
            module_function = getattr(self, command)
            if module_function is not None:
                (ok, args) = self.__check_params(module_function, params, self.__module_name)
                if ok:
                    try:
                        resp.data = module_function(**args)
                    except Exception as e:
                        self.logger.exception(u'Exception during send_command in the same module:')
                        resp.error = True
                        resp.message = str(e)
                else:
                    # invalid command
                    self.logger.error(u'Some command "%s" parameters are missing: %s' % (command, params))
                    resp.error = True
                    resp.message = u'Some command parameters are missing'

        except AttributeError:
            self.logger.exception(u'Command "%s" doesn\'t exist in "%s" module' % (command, self.__module_name))
            resp.error = True
            resp.message = u'Command "%s" doesn\'t exist in "%s" module' % (command, self.__module_name)

        except:
            self.logger.exception(u'Internal error:')
            resp.error = True
            resp.message = u'Internal error'

        return resp.to_dict()

    def send_command(self, command, to, params=None, timeout=3.0):
        """
        Helper function to push command message to bus.

        Args:
            command (string): command name.
            to (string): command recipient. If None the command is broadcasted but you'll get no reponse in return.
            params (dict): command parameters.
            timeout (float): change default timeout if you wish. Default is 3 seconds.

        Returns:
            dict: MessageResponse as dict or None if no response waited
        """
        if to == self.__module_name:
            # message recipient is the module itself, bypass bus and execute directly the command
            return self.__execute_command(command, params)
        else:
            # send command to another module
            request = MessageRequest()
            request.to = to
            request.command = command
            request.params = params

            return self.push(request, timeout)

    def send_command_from_message(self, message, timeout=3.0):
        """
        Directly push message to bus.

        Use this function instead of send_command to fill more data in message like peer infos.

        Args:
            message (MessageRequest): message request
            timeout (float): change default timeout if you wish. Default is 3 seconds.

        Returns:
            dict: MessageResponse as dict or None if no response waited
        """
        if not isinstance(message, MessageRequest):
            raise Exception('Parameter "message" must be MessageRequest instance')

        if to == self.__module_name:
            # message recipient is the module itself, bypass bus and execute directly the command
            return self.__execute_command(command, params)
        else:
            return self.push(message, timeout)

    """
    def send_command_to_peer(self, command, to, peer_uuid, params=None, timeout=5.0):
        Helper function to push command message to specified peer through external bus.

        Args:
            command (string): command name.
            to (string): command recipient. If None the command is broadcasted but you'll get no reponse in return.
            peer_infos (dict): infos about peer that sends the command
            params (dict): command parameters
            timeout (float): timeout

        Returns:
            dict: MessageResponse as dict or None if no response
        if not self.bootstrap['external_bus']:
            self.logger.warning('Unable to send message to peer because there is no external bus application')
        
        if self.__module_name == self.bootstrap['external_bus']:
            # directly call my function
            return self._send_command_to_peer(command, to, peer_uuid, params, timeout)
        else:
            # send command to internal message bus
            return self.send_command(
                'send_command_to_peer',
                self.__bootstrap['external_bus'],
                {
                    'command': command,
                    'to': to,
                    'params': params,
                    'peer_uuid': peer_uuid,
                    'timeout': timeout,
                },
                timeout
            )

    def _send_command_to_peer(self, command, to, peer_uuid, params=None, timeout=5.0):
        Send command to peer implementation

        Args:
            command (string): command name.
            to (string): command recipient. If None the command is broadcasted but you'll get no reponse in return.
            peer_infos (dict): infos about peer that sends the command
            params (dict): command parameters.

        Returns:
            dict: MessageResponse as dict or None if no response

        Warning:
            This function must be implemented ONLY if module implements external bus functionnalities
        pass
    """

    def _on_process(self):
        """
        Overwrite this function to execute code just before each message polling.

        Warning:
            This function must be used with care! It mustn't be blocking or take too much execution
            time otherwise no message will be pulled from queue and your app will become unresponsive.
        """
        pass

    def _configure(self):
        """
        Module configuration. This method is called once at beginning of thread before
        module is really started.

        Warning:
            This function shouldn't be blocking to not increase Cleep startup time.
            If you need to process some long process, prefer using on_start method which is
            intented for that.
        """
        pass

    def _on_start(self):
        """
        Module starts. This method is called once after all modules are started.

        Notes:
            This method is run asynchronously and is dedicated to the execution of more of less long process
        """
        pass

    def _on_stop(self):
        """
        Module stops. This method is called once at end of main process.

        Notes:
            It should be used to stop thread and tasks and to disconnect from
            external services.
        """
        pass

    def _event_received(self, event): # pragma: no cover
        """
        Module received an event message

        Params:
            event (dict): MessageRequest as dict with event values::

                {
                    event (string): event name
                    params (dict): event parameters
                    device_id (string): device that emits event or None
                    sender (string): event sender
                    startup (bool): startup event flag
                }

        """
        pass

    def __started_callback(self):
        """
        Called when module is started. It releases internal event lock.
        """
        self.__on_start_event.set()

    def _wait_is_started(self):
        """
        Wait for module is started.
        Use it if you need to 
        
        Warning:
            As mentionned this function is blocking
        """
        self.__on_start_event.wait()

    def run(self):
        """
        Bus reading process.

        Process cycle life:
            - configure module
            - wait for all modules configured
            - run async start function
            - infinite loop on message bus (custom process can run on each loop)
        """
        self.logger.trace(u'BusClient %s started' % self.__module_name)

        # configuration
        try:
            self._configure()
        except Exception:
            self.__continue = False
            self.logger.exception('Exception during module "%s" configuration:' % self.__module_name)
            self.__get_crash_report().report_exception({
                u'message': 'Exception during module "%s" configuration' % self.__module_name,
                u'module': self.__module_name
            })
        except KeyboardInterrupt:
            self.stop()
        finally:
            self.__module_join_event.set()

        # module sync with others
        self.__core_join_event.wait(self.CORE_SYNC_TIMEOUT)

        # run on_start function asynchronously to avoid dead locks if
        # bus message is mutually used between 2 modules
        start_task = Task(None, self._on_start, self.logger, end_callback = self.__started_callback)
        start_task.start()

        # now run infinite loop on message bus
        while self.__continue:
            try:
                # custom process (do not crash bus on exception)
                try:
                    self._on_process()
                except Exception as e:
                    self.logger.exception(u'Critical error occured in on_process: %s' % str(e))
                    self.__get_crash_report().report_exception({
                        u'message': u'Critical error occured in on_process: %s' % str(e),
                        u'module': self.__module_name
                    })

                msg = {}
                try:
                    # get message
                    msg = self.__bus.pull(self.__module_name)

                except NoMessageAvailable:
                    # no message available
                    # release CPU
                    time.sleep(.25)
                    continue

                # create response
                resp = MessageResponse()
       
                # process message
                if 'message' in msg:
                    if 'command' in msg[u'message']:
                        # command received, process it
                        if 'command' in msg[u'message'] and msg[u'message'][u'command']!=None and len(msg[u'message'][u'command'])>0:
                            try:
                                # get command reference
                                command = getattr(self, msg[u'message'][u'command'])
                                self.logger.debug(u'Module "%s" received command "%s" from "%s" with params: %s' % (self.__module_name, msg[u'message'][u'command'], msg[u'message'][u'sender'], msg[u'message'][u'params']))

                                # check if command was found
                                if command is not None:
                                    # check if message contains all command parameters
                                    (ok, args) = self.__check_params(command, msg[u'message'][u'params'], msg[u'message'][u'sender'])
                                    # self.logger.debug(u'Command ok=%s args=%s' % (ok, args))
                                    if ok:
                                        # execute command
                                        try:
                                            resp.data = command(**args)

                                        except CommandError as e:
                                            self.logger.error(u'Command error: %s' % str(e))
                                            resp.error = True
                                            resp.message = str(e)

                                        except CommandInfo as e:
                                            # informative message
                                            resp.error = False
                                            resp.message = str(e)

                                        except Exception as e:
                                            # command failed
                                            self.logger.exception(u'Exception running command "%s" on module "%s"' % (msg[u'message'][u'command'], self.__module_name))
                                            resp.error = True
                                            resp.message = u'%s' % str(e)
                                    else:
                                        self.logger.error(u'Some "%s" command parameters are missing: %s' % (msg[u'message'][u'command'], msg[u'message'][u'params']))
                                        resp.error = True
                                        resp.message = u'Some command parameters are missing'

                            except AttributeError:
                                # specified command doesn't exists in this module
                                if not msg[u'message'][u'broadcast']:
                                    # log message only for non broadcasted message
                                    self.logger.exception(u'Command "%s" doesn\'t exist in "%s" module' % (msg[u'message'][u'command'], self.__module_name))
                                    resp.error = True
                                    resp.message = u'Command "%s" doesn\'t exist in "%s" module' % (msg[u'message'][u'command'], self.__module_name)

                            except Exception: # pragma: no cover
                                # robustness: this case should not happen because bus already check it
                                # specified command is malformed
                                self.logger.exception(u'Command is malformed:')
                                resp.error = True
                                resp.message = u'Received command was malformed'

                        else: # pragma: no cover
                            # robustness: this case should not happen because bus already check it
                            # no command specified
                            self.logger.error(u'No command specified in message %s' % msg[u'message'])
                            resp.error = True
                            resp.message = u'No command specified in message'
                                
                        # save response into message    
                        msg[u'response'] = resp.to_dict()

                        # unlock event if necessary
                        if msg[u'event']:
                            # event available, client is waiting for response, unblock it
                            msg[u'event'].set()
                    
                    elif 'event' in msg[u'message']:
                        self.logger.debug(u'%s received event "%s" from "%s" with params: %s' % (self.__module_name, msg[u'message'][u'event'], msg[u'message'][u'sender'], msg[u'message'][u'params']))
                        if 'sender' in msg[u'message'] and msg[u'message'][u'sender']==self.__module_name: # pragma: no cover
                            # robustness: this cas should not happen because bus already check it
                            # drop event sent to the same module
                            self.logger.trace('Do not process event from same module')
                            pass
                        else:
                            # event received, process it
                            try:
                                self._event_received(msg[u'message'])
                            except:
                                # do not crash module
                                self.logger.exception(u'Exception in event_received handled by "%s" module:' % self.__class__.__name__)

                else: # pragma: no cover
                    # robustness: this case should not happen because bus already check it
                    # received message is malformed
                    self.logger.warning(u'Received message is malformed, message dropped')

            except KeyboardInterrupt: # pragma: no cover
                # user stop cleep
                break

            except: # pragma: no cover
                # robustness: this case should not happen because all extraneous code is properly surrounded by try...except
                self.logger.exception(u'Fatal exception occured running module "%s":' % self.__module_name)
                self.__get_crash_report().report_exception({
                    'message': u'Fatal exception occured running module',
                    'module': self.__module_name
                })
                self.stop()

        # custom stop
        try:
            self._on_stop()
        except:
            self.logger.exception(u'Fatal exception occured stopping module "%s":' % self.__module_name)
            self.__get_crash_report().report_exception({
                'message': 'Fatal exception occured stopping module',
                'module': self.__module_name,
            })

        # remove subscription
        self.__bus.remove_subscription(self.__module_name)
        self.logger.trace(u'BusClient %s stopped' % self.__module_name)

