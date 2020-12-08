#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import threading
import time
import math
import inspect
from collections import deque
from threading import Event
import uptime
from cleep.libs.internals.task import Task
from cleep.common import MessageResponse, MessageRequest
from cleep.exception import (NoMessageAvailable, InvalidParameter, BusError, NoResponse, CommandError, CommandInfo,
                             InvalidModule, NotReady)

__all__ = ['MessageBus', 'BusClient']

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
                    if msg['event']:
                        msg['event'].set()
                except:
                    continu = False

        # stop purge thread
        if self.__purge:
            self.__purge.stop()

    def app_configured(self):
        """
        Set internal bus flag to say application is ready and messages can be processed
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
            any: MessageResponse or None if no response awaited (request is an event or a broadcast command or if
                 timeout is None)

        Raises:
            InvalidParameter: if request is not a MessageRequest instance.
            NoResponse: if no response is received from module.
            InvalidModule: if specified recipient is unknown.
            NotReady: if trying to push message while Cleep is not ready
        """
        # do not push request if bus is stopped
        if self.__stopped:
            raise Exception('Bus stopped')
        if not self.__app_configured:
            raise NotReady('Pushing messages to internal bus is possible only when application is running. '
                           'If this message appears during Cleep startup it means you try to send a message from module '
                           'constructor or _configure method, if that is the case prefer using _on_start method.')
        if not isinstance(request, MessageRequest):
            raise InvalidParameter('Parameter "request" must be MessageRequest instance')

        # get request as dict
        request_dict = request.to_dict()
        self.logger.trace('Received message %s to push to "%s" module with timeout %s' % (
            request_dict,
            request.to,
            timeout
        ))

        # push message according to context
        if request.to in self._queues:
            # recipient exists and has queue
            return self.__push_to_recipient(request, request_dict, timeout)
        elif request.to == 'rpc':
            # recipient is rpc
            return self.__push_to_rpc(request, request_dict, timeout)
        elif request.to is None:
            # no recipient specified, broadcast message
            return self.__push_to_broadcast(request, request_dict, timeout)
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
            'message': request_dict,
            'event': event,
            'response': None,
            'auto_response': True,
        }

        # log module activity to avoid purge
        self.__activities[request.to] = int(uptime.uptime())

        # append message to queue
        self._queues[request.to].appendleft(msg)

        if not event:
            # no timeout given, do not wait response and return None
            return MessageResponse()

        # wait for response
        self.logger.trace('Push wait for response (%s seconds)....' % str(timeout))
        if event.wait(timeout):
            # response received
            self.logger.debug('Response received %s' % str(msg['response']))
            return msg['response']
        else:
            # no response in time
            self.logger.debug('Command has timed out')
            raise NoResponse(request.to, timeout, request_dict)

    def __push_to_rpc(self, request, request_dict, timeout):
        """
        Send message to all subscribed frontends
        If application is not configured, messages are dropped
        """
        # broadcast message to every rpc subcribers (no response awaited)
        msg = {
            'message': request_dict,
            'event': None,
            'response': None,
            'auto_response': True,
        }
        self.logger.debug('Broadcast to RPC clients message %s' % str(msg))

        # append message to rpc queues
        for q in self._queues.keys():
            if q.startswith('rpc-'):
                self._queues[q].appendleft(msg)

        return MessageResponse()

    def __push_to_broadcast(self, request, request_dict, timeout):
        """
        No recipient to request, broadcast message to all subscribed modules.
        Broadcast message does not reply with a response (return None)
        """
        msg = {
            'message': request_dict,
            'event': None,
            'response':None,
            'auto_response': True,
        }
        self.logger.debug('Broadcast message %s' % str(msg))

        # append message to queues
        for module_queue in self._queues:
            # do not send command to message sender
            if module_queue == request.sender:
                continue

            # enqueue message
            self._queues[module_queue].appendleft(msg)

        return MessageResponse()

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
                    response (MessageResponse): message response instance
                    auto_response (bool): True to handle command response in bus. If False user must send response by himself
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
            self.logger.error('Module %s not found' % module_lc)
            raise InvalidModule(module_lc)

    def __pull_without_timeout(self, module, module_lc, timeout):
        """
        Pull message without timeout
        """
        try:
            msg = self._queues[module_lc].pop()
            self.logger.trace('"%s" pulled without timeout: %s' % (module_lc, msg))
            return msg

        except IndexError:
            # no message available
            raise NoMessageAvailable()

        except:
            self.logger.exception('Error when pulling message:')
            self.crash_report.report_exception({
                'message': 'Error when pulling message',
                'module': module
            })
            raise BusError('Error when pulling message')

    def __pull_with_timeout(self, module, module_lc, timeout):
        """
        Pull message with timeout
        Timeout specified, try to read each 0.1 seconds a message until specified timeout
        """
        loop = math.floor(timeout / 0.10)
        i = 0
        while i < loop:
            try:
                msg = self._queues[module_lc].pop()
                self.logger.trace('"%s" pulled with timeout %s' % (module_lc, msg))
                return msg

            except IndexError:
                # no message available
                pass

            except:
                # unhandled error
                self.logger.exception('Error when pulling message:')
                self.crash_report.report_exception({
                    'message': 'Error when pulling message',
                    'module': module
                })
                raise BusError('Error when pulling message')

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
        self.logger.trace('Add subscription for module "%s"' % module_lc)
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
        self.logger.debug('Remove subscription for module "%s"' % module_lc)
        if module_lc in self._queues:
            del self._queues[module_lc]
            del self.__activities[module_lc]
        else:
            self.logger.error('Subscriber "%s" not found' % module_lc)
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
            if now > (last_pull + self.SUBSCRIPTION_LIFETIME):
                # remove inactive subscription
                self.logger.debug('Remove obsolete subscription "%s"' % module)
                self.remove_subscription(module)




class BusClient(threading.Thread):
    """
    BusClient class must be inherited to handle message from MessageBus.
    It reads module message, read command and execute module command.
    Finally it returns command response to message originator.
    """

    CORE_SYNC_TIMEOUT = 60.0

    # specific parameter name to get command sender specified in command parameters
    PARAM_COMMAND_SENDER = 'command_sender'
    # specific parameter name to get async response function specified in command parameters.
    # Warning:
    #   If parameter is specified, command won't be automatically acknowledged by internal bus. If you don't call
    #   manual response function in your code, command will fall in timeout and never return a response.
    PARAM_MANUAL_RESPONSE = 'manual_response'

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
        self.__bus = bootstrap['internal_bus']
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
        crash_report = getattr(self, 'crash_report', None)
        return crash_report if crash_report else self.__bootstrap_crash_report

    def __check_command_parameters(self, function, message, sender, bus_message=None):
        """
        Check if message contains all necessary function parameters.

        Args:
            function (function): function reference
            message (dict): current message content (contains all command parameters)
            sender (string): message sender ("from" item from MessageRequest)
            bus_message (dict): bus message or None if no message

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
            if param == 'self': # pragma: no cover
                # drop self param
                continue
            if param == BusClient.PARAM_COMMAND_SENDER:
                # function needs request sender value
                args[BusClient.PARAM_COMMAND_SENDER] = sender
            elif param == BusClient.PARAM_MANUAL_RESPONSE:
                # function will take care of the command response
                def manual_response(response, bus_message=bus_message):
                    # store response
                    bus_message['response'] = response
                    # and set event
                    bus_message['event'].set()
                args[BusClient.PARAM_MANUAL_RESPONSE] = manual_response if bus_message else None
                bus_message['auto_response'] = args[BusClient.PARAM_MANUAL_RESPONSE] is None
            elif not isinstance(message, dict) or (param not in message and not params_with_default[param]):
                # missing parameter
                return False, None
            else:
                # update function arguments list
                if param in message:
                    args[param] = message[param]

        return True, args

    def _get_module_name(self):
        """
        Return module name
        """
        return self.__module_name

    def push(self, request, timeout=3.0):
        """
        Push message to specified module and wait for response until timeout.
        By default it is blocking but with timeout=0.0 the function returns instantly
        without result, but command is sent.

        Args:
            request (MessageRequest): message to push.
            timeout (float): time to wait for response. If not specified, function returns None.

        Returns:
            MessageResponse: message response instance

        Raises:
            InvalidParameter: if request is not a MessageRequest instance.
        """
        if not isinstance(request, MessageRequest):
            raise InvalidParameter('Request parameter must be MessageRequest instance')

        # fill sender
        request.sender = self.__module_name

        # drop message send to the same module
        if request.to is not None and request.to == self.__module_name:
            raise Exception('Unable to send message to same module')

        # push message
        response = MessageResponse()
        try:
            if request.is_broadcast() or not timeout:
                # broadcast message or no timeout, so no response
                self.__bus.push(request, timeout)
                response.broadcast = True
            else:
                # response awaited
                response.fill_from_response(self.__bus.push(request, timeout))

        except Exception as e:
            self.logger.exception('Error occured while pushing message to bus')
            response.error = True
            response.message = str(e)

        return response

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

        return self.push(request, None)

    def send_event_from_request(self, request):
        """
        Directly push event message request to bus.

        Use this function instead of send_command to fill more data in message like peer infos.

        Args:
            request (MessageRequest): message request

        Returns:
            None: event always returns None.
        """
        if not isinstance(request, MessageRequest):
            raise Exception('Parameter "request" must be MessageRequest instance')

        return self.push(request, None)

    def __execute_command(self, command, params=None):
        """
        Execute command directly from module itself

        Args:
            command (string): command name
            params (dict): command parameters

        Returns:
            MessageResponse: message response instance
        """
        resp = MessageResponse()
        try:
            # get command reference
            module_function = getattr(self, command)
            if module_function is not None:
                (ok, args) = self.__check_command_parameters(module_function, params, self.__module_name)
                if ok:
                    try:
                        resp.data = module_function(**args)
                    except Exception as e:
                        self.logger.exception('Exception during send_command in the same module:')
                        resp.error = True
                        resp.message = str(e)
                else:
                    # invalid command
                    self.logger.error('Some command "%s" parameters are missing: %s' % (command, params))
                    resp.error = True
                    resp.message = 'Some command parameters are missing'

        except AttributeError:
            self.logger.exception('Command "%s" doesn\'t exist in "%s" module' % (command, self.__module_name))
            resp.error = True
            resp.message = 'Command "%s" doesn\'t exist in "%s" module' % (command, self.__module_name)

        except Exception:
            self.logger.exception('Internal error:')
            resp.error = True
            resp.message = 'Internal error'

        return resp

    def send_command(self, command, to, params=None, timeout=3.0):
        """
        Helper function to push command message to bus.

        Args:
            command (string): command name.
            to (string): command recipient. If None the command is broadcasted but you'll get no reponse in return.
            params (dict): command parameters.
            timeout (float): change default timeout if you wish. Default is 3 seconds.

        Returns:
            MessageResponse: message response instance
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

    def send_command_from_request(self, request, timeout=3.0):
        """
        Directly push message to bus.

        Use this function instead of send_command to fill more data in message like peer infos.

        Args:
            request (MessageRequest): message request
            timeout (float): change default timeout if you wish. Default is 3 seconds.

        Returns:
            MessageResponse: message response instance
        """
        if not isinstance(request, MessageRequest):
            raise Exception('Parameter "request" must be MessageRequest instance')

        if request.to == self.__module_name:
            # message recipient is the module itself, bypass bus and execute directly the command
            return self.__execute_command(request.command, request.params)
        else:
            return self.push(request, timeout)

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

    def _on_event(self, event): # pragma: no cover
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
        Use it if you need to wait for module to be started.

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
        self.logger.trace('BusClient %s started' % self.__module_name)

        # configuration
        try:
            self._configure()
        except Exception:
            self.__continue = False
            self.logger.exception('Exception during module "%s" configuration:' % self.__module_name)
            self.__get_crash_report().report_exception({
                'message': 'Exception during module "%s" configuration' % self.__module_name,
                'module': self.__module_name
            })
        except KeyboardInterrupt: # pragma: no cover
            self.stop()
        finally:
            self.__module_join_event.set()

        # module sync with others
        self.__core_join_event.wait(self.CORE_SYNC_TIMEOUT)

        # run on_start function asynchronously to avoid dead locks if
        # bus message is mutually used between 2 modules
        start_task = Task(None, self._on_start, self.logger, end_callback=self.__started_callback)
        start_task.start()

        # now run infinite loop on message bus
        while self.__continue:
            try:
                # custom process (do not crash bus on exception)
                try:
                    self._on_process()
                except Exception as e:
                    self.logger.exception('Critical error occured in on_process: %s' % str(e))
                    self.__get_crash_report().report_exception({
                        'message': 'Critical error occured in on_process: %s' % str(e),
                        'module': self.__module_name
                    })

                msg = {}
                try:
                    # get message from queue
                    msg = self.__bus.pull(self.__module_name)

                except NoMessageAvailable:
                    # no message available
                    # release CPU
                    time.sleep(.25)
                    continue

                # create response
                resp = MessageResponse()

                # process message
                if msg and 'message' in msg:
                    if 'command' in msg['message']:
                        # command received, process it
                        if ('command' in msg['message'] and msg['message']['command'] != None and
                                len(msg['message']['command']) > 0):
                            try:
                                # get command reference
                                command = getattr(self, msg['message']['command'])
                                self.logger.debug(
                                    'Module "%s" received command "%s" from "%s" with params: %s' % (
                                        self.__module_name,
                                        msg['message']['command'],
                                        msg['message']['sender'],
                                        msg['message']['params']
                                    )
                                )

                                # check if command was found
                                if command is not None:
                                    # check if message contains all command parameters
                                    (ok, args) = self.__check_command_parameters(
                                        command,
                                        msg['message']['params'],
                                        msg['message']['sender'],
                                        msg,
                                    )

                                    if ok:
                                        # execute command
                                        try:
                                            resp.data = command(**args)

                                        except CommandError as e:
                                            self.logger.error('Command error: %s' % str(e))
                                            resp.error = True
                                            resp.message = str(e)

                                        except CommandInfo as e:
                                            # informative message
                                            resp.error = False
                                            resp.message = str(e)

                                        except Exception as e:
                                            # command failed
                                            self.logger.exception(
                                                'Exception running command "%s" on module "%s"' % (
                                                    msg['message']['command'],
                                                    self.__module_name
                                                )
                                            )
                                            resp.error = True
                                            resp.message = '%s' % str(e)
                                    else:
                                        self.logger.error(
                                            'Some "%s" command parameters are missing: %s' % (
                                                msg['message']['command'],
                                                msg['message']['params']
                                            )
                                        )
                                        resp.error = True
                                        resp.message = 'Some command parameters are missing'

                            except AttributeError:
                                # specified command doesn't exists in this module
                                if not msg['message']['broadcast']:
                                    # log message only for non broadcasted message
                                    self.logger.exception(
                                        'Command "%s" doesn\'t exist in "%s" module' % (
                                            msg['message']['command'],
                                            self.__module_name
                                        )
                                    )
                                    resp.error = True
                                    resp.message = 'Command "%s" doesn\'t exist in "%s" module' % (
                                        msg['message']['command'],
                                        self.__module_name
                                    )

                            except Exception: # pragma: no cover
                                # robustness: this case should not happen because bus already check it
                                # specified command is malformed
                                self.logger.exception('Command is malformed:')
                                resp.error = True
                                resp.message = 'Received command was malformed'

                        else: # pragma: no cover
                            # robustness: this case should not happen because bus already check it
                            # no command specified
                            self.logger.error('No command specified in message %s' % msg['message'])
                            resp.error = True
                            resp.message = 'No command specified in message'

                        # unlock event if necessary
                        if (msg['event'] and msg['auto_response']) or (msg['event'] and not msg['auto_response'] and resp.error):
                            # save response into message
                            msg['response'] = resp

                            # event available, client is waiting for response, unblock it
                            msg['event'].set()

                    elif 'event' in msg['message']:
                        self.logger.debug(
                            '%s received event "%s" from "%s" with params: %s' % (
                                self.__module_name,
                                msg['message']['event'],
                                msg['message']['sender'],
                                msg['message']['params']
                            )
                        )
                        if 'sender' in msg['message'] and msg['message']['sender'] == self.__module_name: # pragma: no cover
                            # robustness: this cas should not happen because bus already check it
                            # drop event sent to the same module
                            self.logger.trace('Do not process event from same module')
                            pass
                        else:
                            # event received, process it
                            try:
                                self._on_event(msg['message'])
                            except:
                                # do not crash module
                                self.logger.exception(
                                    'Exception during on_event call, handled by "%s" module:' % self.__class__.__name__
                                )

                else: # pragma: no cover
                    # robustness: this case should not happen because bus already check it
                    # received message is malformed
                    self.logger.warning('Received message is malformed, message dropped')

            except KeyboardInterrupt: # pragma: no cover
                # user stop cleep
                break

            except: # pragma: no cover
                # robustness: this case should not happen because all extraneous code is properly surrounded by try...except
                self.logger.exception('Fatal exception occured running module "%s":' % self.__module_name)
                self.__get_crash_report().report_exception({
                    'message': 'Fatal exception occured running module',
                    'module': self.__module_name
                })
                self.stop()

        # custom stop
        try:
            self._on_stop()
        except:
            self.logger.exception('Fatal exception occured stopping module "%s":' % self.__module_name)
            self.__get_crash_report().report_exception({
                'message': 'Fatal exception occured stopping module',
                'module': self.__module_name,
            })

        # remove subscription
        self.__bus.remove_subscription(self.__module_name)
        self.logger.trace('BusClient %s stopped' % self.__module_name)

