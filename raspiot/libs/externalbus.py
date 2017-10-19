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
from pyre.zhelper import get_ifaddrs as zhelper_get_ifaddrs
from pyre.zhelper import u
import netifaces
import netaddr
import ipaddress


class ExternalBusMessage():
    """
    Handle ExternalBus message data
    """

    def __init__(self, peer_infos=None, data={}):
        """
        Constructor

        Args:
            peer_infos (dict): infos about peer that sends message
            data (dict): message content. This parameter is iterated to look for useful members (command, event...)
        """
        self.command = None
        self.event = None
        self.to = None
        self.params = None
        self.peer_macs = []
        self.peer_hostname = None
        self.peer_ip = None

        #fill peer infos
        if peer_infos and isinstance(peer_infos, dict):
            self.peer_hostname = peer_infos[u'hostname']
            self.peer_macs = peer_infos[u'macs']
            self.peer_ip = peer_infos[u'ip']

        #fill members from message content
        if len(data)!=0:
            for item in data:
                if item==u'command':
                    self.command = data[item]
                elif item==u'event':
                    self.event = data[item]
                elif item==u'to':
                    self.to = data[item]
                elif item==u'params':
                    self.params = data[item]

    def __str__(self):
        """
        To string
        """
        return '%s' % self.to_dict()

    def to_reduced_dict(self):
        """
        Build dict with minimum class content.
        It's useful to get reduced dict when you send message through external bus

        Return:
            dict: minimum members on dict
        """
        out = self.to_dict()
        del out['to']
        del out['peer_macs']
        del out['peer_hostname']
        del out['peer_ip']

        return out

    def to_dict(self):
        """
        Build dict with class content

        Return:
            dict: members on a dict
        """
        if self.event:
            return {
                'event': self.event,
                'params': self.params, 
                'to': self.to,
                'peer_macs': self.peer_macs,
                'peer_hostname': self.peer_hostname,
                'peer_ip': self.peer_ip
            }
        else:
            return {
                'command': self.command,
                'params': self.params, 
                'to': self.to,
                'peer_macs': self.peer_macs,
                'peer_hostname': self.peer_hostname,
                'peer_ip': self.peer_ip
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
        raise NotImplementedError('run function is not implemented')

    def run_once(self):
        """
        Run external bus process once
        """
        raise NotImplementedError('run_once function is not implemented')

    def broadcast_command(self, command, params):
        """
        broadcast command message to all connected peers

        Args:
            command (string): command name
            params (dict): event parameters
        """
        raise NotImplementedError('broadcast_command function is not implemented')

    def broadcast_event(self, event, params):
        """
        broadcast event message to all connected peers

        Args:
            event (string): event name
            params (dict): event parameters
        """
        raise NotImplementedError('broadcast_event function is not implemented')

    def send_command_to(self, peer_id, command, params):
        """
        Send command message to specified peer

        Args:
            peer_id (string): message recipient
            command (string): command name
            params (dict): command parameters
        """
        raise NotImplementedError('send_command_to function is not implemented')

    def send_event_to(self, peer_id, event, params):
        """
        Send event message to specified peer

        Args:
            peer_id (string): message recipient
            event (string): event name
            params (dict): event parameters
        """
        raise NotImplementedError('send_event_to function is not implemented')

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
        pyre_logger = logging.getLogger('pyre')
        if debug_enabled:
            pyre_logger.setLevel(logging.DEBUG)
        else:
            pyre_logger.setLevel(logging.WARN)
        pyre_logger.addHandler(logging.StreamHandler())
        pyre_logger.propagate = False

        #members
        self.__externalbus_configured = False
        self.pipe_in = None
        self.pipe_out = None

    def get_mac_addresses(self):
        """
        Use pyre zhelper to get list of mac addresses used to identify cleep device
        Code from pyre-gevent

        return:
            list: list of mac addresses
        """
        macs = []
        netinf = zhelper_get_ifaddrs()
        for iface in netinf:
            # Loop over the interfaces and their settings to try to find the broadcast address.
            # ipv4 only currently and needs a valid broadcast address
            for name, data in iface.items():
                self.logger.debug("Checking out interface {0}.".format(name))
                data_2 = data.get(netifaces.AF_INET)
                data_17 = data.get(netifaces.AF_LINK)

                if not data_2:
                    self.logger.debug("No data_2 found for interface {0}.".format(name))
                    continue
                if not data_17:
                    self.logger.debug("No data_17 found for interface {0}.".format(name))
                    continue

                address_str = data_2.get("addr")
                netmask_str = data_2.get("netmask")
                mac_str = data_17.get("addr")

                if not address_str or not netmask_str:
                    self.logger.debug("Address or netmask not found for interface {0}.".format(name))
                    continue

                if isinstance(address_str, bytes):
                    address_str = address_str.decode("utf8")

                if isinstance(netmask_str, bytes):
                    netmask_str = netmask_str.decode("utf8")

                if isinstance(mac_str, bytes):
                    mac_str = mac_str.decode("utf8")

                #keep only private interface
                ip_address = netaddr.IPAddress(address_str)
                if ip_address and not ip_address.is_private():
                    self.logger.debug("Interface {0} refers to public ip address, drop it.".format(name))
                    continue

                interface_string = "{0}/{1}".format(address_str, netmask_str)

                interface = ipaddress.ip_interface(u(interface_string))

                if interface.is_loopback:
                    logger.debug("Interface {0} is a loopback device.".format(name))
                    continue

                if interface.is_link_local:
                    logger.debug("Interface {0} is a link-local device.".format(name))
                    continue

                macs.append(mac_str)

        return macs

    def stop(self):
        """
        Custom stop
        """
        #send stop message to unblock pyre task
        if self.pipe_in is not None:
            self.logger.debug('Send STOP on pipe')
            self.pipe_in.send(json.dumps(self.BUS_STOP.encode('utf-8')))

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

        #get mac addresses
        macs = self.get_mac_addresses()
        self.logger.debug('macs=%s' % macs)

        #communication pipe
        self.pipe_in = self.context.socket(zmq.PAIR)
        self.pipe_in.setsockopt(zmq.LINGER, 0)
        self.pipe_in.setsockopt(zmq.RCVHWM, 100)
        self.pipe_in.setsockopt(zmq.SNDHWM, 100)
        self.pipe_in.setsockopt(zmq.SNDTIMEO, 5000)
        self.pipe_in.setsockopt(zmq.RCVTIMEO, 5000)
        self.pipe_out = self.context.socket(zmq.PAIR)
        self.pipe_out.setsockopt(zmq.LINGER, 0)
        self.pipe_out.setsockopt(zmq.RCVHWM, 100)
        self.pipe_out.setsockopt(zmq.SNDHWM, 100)
        self.pipe_out.setsockopt(zmq.SNDTIMEO, 5000)
        self.pipe_out.setsockopt(zmq.RCVTIMEO, 5000)
        iface = 'inproc://%s' % binascii.hexlify(os.urandom(8))
        self.pipe_in.bind(iface)
        self.pipe_out.connect(iface)

        #create node
        self.node = Pyre('CLEEP')
        self.node.set_header('version', version)
        self.node.set_header('hostname', hostname)
        self.node.set_header('port', str(port))
        self.node.set_header('macs', json.dumps(macs))
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

        #communication socket
        self.node_socket = self.node.socket()

        #poller
        self.poller = zmq.Poller()
        self.poller.register(self.pipe_out, zmq.POLLIN)
        self.poller.register(self.node_socket, zmq.POLLIN)

        self.__externalbus_configured = True

    def run_once(self):
        """
        Run pyre bus once
        """
        #check configuration
        if not self.__externalbus_configured:
            raise Exception('Bus not configured. Please call configure function first')

        try:
            #self.logger.debug(u'Polling...')
            items = dict(self.poller.poll(1000))
        except KeyboardInterrupt:
            #stop requested by user
            return False
        except:
            self.logger.exception('Exception occured durring externalbus polling:')

        if self.pipe_out in items and items[self.pipe_out]==zmq.POLLIN:
            #message to send
            data = self.pipe_out.recv()
            self.logger.debug(u'Raw data received on pipe: %s' % data)
            message = json.loads(data.decode(u'utf-8'))

            #stop node
            if message==self.BUS_STOP:
                self.logger.debug(u'Stop Pyre bus')
                return False

            #send message
            message = ExternalBusMessage(None, message)
            self.logger.debug('Send message: %s' % message.to_reduced_dict())
            if message.to is not None:
                #whisper message
                self.node.whisper(uuid.UUID(message.to), json.dumps(message.to_reduced_dict()).encode('utf-8'))
            else:
                #shout message
                self.node.shout(self.BUS_GROUP, json.dumps(message.to_reduced_dict()).encode('utf-8'))

        elif self.node_socket in items and items[self.node_socket]==zmq.POLLIN:
            #message received
            data = self.node.recv()
            data_type = data.pop(0).decode('utf-8')
            data_peer = uuid.UUID(bytes=data.pop(0))
            data_name = data.pop(0).decode('utf-8')
            self.logger.debug('type=%s peer=%s name=%s' % (data_type, data_peer, data_name))

            if data_type=='SHOUT' or data_type=='WHISPER':
                #message received, decode it and trigger callback
                data_group = data.pop(0).decode('utf-8')

                #check message group
                if data_group!=self.BUS_GROUP:
                    #invalid group?!?
                    self.logger.error('Invalid message group received (%s instaead of %s)' % (data_group, self.BUS_GROUP))

                #trigger message received callback
                try:
                    data_content = data.pop(0)
                    self.logger.debug('Raw data received on bus: %s' % data_content)
                    message = json.loads(data_content.decode(u'utf-8'))
                    peer_infos = self.get_peer_infos(data_peer)
                    self.on_message_received(ExternalBusMessage(peer_infos, message))
                except:
                    self.logger.exception('Unable to parse message:')

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
                            'macs': json.loads(headers['macs']),
                            'version': headers['version'],
                            'hostname': headers['hostname'],
                            'ip': peer_endpoint.hostname,
                            'port': int(headers['port']),
                            'ssl': bool(eval(headers['ssl']))
                        }
                        self._add_peer(data_peer, infos)
                        self.on_peer_connected(str(data_peer), infos)
                    except:
                        self.logger.exception('Unable to add new peer:')

                else:
                    #invalid peer
                    self.logger.debug('Invalid peer connected: peer=%s name=%s' % (data_peer, data_name))

            elif data_type=='EXIT':
                #peer disconnected
                self.logger.debug('Peer disconnected: peer=%s' % data_peer)
                self._remove_peer(data_peer)
                if self.on_peer_disconnected:
                    self.on_peer_disconnected(str(data_peer))
        else:
            #timeout occured
            #self.logger.debug(' polling timeout')
            pass

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
                    self.logger.debug(' ==> stop requested programmatically')
                    break

            except KeyboardInterrupt:
                #user stop
                self.logger.debug(' ==> stop requested manually (CTRL-C)')
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
        self.pipe_in.send(json.dumps(message.to_dict()).encode(u'utf-8'))

    def broadcast_event(self, event, params):
        """
        Broadcast command
        """
        #prepare message
        message = ExternalBusMessage()
        message.event = event
        message.params = params

        #send message
        self.pipe_in.send(json.dumps(message.to_dict()).encode(u'utf-8'))

    def send_command_to(self, peer_id, command, params):
        """
        Send command message to specified peer

        Args:
            peer_id (string): message recipient
            command (string): command name
            params (dict): command parameters
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
        self.pipe_in.send(json.dumps(message.to_dict()).encode(u'utf-8'))

    def send_event_to(self, peer_id, event, params):
        """
        Send event message to specified peer

        Args:
            peer_id (string): message recipient
            event (string): event name
            params (dict): event parameters
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
        self.pipe_in.send(json.dumps(message.to_dict()).encode(u'utf-8'))


if __name__ == '__main__':
   
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s.%(funcName)s +%(lineno)s: %(levelname)-8s [%(process)d] %(message)s')

    class Test(Thread):
        def __init__(self):
            Thread.__init__(self)
            Thread.daemon = True
            self.bus = PyreBus(self.message_received, self.on_connection, self.on_disconnection, True, None)

        def stop(self):
            self.bus.stop()

        def broadcast_event(self, event, params):
            self.bus.logger.info('broadcast event: %s %s' % (event, params))
            self.bus.broadcast_event(event, params)

        def run(self):
            self.bus.configure('0.0.0', 'testbus', 80, False, False)
            self.bus.run()

        def message_received(self, message):
            print(message)

        def on_connection(self, peer_id, infos):
            print(peer_id, infos)

        def on_disconnection(self, peer):
            print(peer)

    t = Test()
    t.start()

    try:
        count = 0
        while True:
            time.sleep(5.0)
            t.broadcast_event('test.event.count', count)
            count += 1
    except KeyboardInterrupt:
        pass
    except:
        logging.exception('Exception:')
        pass

    t.stop()

    print('END')


