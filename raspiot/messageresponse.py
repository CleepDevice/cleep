#!/usr/bin/env python

import sys
import logging
import threading
import time
import math
import inspect
from collections import deque
from threading import Event
from task import Task

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
logger = logging.getLogger(__name__)

class NoResponse(Exception):
    def __str__(self):
        return repr('')

class NoMessageAvailable(Exception):
    def __str__(self):
        return repr('')

class InvalidParameter(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class BusError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class MessageBus():
    """
    Message bus
    Used to send messages to connected clients (ie webui) in polling mode
    """
    
    BROADCAST = '__broadcast__'

    def __init__(self):
        self.__queues = {}

    def broadcast(self, message):
        """
        Push message to all modules
        @info shortcut to push method
        """
        return self.push(message, self.BROADCAST, timeout=0.0)

    def push(self, message, to, timeout=3.0):
        """
        Push message to specified module and wait for response until timeout.
        By default it is blocking but with timeout=0.0 the function returns instantly
        without result, but command is sent.
        @param message: message to push
        @param to: destination module name
        @param timeout: time to wait for response. If not specified, function returns None
        @return message response
        @raise InvalidParameter, NoResponse
        """
        if message and to:
            _to = to.lower()
            #push message to specified queue
            if self.__queues.has_key(_to):
                #prepare event
                event = None
                if timeout:
                    event = Event()

                #prepare output
                msg = {'message':message, 'event':event, 'response':None}

                #append message to queue
                self.__queues[_to].append(msg)
                logger.debug('MessageBus: push: %s' % self.__queues)

                #and wait for response or not (if no timeout)
                if event:
                    #wait for response
                    logger.debug('MessageBus: push wait for response....')
                    if event.wait(timeout):
                        #response received
                        logger.debug(' - resp received')
                        return msg['response']
                    else:
                        #no response in time
                        logger.debug(' - timeout')
                        raise NoResponse()
                else:
                    #no timeout given, return nothing
                    return None
            elif _to==self.BROADCAST:
                #push message to every modules, without waiting for a response
                #prepare output
                msg = {'message':message, 'event':None, 'response':None}

                #append message to queues
                for q in self.__queues:
                    self.__queues[q].append(msg)

                return None
            else:
                raise InvalidParameter('Unknown destination %s, check "to" param' % _to)
        else:
            if not message:
                raise InvalidParameter('Message parameter is missing')
            elif not to:
                raise InvalidParameter('To parameter is missing')

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
            if not timeout:
                #no timeout specified, try to pop a message and return just after
                try:
                    msg = self.__queues[_module].pop()
                    logger.debug('MessageBus: pull wo to: %s' % msg)
                    return msg
                except IndexError:
                    #no message available
                    raise NoMessageAvailable()
                except:
                    logger.exception('MessageBus: error when pulling message:')
                    raise BusError('Error when pulling message')
            else:
                #timeout specified, try to read each 0.25 seconds a message until specified timeout
                loop = math.floor(timeout / 0.25)
                i = 0
                while i<loop:
                    try:
                        msg = self.__queues[_module].pop()
                        logger.debug('MessageBus: pull w to: %s' % msg)
                        return msg
                    except IndexError:
                        #no message available
                        pass
                    except:
                        #unhandled error
                        logger.exception('MessageBus: error when pulling message:')
                        raise BusError('Error when pulling message')
                    finally:
                        time.sleep(0.25)
                        i += 1

                #end of loop and no message found
                raise NoMessageAvailable()

        else:
            #subscriber not found
            logger.error('Module %s not found' % _module)
            raise InvalidParameter('Unknown module name %s, check "module" param' % _module)

    def add_subscription(self, module):
        """
        Add new subscription
        """
        _module = module.lower()
        logger.debug('Add subscription for module %s' % _module)
        self.__queues[_module] = deque()

    def remove_subscription(self, module):
        """
        Remove existing subscription
        @raise InvalidParameter
        """
        _module = module.lower()
        logger.debug('Remove subscription for module %s' % _module)
        if self.__queues.has_key(_module):
            del self.__queues[_module]
        else:
            #uuid does not exists
            logger.error('Subscriber %s not found' % _module)
            raise InvalidParameter('Unknown module name, check "module" param')



class MessageResponse():
    """
    Object that holds message response
    A response is composed of:
     - an error flag: True if error, False otherwise
     - a message: a message about request
     - some data: data returned by the request
    """

    def __init__(self):
        self.error = False
        self.message = ''
        self.data = None

    def __str__(self):
        return '{error:%r, message:%s, data:%s}' % (self.error, self.message, str(self.data))

    def to_dict(self):
        """
        Return message response
        """
        return {'error':self.error, 'message':self.message, 'data':self.data}


class BusClient(threading.Thread):
    """
    BusClient class must be inherited to handle message from MessageBus
    It reads module message, read command and execute module command
    Finally it returns command response to message originator
    """
    def __init__(self, bus):
        threading.Thread.__init__(self)
        self.__continue = True
        self.bus = bus
        self.__name = self.__class__.__name__

    def __del__(self):
        self.stop()

    def stop(self):
        self.__continue = False

    def __check_params(self, function, message):
        """
        Check if message contains all necessary functions parameters
        @param function: function reference
        @param message: current message content (contains all command parameters)
        @return tuple (True/False, args to pass during command call/None)
        """
        args = {}
        (params, _, _, _) = inspect.getargspec(function)
        for param in params:
            if param=='self':
                #drop self param
                pass
            elif not message.has_key(param):
                #parameters is not available in message
                return False, None
            else:
                #update function arguments list
                args[param] = message[param]
        return True, args

    def broadcast(self, message):
        """
        Broadcast message to all modules (no response awaited)
        """
        self.bus.broadcast(message)

    def push(self, message, to, timeout=3.0):
        """
        Push message to specified module and wait for response until timeout.
        By default it is blocking but with timeout=0.0 the function returns instantly
        without result, but command is sent.
        @param message: message to push
        @param to: destination module name
        @param timeout: time to wait for response. If not specified, function returns None
        @return message response
        @raise InvalidParameter, NoResponse
        """
        self.bus.push(message, to, timeout)
       

    def run(self):
        """
        Bus reading process
        """
        logger.info('BusClient %s started' % self.__name)
        #add subscription
        self.bus.add_subscription(self.__name)
        
        #check messages
        while self.__continue:
            try:
                logger.debug('BusClient: pull message')

                try:
                    #get message
                    msg = self.bus.pull(self.__name)
                    logger.debug('BusClient: %s received %s' % (self.__name, msg))

                except NoMessageAvailable:
                    #no message available
                    logger.debug('BusClient no msg avail')
                    continue

                #create response
                resp = MessageResponse()
       
                #process message
                logger.debug('BusClient: %s process message' % (self.__name))
                if msg.has_key('message'):
                    if msg['message'].has_key('command'):
                        #command received, process it
                        if len(msg['message']['command'])>0:
                            try:
                                #get command reference
                                logger.debug('BusClient: %s get command' % (self.__name))
                                command = getattr(self, msg['message']['command'])

                                #check if command was found
                                if command is not None:
                                    #check if message contains all command parameters
                                    (ok, args) = self.__check_params(command, msg['message'])
                                    logger.debug('BusClient: ok=%s args=%s' % (ok, args))
                                    if ok:
                                        #execute command
                                        try:
                                            resp.data = command(**args)
                                        except Exception, e:
                                            #command failed
                                            resp.error = True
                                            resp.message = 'Command execution failed [%s]' % str(e)
                                    else:
                                        #logger.error('Some command parameters are missing')
                                        resp.error = True
                                        resp.message = 'Some command parameters are missing'

                            except AttributeError:
                                #specified command doesn't exists in this module
                                logger.error('Command %s doesn\'t exist in this module' % (msg['message']['command']))
                                resp.error = True
                                resp.message = 'Command %s doesn\'t exist in %s module' % (msg['message']['command'], self.__name)
                        else:
                            #no command specified
                            logger.error('BusClient: No command specified in message')
                            resp.error = True
                            resp.message = 'No command specified in message'
                                
                        #save response into message    
                        msg['response'] = resp.to_dict()

                        #unlock event if necessary
                        if msg['event']:
                            #event available, client is waiting for response, unblock it
                            logger.debug('BusClient: unlock event')
                            msg['event'].set()
                    
                    elif msg['message'].has_key('event'):
                        #event received, process it
                        try:
                            on_event = getattr(self, 'on_event')
                            if on_event is not None:
                                #function implemented in object, execute it
                                on_event(msg['message'])
                        except AttributeError:
                            #on_event function not implemented, drop received message
                            logger.debug('on_event not implemented, received message dropped')

                else:
                    #received message is badly formatted
                    logger.warning('Received message is badly formatted, message dropped')

            except:
                #error occured
                logger.exception('BusClient: fatal exception')

            #logger.debug('----> sleep')
            #time.sleep(1.0)

        #remove subscription
        self.bus.remove_subscription(self.__name)
        logger.info('BusClient %s stopped' % self.__name)



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
        except InvalidParameter, e:
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

    
