from pyre_gevent import Pyre
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
from pyre_gevent.zhelper import get_ifaddrs as zhelper_get_ifaddrs
from pyre_gevent.zhelper import u
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
            data (dict): message content. This parameter is iterated to look for useful members
        """
        self.event = None
        self.to = None
        self.params = None
        self.peer_macs = []
        self.peer_hostname = None
        self.peer_ip = None
        self.device_id = None

        #fill peer infos
        if peer_infos and isinstance(peer_infos, dict):
            self.peer_hostname = peer_infos[u'hostname']
            self.peer_macs = peer_infos[u'macs']
            self.peer_ip = peer_infos[u'ip']

        #fill members from message content
        if len(data)!=0:
            for item in data:
                if item==u'event':
                    self.event = data[item]
                elif item==u'to':
                    self.to = data[item]
                elif item==u'params':
                    self.params = data[item]
                elif item==u'device_id':
                    self.device_id = data[item]

    def __str__(self):
        """
        To string

        Returns:
            string: string representation of message
        """
        return '%s' % self.to_dict()

    def to_reduced_dict(self):
        """
        Build dict with minimum class content.
        It's useful to get reduced dict when you send message through external bus

        Returns:
            dict: minimum members on dict::
                
                {
                    event (string): event name
                    device_id (string): device identifier
                    params (dict): event parameters (can be None)
                }

        """
        out = self.to_dict()
        del out['to']
        del out['peer_macs']
        del out['peer_hostname']
        del out['peer_ip']
        for key in out.keys():
            if out[key] is None:
                del out[key]

        return out

    def to_dict(self):
        """
        Build dict with class content

        Returns:
            dict: members on a dict::

                {
                    event (string): event name
                    device_id (string): device identifier
                    params (dict): event parameters (can be None)
                    to (string): message recipient
                    peers_macs (list): list of peers mac addresses
                    peer_hostname (string): peer hostname
                    peer_ip (string): current peer ip
                }

        """
        return {
            'event': self.event,
            'device_id': self.device_id,
            'params': self.params, 
            'to': self.to,
            'peer_macs': self.peer_macs,
            'peer_hostname': self.peer_hostname,
            'peer_ip': self.peer_ip
        }

class ExternalBus():
    """
    ExternalBus base class

    External bus is only based on event handling.
    This way of doing forces developper to handle async requests only.
    This also reduces bus complexity.

    This class provides:
        - peers list handling
        - base bus functions canvas (not implementation)
        - internal logger with debug enabled or not
    """
    def __init__(self, on_message_received, on_peer_connected, on_peer_disconnected, debug_enabled, crash_report):
        """
        Constructor

        Args:
            on_message_received (callback): function called when message is received on bus
            on_peer_connected (callback): function called when new peer connected
            on_peer_disconnected (callback): function called when peer is disconnected
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

    def _parse_headers(self, headers):
        """
        Parse peer connection header

        Warning:
            Must be implemented

        Args:
            headers (dict): received headers from peer connection

        Returns:
            dict: headers dict with parsed data as needed (json=>dict|list, '1'|'0'=>True|False, '666'=>int(666), ...)
        """
        raise NotImplementedError('_parse_headers is not implemented in "%s"' % self.__class__.__name__)

    def run(self):
        """
        Run external bus process

        Warning:
            Must be implemented
        """
        raise NotImplementedError('run function is not implemented in "%s"' % self.__class__.__name__)

    def run_once(self):
        """
        Run external bus process once

        Warning:
            Must be implemented
        """
        raise NotImplementedError('run_once function is not implemented in "%s"' % self.__class__.__name__)

    def broadcast_event(self, event, params, device_id):
        """
        broadcast event message to all connected peers

        Warning:
            Must be implemented

        Args:
            event (string): event name
            params (dict): event parameters
            device_id (uuid): device identifier that emits event
        """
        raise NotImplementedError('broadcast_event function is not implemented "%s"' % self.__class__.__name__)

    def send_event(self, event, params, device_id, peer_id):
        """
        Send event message to specified peer

        Warning:
            Must be implemented

        Args:
            event (string): event name
            params (dict): event parameters
            device_id (uuid): device identifier that emits event
            peer_id (string): message recipient
        """
        raise NotImplementedError('send_event function is not implemented "%s"' % self.__class__.__name__)

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

        Returns:
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

        Returns:
            dict or None if peer not found
        """
        if peer_id in self.peers.keys():
            del self.peers[peer_id]
            return True

        return False

