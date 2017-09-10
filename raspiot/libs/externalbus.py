try:
    from zyre_pyzmq import Zyre as Pyre
except Exception as e:
    from pyre import Pyre
from pyre import zhelper
import zmq
import json
import logging
import time
from threading import Thread
import uuid
try:
    from urlparse import urlparse
except:
    from urllib.parse import urlparse

class ExternalBusMessage():
    def __init__(self, data={}):
        self.command = None
        self.event = None
        self.to = None
        self.params = None

        if len(data)!=0:
            for item in data:
                if item=='command':
                    self.command = command
                elif item=='event':
                    self.event = event
                elif item=='to':
                    self.to = to
                elif item=='params':
                    self.params = params

    def to_dict(self):
        if self.event:
            return {
                'event': self.event,
                'params': self.params, 
                'to': self.to
            }
        else:
            return {
                'command': self.command,
                'params': self.params, 
                'to': self.to
            }

class ExternalBus():
    """
    ExternalBus abstract class
    Provide:
        - clients list handling
        - base bus functions (send_to and broadcast)
        - thread facilities (start, stop and default run function)
        - internal logger with debug enabled or not
    """
    def __init__(self, on_message_received, on_peer_connected, on_peer_disconnected, debug_enabled, crash_report):
        """
        Constructor

        Args:
            debug_enabled (bool): True if debug is enabled
            crash_report (CrashReport): crash report instance
        """
        #members
        self.debug_enabled = debug_enabled
        self.crash_report = crash_report
        self.on_message_received = on_message_received
        self.on_peer_connected = on_peer_connected
        self.on_peer_disconnected = on_peer_disconnected
        self.peers = {}

        #logging
        self.logger = logging.getLogger(self.__class__.__name__)
        if self.debug_enabled:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.WARN)

    def broadcast(self, message):
        """
        broadcast message to all connected peers

        Args:
            message (ExternalBusMessage): message to broadcast
        """
        raise NotImplementedError('broadcast function is not implemented')

    def send_to(self, peer_id, message):
        """
        Send message to specified peer

        Args:
            peer_id (string): message recipient
            message (ExternalBusMessage): message to send
        """
        raise NotImplementedError('send_to function is not implemented')

    def get_peers(self):
        """
        Return connected peers
        """
        return self.peers

    def get_peer_infos(self, peer_id):
        """
        Return peer infos

        Args:
            peer_id (string): peer identifier

        Return:
            dict or None if peer not found
        """
        if peer_id in self.peers.keys():
            return self.peers[peer_id]

        return None

    def _add_peer(self, peer_id, infos):
        """
        Save peer infos

        Args:
            peer_id (string): peer identifier
            infos (dict): associated peer informations
        """
        self.peers[peer_id] = infos

    def _remove_peer(self, peer_id):
        """
        Remove peer

        Args:
            peer_id (string): peer identifier

        Return:
            dict or None if peer not found
        """
        if peer_id in self.peers.keys():
            del self.peers[peer_id]
            return True

        return False


    
class PyreBus(ExternalBus):
    """
    External bus using Pyre lib
    Pyre is python implementation of ZeroMQ ZRE concept (https://rfc.zeromq.org/spec:36/ZRE/)

    This code is based on chat example (https://github.com/zeromq/pyre/blob/master/examples/chat.py)
    """

    CLEEP_NAME = 'CLEEP'
    CLEEP_STOP = '$$STOP$$'

    def __init__(self, on_message_received, on_peer_connected, on_peer_disconnected, debug_enabled, crash_report):
        """
        Constructor

        Args:
            debug_enabled (bool) True if debug is enabled
            crash_report (CrashReport): crash report instance
        """
        ExternalBus.__init__(self, on_message_received, on_peer_connected, on_peer_disconnected, debug_enabled, crash_report)
        
        #pyre logger
        pyre_logger = logging.getLogger('pyre')
        if debug_enabled:
            pyre_logger.setLevel(logging.DEBUG)
        else:
            pyre_logger.setLevel(logging.WARN)
        pyre_logger.addHandler(logging.StreamHandler())
        pyre_logger.propagate = False

        #members
        self.headers = {}
        self.group = 'CLEEP'

    def start(self, version, hostname, port, ssl):
        """
        Start external bus (blocking)

        Args:
            version (string): software version
            hostname (string): hostname
            port (int): web port
            ssl (bool): True if ssl enabled
        """
        #save headers
        self.headers['version'] = version
        self.headers['hostname'] = hostname
        self.headers['port'] = str(port)
        self.headers['ssl'] = '0'
        if ssl:
            self.headers['ssl'] = '1'

        #launch pyre task
        ctx = zmq.Context()
        self.__pipe = zhelper.zthread_fork(ctx, self.__pyre_task)

    def stop(self):
        """
        Custom stop
        """
        #send stop message to unblock pyre task
        self.logger.debug('Send STOP on pipe')
        self.__pipe.send(self.CLEEP_STOP.encode('utf-8'))

    def __pyre_task(self, ctx, pipe):
        """
        """
        node = Pyre('CLEEP')
        for header in self.headers:
            node.set_header(header, self.headers[header])
        node.join(self.group)
        node.start()

        poller = zmq.Poller()
        poller.register(pipe, zmq.POLLIN)
        poller.register(node.socket(), zmq.POLLIN)

        while True:
            items = dict(poller.poll())

            if pipe in items and items[pipe] == zmq.POLLIN:
                #message to send
                data = pipe.recv()
                message = data.decode('utf-8')
                self.logger.debug('Data received on pipe: %s' % message)

                #stop node
                if message==self.CLEEP_STOP:
                    self.logger.debug('Stop Pyre bus')
                    break

                #send message on bus
                if message.to is not None:
                    #whisper message
                    node.whisper(message.to, message.data)

                else:
                    #shout message
                    node.shout(self.group, message.data)

            else:
                #message received
                data = node.recv()
                data_type = data.pop(0)
                data_type = data_type.decode('utf-8')
                data_peer = uuid.UUID(bytes=data.pop(0))
                data_name = data.pop(0)
                data_name = data_name.decode('utf-8')
                self.logger.debug('type=%s peer=%s name=%s' % (data_type, data_peer, data_name))

                if data_type=='SHOUT':
                    #message received
                    message = data.pop(0)
                    #TODO decode json to get externalbusmessage instance
                    self.on_message_received(message)

                elif data_type=='ENTER':
                    #new peer connected
                    self.logger.debug('New peer connected: peer=%s name=%s' % (data_peer, data_name))
                    if data_name==self.CLEEP_NAME:
                        #get headers
                        headers = json.loads(data.pop(0).decode('utf-8'))
                        self.logger.debug('header=%s' % headers)

                        #get peer ip
                        self.logger.debug('Peer endpoint: %s' % node.peer_address(data_peer))
                        peer_endpoint = urlparse(node.peer_address(data_peer))

                        #add new peer
                        try:
                            infos = {
                                'id': data_peer,
                                'hostname': headers['hostname'],
                                'ip': peer_endpoint.hostname,
                                'port': int(headers['port']),
                                'ssl': bool(eval(headers['ssl']))
                            }
                            self._add_peer(data_peer, infos)
                            self.on_peer_connected(data_peer, infos)
                        except:
                            self.logger.exception('Unable to add new peer:')

                    else:
                        #invalid peer
                        self.logger.debug('Invalid peer connected: peer=%s name=%s' % (data_peer, data_name))

                elif data_type=='EXIT':
                    #peer disconnected
                    self.logger.debug('Peer disconnected: peer=%s' % data_peer)
                    self._remove_peer(data_peer)
                    self.on_peer_disconnected(data_peer)

        self.logger.debug('End of pyre bus')
        node.stop()
                
    def broadcast_command(self, command, params):
        """
        Broadcast command
        """
        #prepare message
        message = ExternalBusMessage()
        message.command = command
        message.params = params

        #send message
        self.__pipe.send(message.to_dict())

    def broadcast_event(self, event, params):
        """
        Broadcast command
        """
        #prepare message
        message = ExternalBusMessage()
        message.event = event
        message.params = params

        #send message
        self.__pipe.send(message.to_dict())

    def send_to(self, peer_id, command, params):
        """
        Send command to specified peer
        """
        #check params
        if peer_id not in self.peers.keys():
            raise Exception('Invalid peer specified')

        #prepare message
        message = ExternalBusMessage()
        message.command = command
        message.to = peer_id
        message.params = params

        #send message
        self.__pipe.send(message.to_dict())

    def send_event_to(self, peer_id, event, params):
        """
        Send event to specified peer
        """
        #check params
        if peer_id not in self.peers.keys():
            raise Exception('Invalid peer specified')

        #prepare message
        message = ExternalBusMessage()
        message.event = event
        message.to = peer_id
        message.params = params

        #send message
        self.__pipe.send(message.to_dict())


if __name__ == '__main__':
   
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s.%(funcName)s +%(lineno)s: %(levelname)-8s [%(process)d] %(message)s')

    bus = PyreBus(True, None)
    def run():
        bus.start('0.0.0', 'myhostname', 80, False)
    t = Thread()
    t.run = run

    try:
        t.start()
        while True:
            time.sleep(1.0)
    except:
        logging.exception('Exception:')
        pass

    bus.stop()

    print('END')



