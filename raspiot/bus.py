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
from .libs.internals.task import Task
from Queue import Queue
from utils import MessageResponse, MessageRequest, NoMessageAvailable, InvalidParameter, MissingParameter, BusError, NoResponse, CommandError, CommandInfo, InvalidModule

__all__ = [u'MessageBus', u'BusClient']

class MessageBus():

    STARTUP_TIMEOUT = 30.0
    DEQUE_MAX_LEN = 50

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
        #init
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)

        #members
        self.crash_report = crash_report
        self.__stopped = False
        #module message queues
        self.__queues = {}
        #module queue activities
        self.__activities = {}
        #subscription lifetime (in seconds)
        self.lifetime = 600
        #purge task
        self.__purge = None
        #configured flag
        self.__app_configured = False
        self.__deferred_messages = Queue()

    def stop(self):
        """
        Stop bus
        """
        #set flag
        self.__stopped = True

        #clear all queues
        for q in self.__queues:
            continu = True
            while continu:
                try:
                    msg = self.__queues[q].pop()
                    self.logger.debug('Purging %s queue message: %s' % (q, msg))
                    if msg[u'event']:
                        msg[u'event'].set()
                except IndexError:
                    continu = False

        #stop purge thread
        if self.__purge:
            self.__purge.stop()

    def app_configured(self):
        """
        Say message bus is configured
        /!\ This way of proceed is dangerous if clients always broadcast messages, the bus may always stay
        blocked in "app not configured" state. But in small system like raspiot, it should be fine.
        """
        #first of all unqueue deferred messages to preserve order
        self.logger.debug('Unqueue deferred message')
        while not self.__deferred_messages.empty():
            msg = self.__deferred_messages.get()
            #msg.startup = True
            self.logger.debug(u'Push deferred: %s' % unicode(msg))
            for q in self.__queues:
                self.__queues[q].append(msg)

        #then set app is configured
        self.__app_configured = True

        #and finally launch purge subscriptions task
        self.__purge = Task(60.0, self.purge_subscriptions, self.logger)
        self.__purge.start()

        #now push function will handle new messages

    def push(self, request, timeout=3.0):
        """
        Push message to specified module and wait for response until timeout.
        By default it is blocking but with timeout=0.0 the function returns instantly
        without result, but command is sent.

        Args:
            request (MessageRequest): message to push.
            timeout (float): time to wait for response. If not specified, function returns None.

        Returns:
            MessageResponse: message response instance.
            None: if request is event or broadcast.

        Raises:
            InvalidParameter: if request is not a MessageRequest instance.
            NoResponse: if no response is received from module.
            InvalidModule: if specified recipient is unknown.
        """
        #do not push request if bus is stopped
        if self.__stopped:
            return None

        #increase default timeout during startup (really useful for raspiot v1)
        if not self.__app_configured and timeout:
            timeout *= 3.0

        if isinstance(request, MessageRequest):
            #get request as dict
            request_dict = request.to_dict(not self.__app_configured)
            self.logger.debug(u'Push %s => %s' % (request_dict, request.to))

            #push message to specified queue
            if self.__queues.has_key(request.to):
                #prepare event
                event = None
                if timeout:
                    event = Event()

                #prepare message
                msg = {u'message':request_dict, u'event':event, u'response':None}
                self.logger.debug(u'MessageBus: push to "%s" message %s' % (request.to, unicode(msg)))

                #log module activity
                self.__activities[request.to] = int(uptime.uptime())

                #append message to queue
                self.__queues[request.to].appendleft(msg)

                #and wait for response or not (if no timeout)
                if event:
                    #wait for response
                    self.logger.debug(u'MessageBus: push wait for response (%s seconds)....' % unicode(timeout))
                    if event.wait(timeout):
                        #response received
                        self.logger.debug(u' - resp received %s' % unicode(msg))
                        return msg[u'response']
                    else:
                        #no response in time
                        self.logger.debug(u' - timeout')
                        raise NoResponse(request.to, timeout, request_dict)
                else:
                    #no timeout given, return nothing
                    return None

            elif request.to==u'rpc':
                #broadcast message to every rpc subcribers (no response awaited)
                if self.__app_configured:
                    #prepare message
                    msg = {u'message':request_dict, u'event':None, u'response':None}
                    self.logger.debug(u'Broadcast to RPC clients message %s' % unicode(msg))

                    #append message to rpc queues
                    for q in self.__queues.keys():
                        if q.startswith(u'rpc-'):
                            self.__queues[q].appendleft(msg)
                else:
                    #application not ready, no rpc client should be connected, drop message
                    pass

                return None

            elif request.to==None:
                #broadcast message to every modules, without waiting for a response
                #prepare message
                msg = {u'message':request_dict, u'event':None, u'response':None}
                self.logger.debug(u'Broadcast message %s' % unicode(msg))

                if self.__app_configured:
                    #append message to queues
                    for q in self.__queues:
                        #do not send command to message sender
                        if q==request.from_:
                            continue

                        #enqueue message
                        self.__queues[q].appendleft(msg)

                else:
                    #defer message if app not configured yet
                    self.logger.debug(u'defer message: %s' % unicode(msg))
                    self.__deferred_messages.put(msg)
    
                return None

            elif not self.__app_configured and request.to is not None:
                #handle startup event
                self.logger.debug(u'Handle startup event')

                #prepare event
                event = Event()

                #prepare message
                msg = {u'message':request_dict, u'event':event, u'response':None}
                self.logger.debug(u'MessageBus: push to "%s" delayed message %s' % (request.to, unicode(msg)))

                #append message to queue
                self.__queues[request.to] = deque(maxlen=self.DEQUE_MAX_LEN)
                self.__queues[request.to].appendleft(msg)

                #wait for response
                self.logger.debug(u'MessageBus: push wait for startup event response (%s seconds)....' % unicode(self.STARTUP_TIMEOUT))
                if event.wait(self.STARTUP_TIMEOUT):
                    #response received
                    self.logger.debug(u' - resp received %s' % unicode(msg))
                    return msg[u'response']
                else:
                    #no reponse in time
                    self.logger.debug(u' - timeout')
                    raise NoResponse(request.to, self.STARTUP_TIMEOUT, request_dict)

            else:
                #app is configured but recipient is unknown
                raise InvalidModule(request.to)

        else:
            raise InvalidParameter(u'Request parameter must be MessageRequest instance')

    def pull(self, module, timeout=0.5):
        """
        Pull message from specified module queue.

        Args:
            module (string): module name;
            timeout (float): time to wait, default is blocking (0.5s).

        Returns:
            MessageResponse: received message.

        Raises:
            InvalidModule: if module is unknown.
            BusError: if fatal error occured during message pulling.
            NoMessageAvailable: if no message is available.
        """
        _module = module.lower()
        if self.__queues.has_key(_module):

            #log module activity
            self.__activities[_module] = int(uptime.uptime())

            if not timeout:
                #no timeout specified, try to pop a message and return just after
                try:
                    msg = self.__queues[_module].pop()
                    self.logger.debug(u'MessageBus: %s pulled noto: %s' % (_module, msg))
                    return msg

                except IndexError:
                    #no message available
                    raise NoMessageAvailable()

                except:
                    self.logger.exception(u'MessageBus: error when pulling message:')
                    self.crash_report.report_exception()
                    raise BusError(u'Error when pulling message')

            else:
                #timeout specified, try to read each 0.1 seconds a message until specified timeout
                loop = math.floor(timeout / 0.10)
                i = 0
                while i<loop:
                    try:
                        msg = self.__queues[_module].pop()
                        self.logger.debug(u'MessageBus: %s pulled %s' % (_module, msg))
                        return msg

                    except IndexError:
                        #no message available
                        pass

                    except:
                        #unhandled error
                        self.logger.exception(u'MessageBus: error when pulling message:')
                        self.crash_report.report_exception()
                        raise BusError(u'Error when pulling message')

                    finally:
                        time.sleep(0.10)
                        i += 1

                #end of loop and no message found
                raise NoMessageAvailable()

        else:
            #subscriber not found
            self.logger.error(u'Module %s not found' % _module)
            raise InvalidModule(_module)

    def add_subscription(self, module):
        """
        Add new subscription.

        Args:
            module (string): module name.
        """
        _module = module.lower()
        self.logger.debug(u'Add subscription for module %s' % _module)
        self.__queues[_module] = deque(maxlen=self.DEQUE_MAX_LEN)
        self.__activities[_module] = int(uptime.uptime())

    def remove_subscription(self, module):
        """
        Remove existing subscription;

        Args:
            module (string): module name.

        Raises:
            InvalidParameter: if module is unknown.
        """
        _module = module.lower()
        self.logger.debug(u'Remove subscription for module %s' % _module)
        if self.__queues.has_key(_module):
            del self.__queues[_module]
            del self.__activities[_module]
        else:
            #uuid does not exists
            self.logger.error(u'Subscriber %s not found' % _module)
            raise InvalidModule(_module)

    def is_subscribed(self, module):
        """
        Check if module is subscribed.

        Args:
            module (string): module name.

        Returns:
            bool: True if module is subscribed.
        """
        return self.__queues.has_key(module.lower())

    def purge_subscriptions(self):
        """
        Purge old subscriptions.
        """
        now = int(uptime.uptime())
        copy = self.__activities.copy()
        for module, last_pull in copy.iteritems():
            if now>last_pull+self.lifetime:
                #remove inactive subscription
                self.logger.debug(u'Remove obsolete subscription "%s"' % module)
                self.remove_subscription(module)




class BusClient(threading.Thread):
    """
    BusClient class must be inherited to handle message from MessageBus.
    It reads module message, read command and execute module command.
    Finally it returns command response to message originator.
    """
    def __init__(self, bootstrap):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
        """
        threading.Thread.__init__(self)
        threading.Thread.daemon = True

        #members
        self.__continue = True
        self.bus = bootstrap[u'message_bus']
        self.__name = self.__class__.__name__
        self.__module = self.__name.lower()
        self.join_event = bootstrap[u'join_event']
        self.join_event.clear()

        #subscribe module to bus
        self.bus.add_subscription(self.__module)

    def __del__(self):
        self.stop()

    def stop(self):
        self.__continue = False

    def __check_params(self, function, message, sender):
        """
        Check if message contains all necessary function parameters.

        Args:
            function (function): function reference.
            message (dict): current message content (contains all command parameters).
            sender (string): message sender ("from" item from MessageRequest).

        Returns:
            tuple: (
                bool: True or False,
                dict: args to pass during command call or None
            )
        """
        args = {}
        params_with_default = {}
        #self.logger.debug('message params:%s' % (message))

        #get function parameters
        (params, _, _, defaults) = inspect.getargspec(function)
        #self.logger.debug('params:%s default:%s' % (params, defaults))

        #check message parameters according to function parameters
        if message is None or not isinstance(message, dict) and len(params)==0:
            #no parameter needed
            return True, args

        #check params with default value
        if defaults is None:
            defaults = ()
        for param in params:
            params_with_default[param] = False
        for pos in range(len(params)-len(defaults), len(params)):
            params_with_default[params[pos]] = True

        #fill parameters list
        for param in params:
            if param==u'self':
                #drop self param
                pass
            elif param==u'command_sender':
                #function needs request sender value
                args[u'command_sender'] = sender
            elif not message.has_key(param) and not params_with_default[param]:
                #missing parameter
                return False, None
            else:
                #update function arguments list
                if message.has_key(param):
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
            MessageResponse: message response instance.
            None: if request is event or broadcast.

        Raises:
            InvalidParameter: if request is not a MessageRequest instance.
        """
        if isinstance(request, MessageRequest):
            #fill sender
            request.from_ = self.__module

            #drop message send to the same module
            if request.to is not None and request.to==self.__module:
                raise Exception(u'Unable to send message to itself')

            #push message
            if request.is_broadcast() or timeout is None or timeout==0.0:
                #broadcast message or no timeout, so no response
                self.bus.push(request, timeout)

                #broadcast response
                resp = MessageResponse()
                resp.broadcast = True
                return resp

            else:
                #response awaited
                resp = self.bus.push(request, timeout)
                return resp

        else:
            raise InvalidParameter(u'Request parameter must be MessageRequest instance')

    def send_event(self, event, params=None, device_id=None, to=None):
        """
        Helper function to push event message to bus.

        Args:
            event (string): event name.
            params (dict): event parameters.
            device_id (string): device id that send event. If not specified event cannot be monitored.
            to (string): event recipient. If not specified, event will be broadcasted.

        Returns:
            None: event always returns None.
        """
        request = MessageRequest()
        request.to = to
        request.event = event
        request.device_id = device_id
        request.params = params

        return self.push(request, None)

    def send_external_event(self, event, params, peer_infos):
        """
        Helper function to push event message to cleep bus.

        Args:
            event (string): event name.
            params (dict): event parameters.
            peer_infos (dict): infos about peer that sends the event

        Returns:
            None: event always returns None.
        """
        request = MessageRequest()
        request.event = event
        request.params = params
        request.peer_infos = peer_infos

        return self.push(request, None)

    def send_command(self, command, to, params=None, timeout=3.0):
        """
        Helper function to push command message to bus.

        Args:
            command (string): command name.
            to (string): command recipient. If None the command is broadcasted but you'll get no reponse in return.
            params (dict): command parameters.
            timeout (float): change default timeout if you wish. Default is 3 seconds.

        Returns:
            MessageResponse: push response.
            None: if command is broadcast.
        """
        if to==self.__module:
            #message recipient is the module itself, bypass bus
            resp = MessageResponse()
            try:
                #get command reference
                module_function = getattr(self, command)
                if module_function is not None:
                    (ok, args) = self.__check_params(module_function, params, self.__module)
                    if ok:
                        try:
                            resp.data = module_function(**args)

                        except Exception as e:
                            self.logger.exception(u'Exception during send_command in the same module:')
                            resp.error = True
                            resp.message = unicode(e)

                    else:
                        #invalid command
                        self.logger.error(u'Some command "%s" parameters are missing: %s' % (command, params))
                        resp.error = True
                        resp.message = u'Some command parameters are missing'
            
            except AttributeError:
                self.logger.exception(u'Command "%s" doesn\'t exist in "%s" module' % (msg[u'message'][u'command'], self.__module))
                resp.error = True
                resp.message = u'Command "%s" doesn\'t exist in "%s" module' % (command, self.__module)

            except:
                self.logger.exception(u'Command is malformed:')
                resp.error = True
                resp.message = u'Received command was malformed'

            return resp.to_dict()
                        
        else:
            #prepare request
            request = MessageRequest()
            request.to = to
            request.command = command
            request.params = params

            return self.push(request, timeout)

    def _custom_process(self):
        """
        Overwrite this function to execute something during bus message polling

        Note:
            This function mustn't be blocking!
        """
        pass

    def _configure(self):
        """
        Module configuration. This method is called at beginning of thread.
        You can execute long process but your module will not be available quickly

        Note:
            This function mustn't be blocking!
        """
        pass

    def run(self):
        """
        Bus reading process.
        """
        self.logger.debug(u'BusClient %s started' % self.__module)

        #configuration
        try:
            self._configure()
        except:
            self.logger.exception('Exception during module "%s" configuration:' % self.__module)
            self.crash_report.report_exception()
        finally:
            self.join_event.set()

        #check messages
        while self.__continue:
            try:

                #custom process (do not crash bus on exception)
                try:
                    self._custom_process()
                except Exception as e:
                    self.logger.error('Critical error occured in custom_process: %s' % str(e))
                    self.crash_report.report_exception()

                msg = {}
                try:
                    #get message
                    msg = self.bus.pull(self.__module)

                except NoMessageAvailable:
                    #no message available
                    #release CPU
                    time.sleep(.25)
                    continue

                except KeyboardInterrupt:
                    #user stop raspiot
                    break

                #create response
                resp = MessageResponse()
       
                #process message
                if msg.has_key(u'message'):
                    if msg[u'message'].has_key(u'command'):
                        #command received, process it
                        if msg[u'message'].has_key(u'command') and msg[u'message'][u'command']!=None and len(msg[u'message'][u'command'])>0:
                            try:
                                #get command reference
                                command = getattr(self, msg[u'message'][u'command'])
                                self.logger.debug(u'%s received command "%s" from "%s" with params: %s' % (self.__module, msg[u'message'][u'command'], msg[u'message'][u'from'], msg[u'message'][u'params']))

                                #check if command was found
                                if command is not None:
                                    #check if message contains all command parameters
                                    (ok, args) = self.__check_params(command, msg[u'message'][u'params'], msg[u'message'][u'from'])
                                    #self.logger.debug(u'Command ok=%s args=%s' % (ok, args))
                                    if ok:
                                        #execute command
                                        try:
                                            resp.data = command(**args)

                                        except CommandError as e:
                                            self.logger.error(u'Command error: %s' % unicode(e))
                                            resp.error = True
                                            resp.message = unicode(e)

                                        except CommandInfo as e:
                                            #informative message
                                            resp.message = unicode(e)

                                        except Exception as e:
                                            #command failed
                                            self.logger.exception(u'bus.run exception')
                                            resp.error = True
                                            resp.message = u'%s' % unicode(e)
                                    else:
                                        self.logger.error(u'Some command "%s" parameters are missing: %s' % (msg[u'message'][u'command'], msg[u'message'][u'params']))
                                        resp.error = True
                                        resp.message = u'Some command parameters are missing'

                            except AttributeError:
                                #specified command doesn't exists in this module
                                if not msg[u'message'][u'broadcast']:
                                    #log message only for non broadcasted message
                                    self.logger.exception(u'Command "%s" doesn\'t exist in "%s" module' % (msg[u'message'][u'command'], self.__module))
                                    resp.error = True
                                    resp.message = u'Command "%s" doesn\'t exist in "%s" module' % (msg[u'message'][u'command'], self.__module)

                            except:
                                #specified command is malformed
                                self.logger.exception(u'Command is malformed:')
                                resp.error = True
                                resp.message = u'Received command was malformed'

                        else:
                            #no command specified
                            self.logger.error(u'No command specified in message %s' % msg[u'message'])
                            resp.error = True
                            resp.message = u'No command specified in message'
                                
                        #save response into message    
                        msg[u'response'] = resp.to_dict()

                        #unlock event if necessary
                        if msg[u'event']:
                            #event available, client is waiting for response, unblock it
                            msg[u'event'].set()
                    
                    elif msg[u'message'].has_key(u'event'):
                        if msg[u'message'].has_key(u'from') and msg[u'message'][u'from']==self.__module:
                            #drop event sent to the same module
                            pass
                        else:
                            #event received, process it
                            try:
                                self._event_received(msg[u'message'])
                            except:
                                #do not crash module
                                self.logger.exception(u'Exception in event_received handled by "%s" module:' % self.__class__.__name__)

                else:
                    #received message is badly formatted
                    self.logger.warning(u'Received message is badly formatted, message dropped')

            except:
                #error occured
                self.logger.exception(u'Fatal exception occured running module "%s":' % self.__module)
                self.crash_report.report_exception()
                self.stop()

            #self.logger.debug('----> sleep')
            #time.sleep(1.0)

        #remove subscription
        self.bus.remove_subscription(self.__module)
        self.logger.debug(u'BusClient %s stopped' % self.__module)



class TestPolling(threading.Thread):
    """
    Only for debug purpose
    Object to send periodically message to subscriber
    """
    def __init__(self, bus):
        threading.Thread.__init__(self)
        threading.Thread.daemon = True
        self.bus = bus
        self.c = True

    def stop(self):
        self.c = False

    def run(self):
        while self.c:
            bus.push(time.strftime(u'%A %d %B, %H:%M:%S'))
            time.sleep(5)

if __name__ == '__main__':
    logger = logging.getLogger(u'test')

    class TestProcess1(BusClient):
        def __init__(self, bus):
            BusClient.__init__(self, bus)

        def command1(self):
            print u'command1'
            return u'command1 executed'

        def command2(self, p1, p2):
            print u'command2 wih p1=%s and p2=%s' % (unicode(p1), unicode(p2))

    class TestProcess2(BusClient):
        def __init__(self, bus):
            BusClient.__init__(self, bus)

        def command3(self):
            print u'command3 started'
            time.sleep(3.5)
            print u'command3 ended'

        def command4(self, param):
            print u'command4 wih param=%s' % (unicode(param))

    try:
        bus = MessageBus()
        p1 = TestProcess1(bus)
        p2 = TestProcess2(bus)
        p1.start()
        p2.start()
        msg0 = {u'command':u'command', u'param1':u'hello'}
        msg1 = {u'command':u'command1', u'param1':u'hello'}
        msg2 = {u'command':u'command2', u'p1':u'hello', u'p2':u'world'}
        msg3 = {u'command':u'command2', u'p1':u'hello', u'p3':u'world'}
        msg4 = {u'command':u'command3', u'param1':u'hello'}
        msg5 = {u'command':u'command4', u'param':u'ola que tal'}

        #pause to make sure everything is started
        time.sleep(1.0)

        #==============================================
        logger.info(u'TEST1: send command to non existing module')
        try:
            bus.push(msg0, u'TestProcess')
        except InvalidParameter as e:
            if e.value.lower().find('unknown destination')!=-1:
                logger.info(' -> ok')
            else:
                logger.error(' -> ko')
        time.sleep(1.0)
        
        #==============================================
        logger.info('TEST2: send command with result')
        try:
            resp = bus.push(msg1, 'TestProcess1')
            if resp and resp['data']=='command1 executed':
                logger.info(' -> ok')
            else:
                logger.error(' -> ko')
        except:
            logger.exception(' -> ko')
        time.sleep(1.0)

        #==============================================
        logger.info('TEST3: send command with 2 params')
        try:
            resp = bus.push(msg2, 'TestProcess1')
            if resp['error']:
                logger.error(' -> ko')
            else:
                logger.info(' -> ok')
        except:
            logger.exception(' -> ko')
        time.sleep(1.0)

        #==============================================
        logger.info('TEST4: send command with 2 params with one invalid')
        try:
            resp = bus.push(msg3, 'TestProcess1')
            if resp['error'] and resp['message']=='Some command parameters are missing':
                logger.info(' -> ok')
            else:
                logger.error(' -> ko')
        except:
            logger.exception(' -> ko')
        time.sleep(1.0)

        #==============================================
        logger.info('TEST5: send command to module that doesn\'t implement command')
        try:
            resp = bus.push(msg3, 'TestProcess2')
            if resp['error'] and resp['message']=='Command command2 doesn\'t exist in TestProcess2 module':
                logger.info(' -> ok')
            else:
                logger.error(' -> ko')
        except:
            logger.exception(' -> ko')
        time.sleep(1.0)

        #==============================================
        logger.info('TEST6: test push timeout')
        try:
            resp = bus.push(msg4, 'TestProcess2')
            logger.error(' -> ko')
        except NoResponse:
            logger.info(' -> ok')
        except:
            logger.exception(' -> ko')
        time.sleep(1.0)

        #==============================================
        logger.info('--------------------------')
        logger.info('Tests ended CTRL-C to quit')
        #==============================================
        while True:
            time.sleep(0.25)
            
    except KeyboardInterrupt:
        print 'CTRL-C'
        p1.stop()
        p2.stop()
        sys.exit(1)

    
