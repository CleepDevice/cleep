try:
    from zyre_pyzmq import Zyre as Pyre
except Exception as e:
    from pyre import Pyre
import zmq.green as zmq
import json
import logging
import time
from threading import Thread
import uuid
import binascii
import os
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
        - base bus functions implementation (send_to and broadcast)
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

    def run(self):
        """
        Run external bus process
        """
        raise NotImplementedError('broadcast function is not implemented')

    def run_once(self):
        """
        Run external bus process once
        """
        raise NotImplementedError('broadcast function is not implemented')

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

    BUS_NAME = 'CLEEP'
    BUS_GROUP = 'CLEEP'
    BUS_STOP = '$$STOP$$'

    def __init__(self, on_message_received, on_peer_connected, on_peer_disconnected, debug_enabled, crash_report):
        """
        Constructor

        Args:
            debug_enabled (bool) True if debug is enabled
            crash_report (CrashReport): crash report instance
        """
        ExternalBus.__init__(self, on_message_received, on_peer_connected, on_peer_disconnected, debug_enabled, crash_report)
        
        #bus logger
        self.pyre_logger = logging.getLogger('Pyre')
        self.pyre_logger.setLevel(logging.WARN)
        self.pyre_logger.addHandler(logging.StreamHandler())
        self.pyre_logger.propagate = False

        #members
        self.__externalbus_configured = False
        self.pipe = None

    def stop(self):
        """
        Custom stop
        """
        #send stop message to unblock pyre task
        if self.pipe is not None:
            self.logger.debug('Send STOP on pipe')
            self.pipe.send(self.BUS_STOP.encode('utf-8'))

    def configure(self, version, hostname, port, ssl, cleepdesktop):
        """
        Configure bus

        Args:
            version (string): software version
            hostname (string): hostname
            port (int): web port
            ssl (bool): True if ssl enabled
            cleepdesktop (bool): True if client is cleepdesktop
        """
        #zmq context
        self.context = zmq.Context()

        #communication pipe
        self.pipe = self.context.socket(zmq.PAIR)
        self.pipe.setsockopt(zmq.LINGER, 0)
        self.pipe.setsockopt(zmq.LINGER, 0)
        self.pipe.setsockopt(zmq.SNDHWM, 100)
        self.pipe.setsockopt(zmq.SNDTIMEO, 5000)
        self.pipe.setsockopt(zmq.RCVTIMEO, 5000)

        #bus socket
        self.socket = self.context.socket(zmq.PAIR)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.SNDHWM, 100)
        self.socket.setsockopt(zmq.SNDTIMEO, 5000)
        self.socket.setsockopt(zmq.RCVTIMEO, 5000)

        #configure socket and pipe
        iface = 'inproc://%s' % binascii.hexlify(os.urandom(8))
        self.pipe.bind(iface)
        self.socket.connect(iface)

        #create node
        self.node = Pyre('CLEEP')
        self.node.set_header('version', version)
        self.node.set_header('hostname', hostname)
        self.node.set_header('cleepdesktop', str(port))
        if ssl:
            self.node.set_header('ssl', '1')
        else:
            self.node.set_header('ssl', '0')
        if cleepdesktop:
            self.node.set_header('cleepdesktop', '1')
        else:
            self.node.set_header('cleepdesktop', '0')
        self.node.join(self.BUS_GROUP)
        self.node.start()

        #poller
        self.poller = zmq.Poller()
        self.poller.register(self.pipe, zmq.POLLIN)
        self.poller.register(self.node.socket(), zmq.POLLIN)

        self.__externalbus_configured = True

    def run_once(self):
        """
        Run pyre bus once
        """
        #check configuration
        if not self.__externalbus_configured:
            raise Exception('Bus not configured. Please call configure function first')

        self.logger.debug('Polling...')
        items = dict(self.poller.poll())

        if self.pipe in items and items[self.pipe] == zmq.POLLIN:
            #message to send
            data = self.pipe.recv()
            message = data.decode('utf-8')
            self.logger.debug('Data received on pipe: %s' % message)

            #stop node
            if message==self.BUS_STOP:
                self.logger.debug('Stop Pyre bus')
                return False

            #send message
            if message.to is not None:
                #whisper message
                self.node.whisper(uuid.UUID(message.to), message.data)
            else:
                #shout message
                self.node.shout(self.BUS_GROUP, message.data)

        else:
            #message received
            data = self.node.recv()
            data_type = data.pop(0)
            data_type = data_type.decode('utf-8')
            data_peer = uuid.UUID(bytes=data.pop(0))
            data_name = data.pop(0)
            data_name = data_name.decode('utf-8')
            self.logger.debug('type=%s peer=%s name=%s' % (data_type, data_peer, data_name))

            if data_type=='SHOUT' or data_type=='WHISPER':
                #message received
                message = data.pop(0)
                #TODO decode json to get externalbusmessage instance
                self.on_message_received(message)

            elif data_type=='ENTER':
                #new peer connected
                self.logger.debug('New peer connected: peer=%s name=%s' % (data_peer, data_name))
                if data_name==self.BUS_NAME:
                    #get headers
                    headers = json.loads(data.pop(0).decode('utf-8'))
                    self.logger.debug('header=%s' % headers)

                    #get peer ip
                    self.logger.debug('Peer endpoint: %s' % self.node.peer_address(data_peer))
                    peer_endpoint = urlparse(self.node.peer_address(data_peer))

                    #add new peer
                    try:
                        infos = {
                            'id': str(data_peer),
                            'version': headers['version'],
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

        return True

    def run(self):
        """
        Run pyre bus in infinite loop (blocking)
        """
        #check configuration
        if not self.__externalbus_configured:
            raise Exception('Bus not configured. Please call configure_bus function first')

        self.logger.debug('Pyre node started')
        while True:
            try:
                if not self.run_once():
                    #stop requested
                    break

            except KeyboardInterrupt:
                #user stop
                break

            except:
                self.logger.exception('Exception during external bus polling:')
                continue

        self.logger.debug('Pyre node terminated')
        self.node.stop()
                
    def broadcast_command(self, command, params):
        """
        Broadcast command
        """
        #prepare message
        message = ExternalBusMessage()
        message.command = command
        message.params = params

        #send message
        self.pipe.send(message.to_dict())

    def broadcast_event(self, event, params):
        """
        Broadcast command
        """
        #prepare message
        message = ExternalBusMessage()
        message.event = event
        message.params = params

        #send message
        self.pipe.send(message.to_dict())

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
        self.pipe.send(message.to_dict())

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
        self.pipe.send(message.to_dict())


if __name__ == '__main__':
   
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s.%(funcName)s +%(lineno)s: %(levelname)-8s [%(process)d] %(message)s')

    class Test(Thread):
        def __init__(self):
            Thread.__init__(self)
            Thread.daemon = True
            self.bus = PyreBus(self.message_received, self.on_connection, self.on_disconnection, True, None)

        def stop(self):
            self.bus.stop()

        def run(self):
            self.bus.start('0.0.0', 'myhostname', 80, False)

        def message_received(self, message):
            print(message)

        def on_connection(self, peer, infos):
            print(peer, infos)

        def on_disconnection(self, peer):
            print(peer)

    t = Test()
    t.start()

    try:
        while True:
            time.sleep(1.0)
    except:
        logging.exception('Exception:')
        pass

    t.stop()

    print('END')


