#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import threading
import time
import math
import inspect
from collections import deque
from threading import Event
from .libs.task import Task
from Queue import Queue
from utils import MessageResponse, MessageRequest, NoMessageAvailable, InvalidParameter, MissingParameter, BusError, NoResponse, CommandError, CommandInfo

__all__ = ['MessageBus', 'BusClient']

class MessageBus():
    """
    Message bus
    Used to send messages to subscribed clients
    A pushed message can have recipient to directly send message to specific client. In that case
    a response is awaited. If there is no response before end of timeout, an exception is throwed.
    A message without recipient is broadcasted to all subscribers. No response is awaited.
    Only broadcasted messages can be sent before all clients have subscribed (during init phase)
    """
    def __init__(self, debug_enabled):
        #init
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)

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
        self.__defered_messages = Queue()

    def stop(self):
        """
        Stop bus
        """
        if self.__purge:
            self.__purge.stop()

    def app_configured(self):
        """
        Say message bus app is configured
        If not called, all broadcasted messages are stored and not really pushed
        /!\ This way of proceed is dangerous if clients always broadcast messages, the bus may always stay
        blocked in "app not configured" state. But in small system like raspiot, it should be fine.
        """
        #first of all unqueue defered messages to preserve order
        self.logger.debug('Unqueue defered message')
        while not self.__defered_messages.empty():
            msg = self.__defered_messages.get()
            #msg.startup = True
            self.logger.debug('Push defered: %s' % str(msg))
            for q in self.__queues:
                self.__queues[q].append(msg)

        #then set app is configured
        self.__app_configured = True

        #and finally launch purge subscriptions task
        self.__purge = Task(60.0, self.purge_subscriptions)
        self.__purge.start()

        #now push function will handle new messages

    def push(self, request, timeout=3.0):
        """
        Push message to specified module and wait for response until timeout.
        By default it is blocking but with timeout=0.0 the function returns instantly
        without result, but command is sent.
        @param request: message to push
        @param timeout: time to wait for response. If not specified, function returns None
        @return message response
        @raise InvalidParameter, NoResponse
        """
        if isinstance(request, MessageRequest):
            #get request as dict
            request_dict = request.to_dict(not self.__app_configured)

            #push message to specified queue
            if self.__queues.has_key(request.to):
                #prepare event
                event = None
                if timeout:
                    event = Event()

                #prepare message
                msg = {'message':request_dict, 'event':event, 'response':None}
                self.logger.debug('MessageBus: push to "%s" message %s' % (request.to, str(msg)))

                #log module activity
                self.__activities[request.to] = time.time()

                #append message to queue
                self.__queues[request.to].appendleft(msg)

                #and wait for response or not (if no timeout)
                if event:
                    #wait for response
                    self.logger.debug('MessageBus: push wait for response (%s seconds)....' % str(timeout))
                    if event.wait(timeout):
                        #response received
                        self.logger.debug(' - resp received %s' % str(msg))
                        return msg['response']
                    else:
                        #no response in time
                        self.logger.debug(' - timeout')
                        raise NoResponse()
                else:
                    #no timeout given, return nothing
                    return None

            elif request.to==None:
                #broadcast message to every modules, without waiting for a response
                #prepare message
                msg = {'message':request_dict, 'event':None, 'response':None}
                self.logger.debug('MessageBus: broadcast message %s' % str(msg))

                if self.__app_configured:
                    #append message to queues
                    for q in self.__queues:
                        self.__queues[q].appendleft(msg)
                else:
                    #defer message if app not configured yet
                    self.logger.debug('defer message: %s' % str(msg))
                    self.__defered_messages.put(msg)
    
                return None

            elif not self.__app_configured:
                #surely a message with recipient, but app is not configured yet
                pass

            else:
                #app is configured but recipient is unknown
                raise InvalidParameter('Unknown destination %s, check "to" param' % request.to)

        else:
            raise InvalidParameter('Request parameter must be MessageRequest instance')

    def pull(self, module, timeout=0.5):
        """
        Pull message from specified module queue
        @param module: module name
        @param timeout: time to wait, default is blocking (0.5s)
        @return received message
        @raise InvalidParameter, BusError, NoMessageAvailable
        """
        _module = module.lower()
        if self.__queues.has_key(_module):

            #log module activity
            self.__activities[_module] = int(time.time())

            if not timeout:
                #no timeout specified, try to pop a message and return just after
                try:
                    msg = self.__queues[_module].pop()
                    self.logger.debug('MessageBus: %s pulled noto: %s' % (_module, msg))
                    return msg
                except IndexError:
                    #no message available
                    raise NoMessageAvailable()
                except:
                    self.logger.exception('MessageBus: error when pulling message:')
                    raise BusError('Error when pulling message')
            else:
                #timeout specified, try to read each 0.1 seconds a message until specified timeout
                loop = math.floor(timeout / 0.10)
                i = 0
                while i<loop:
                    try:
                        msg = self.__queues[_module].pop()
                        self.logger.debug('MessageBus: %s pulled %s' % (_module, msg))
                        return msg
                    except IndexError:
                        #no message available
                        pass
                    except:
                        #unhandled error
                        self.logger.exception('MessageBus: error when pulling message:')
                        raise BusError('Error when pulling message')
                    finally:
                        time.sleep(0.10)
                        i += 1

                #end of loop and no message found
                raise NoMessageAvailable()

        else:
            #subscriber not found
            self.logger.error('Module %s not found' % _module)
            raise InvalidParameter('Unknown module name %s, check "module" param' % _module)

    def add_subscription(self, module):
        """
        Add new subscription
        """
        _module = module.lower()
        self.logger.debug('Add subscription for module %s' % _module)
        self.__queues[_module] = deque()
        self.__activities[_module] = int(time.time())

    def remove_subscription(self, module):
        """
        Remove existing subscription
        @raise InvalidParameter
        """
        _module = module.lower()
        self.logger.debug('Remove subscription for module %s' % _module)
        if self.__queues.has_key(_module):
            del self.__queues[_module]
            del self.__activities[_module]
        else:
            #uuid does not exists
            self.logger.error('Subscriber %s not found' % _module)
            raise InvalidParameter('Unknown module name, check "module" param')

    def is_subscribed(self, module):
        """
        Check if module is subscribed
        """
        return self.__queues.has_key(module.lower())

    def purge_subscriptions(self):
        """
        Purge old subscriptions
        """
        now = int(time.time())
        copy = self.__activities.copy()
        for module, last_pull in copy.iteritems():
            if now>last_pull+self.lifetime:
                #remove inactive subscription
                self.logger.debug('Remove obsolete subscription "%s"' % module)
                self.remove_subscription(module)




class BusClient(threading.Thread):
    """
    BusClient class must be inherited to handle message from MessageBus
    It reads module message, read command and execute module command
    Finally it returns command response to message originator
    """
    def __init__(self, bus, pre_start, pre_stop):
        threading.Thread.__init__(self)
        self.__continue = True
        self.bus = bus
        self.__name = self.__class__.__name__
        self.__module = self.__name.lower()
        self.__pre_start = pre_start
        self.__pre_stop = pre_stop

        #add subscription
        self.bus.add_subscription(self.__name)

    def __del__(self):
        self.stop()

    def stop(self):
        self.__continue = False

    def __check_params(self, function, message, sender):
        """
        Check if message contains all necessary function parameters
        @param function: function reference
        @param message: current message content (contains all command parameters)
        @param sender: message sender ("from" item from MessageRequest)
        @return tuple (True/False, args to pass during command call/None)
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
            if param=='self':
                #drop self param
                pass
            elif param=='command_sender':
                #function needs request sender value
                args['command_sender'] = sender
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
        @param request: MessageRequest to push
        @param timeout: time to wait for response. If not specified, function returns None
        @return message response
        @raise InvalidParameter, NoResponse
        """
        if isinstance(request, MessageRequest):
            #fill sender
            request.from_ = self.__module

            if request.is_broadcast() or timeout is None or timeout==0.0:
                #broadcast message or no timeout, so no response
                self.bus.push(request, timeout)
                return None
            else:
                #response awaited
                resp = self.bus.push(request, timeout)
                return resp
        else:
            raise InvalidParameter('Request parameter must be MessageRequest instance')

    def send_event(self, event, params=None, uuid=None, to=None):
        """
        Helper function to push event message to bus
        @param event: event name
        @param params: event parameters
        @param uuid: device uuid that send event. If not specified event cannot be monitored
        @param to: event recipient. If not specified, event will be broadcasted
        """
        request = MessageRequest()
        request.to = to
        request.event = event
        request.uuid = uuid
        request.params = params

        return self.push(request, None)

    def send_command(self, command, to, params=None, timeout=3.0):
        """
        Helper function to push command message to bus
        @param command: command name
        @param to: command recipient. If None the command is broadcasted but you'll get no reponse in return
        @param params: command parameters
        @param timeout: change default timeout if you wish. Default is 3 seconds
        """
        request = MessageRequest()
        request.to = to
        request.command = command
        request.params = params

        return self.push(request, timeout)

    def run(self):
        """
        Bus reading process
        """
        self.logger.debug('BusClient %s started' % self.__name)

        #call pre start function
        if self.__pre_start:
            self.__pre_start()
        
        #check messages
        while self.__continue:
            try:
                #self.logger.debug('BusClient: pull message')
                msg = {}
                try:
                    #get message
                    msg = self.bus.pull(self.__name)
                    #self.logger.debug('BusClient: %s received %s' % (self.__name, msg))

                except NoMessageAvailable:
                    #no message available
                    #self.logger.debug('BusClient no msg avail')
                    continue

                except KeyboardInterrupt:
                    #user stop raspiot
                    break

                #create response
                resp = MessageResponse()
       
                #process message
                #self.logger.debug('BusClient: %s process message' % (self.__name))
                if msg.has_key('message'):
                    if msg['message'].has_key('command'):
                        #command received, process it
                        if msg['message'].has_key('command') and msg['message']['command']!=None and len(msg['message']['command'])>0:
                            try:
                                #get command reference
                                self.logger.debug('BusClient: %s get command' % (self.__name))
                                command = getattr(self, msg['message']['command'])

                                #check if command was found
                                if command is not None:
                                    #check if message contains all command parameters
                                    (ok, args) = self.__check_params(command, msg['message']['params'], msg['message']['from'])
                                    self.logger.debug('BusClient: ok=%s args=%s' % (ok, args))
                                    if ok:
                                        #execute command
                                        try:
                                            resp.data = command(**args)
                                        except CommandError as e:
                                            self.logger.error('Command error: %s' % str(e))
                                            resp.error = True
                                            resp.message = str(e)
                                        except CommandInfo as e:
                                            #informative message
                                            resp.message = str(e)
                                        except Exception as e:
                                            #command failed
                                            self.logger.exception('bus.run exception')
                                            resp.error = True
                                            resp.message = '%s' % str(e)
                                    else:
                                        resp.error = True
                                        resp.message = 'Some command parameters are missing'

                            except AttributeError:
                                #specified command doesn't exists in this module
                                self.logger.exception('Command "%s" doesn\'t exist in "%s" module' % (msg['message']['command'], self.__name))
                                resp.error = True
                                resp.message = 'Command "%s" doesn\'t exist in "%s" module' % (msg['message']['command'], self.__name)

                            except:
                                #specified command is malformed
                                self.logger.exception('Command is malformed:')
                                resp.error = True
                                resp.message = 'Received command was malformed'

                        else:
                            #no command specified
                            self.logger.error('BusClient: No command specified in message %s' % msg['message'])
                            resp.error = True
                            resp.message = 'No command specified in message'
                                
                        #save response into message    
                        msg['response'] = resp.to_dict()

                        #unlock event if necessary
                        if msg['event']:
                            #event available, client is waiting for response, unblock it
                            self.logger.debug('BusClient: unlock event')
                            msg['event'].set()
                    
                    elif msg['message'].has_key('event'):
                        #event received, process it
                        try:
                            event_received = getattr(self, 'event_received')
                            if event_received is not None:
                                #function implemented in object, execute it
                                event_received(msg['message'])
                        except AttributeError:
                            #on_event function not implemented, drop received message
                            #self.logger.debug('event_received not implemented, received message dropped')
                            pass
                        except:
                            #do not crash module
                            self.logger.exception('event_received exception:')

                else:
                    #received message is badly formatted
                    self.logger.warning('Received message is badly formatted, message dropped')

            except:
                #error occured
                self.logger.exception('BusClient: fatal exception')
                self.stop()

            #self.logger.debug('----> sleep')
            #time.sleep(1.0)

        #call pre stop function
        if self.__pre_stop:
            self.__pre_stop()

        #remove subscription
        self.bus.remove_subscription(self.__name)
        self.logger.debug('BusClient %s stopped' % self.__name)



class TestPolling(threading.Thread):
    """
    Only for debug purpose
    Object to send periodically message to subscriber
    """
    def __init__(self, bus):
        threading.Thread.__init__(self)
        self.bus = bus
        self.c = True

    def stop(self):
        self.c = False

    def run(self):
        while self.c:
            bus.push(time.strftime('%A %d %B, %H:%M:%S'))
            time.sleep(5)

if __name__ == '__main__':
    logger = logging.getLogger('test')

    class TestProcess1(BusClient):
        def __init__(self, bus):
            BusClient.__init__(self, bus)

        def command1(self):
            print 'command1'
            return 'command1 executed'

        def command2(self, p1, p2):
            print 'command2 wih p1=%s and p2=%s' % (str(p1), str(p2))

    class TestProcess2(BusClient):
        def __init__(self, bus):
            BusClient.__init__(self, bus)

        def command3(self):
            print 'command3 started'
            time.sleep(3.5)
            print 'command3 ended'

        def command4(self, param):
            print 'command4 wih param=%s' % (str(param))

    try:
        bus = MessageBus()
        p1 = TestProcess1(bus)
        p2 = TestProcess2(bus)
        p1.start()
        p2.start()
        msg0 = {'command':'command', 'param1':'hello'}
        msg1 = {'command':'command1', 'param1':'hello'}
        msg2 = {'command':'command2', 'p1':'hello', 'p2':'world'}
        msg3 = {'command':'command2', 'p1':'hello', 'p3':'world'}
        msg4 = {'command':'command3', 'param1':'hello'}
        msg5 = {'command':'command4', 'param':'ola que tal'}

        #pause to make sure everything is started
        time.sleep(1.0)

        #==============================================
        logger.info('TEST1: send command to non existing module')
        try:
            bus.push(msg0, 'TestProcess')
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

    
