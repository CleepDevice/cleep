#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.raspiot import RaspIotModule
from raspiot.libs.externalbus import PyreBus
from raspiot.libs.hostname import Hostname
from raspiot import __version__ as VERSION
import raspiot
import json
import uuid

__all__ = [u'Cleepbus']


class Cleepbus(RaspIotModule):

    MODULE_CONFIG_FILE = u'cleepbus.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Enable communications between all your Cleep devices through your home network'
    MODULE_LOCKED = True
    MODULE_TAGS = [u'bus', u'communication']
    MODULE_COUNTRY = None
    MODULE_LINK = u'https://github.com/tangb/Raspiot/wiki/Cleepbus'

    DEFAULT_CONFIG = {
        u'uuid': None
    }

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #members
        #self.external_bus = PyreBus(self.__on_message_received, self.__on_peer_connected, self.__on_peer_disconnected, self.__decode_bus_headers, debug_enabled, None)
        self.external_bus = PyreBus(self.__on_message_received, self.__on_peer_connected, self.__on_peer_disconnected, self.__decode_bus_headers, True, None)
        #self.external_bus = None
        self.devices = {}
        self.hostname = Hostname(self.cleep_filesystem)
        self.uuid = None

    def _configure(self):
        """
        Configure module
        """
        #set device uuid if not setted yet
        config = self._get_config()
        self.logger.debug('=====>Config: %s' % config)
        if config[u'uuid'] is None:
            self.logger.debug('Set device uuid')
            self.uuid = str(uuid.uuid4())
            config[u'uuid'] = self.uuid
            self._save_config(config)

        else:
            self.uuid = config[u'uuid']

    def get_bus_headers(self):
        """
        Headers to send at bus connection (values must be in string format)

        Return:
            dict: dict of headers (only string supported)
        """
        macs = self.external_bus.get_mac_addresses()
        #TODO handle port and ssl when security implemented
        headers = {
            u'uuid': self.uuid,
            u'version': VERSION,
            u'hostname': self.hostname.get_hostname(),
            u'port': '80',
            u'macs': json.dumps(macs),
            u'ssl': '0',
            u'cleepdesktop': '0'
        }

        return headers

    def __decode_bus_headers(self, headers):
        """
        Decode bus headers fields

        Args:
            headers (dict): dict of values as returned by bus

        Return:
            dict: dict with parsed values
        """
        if u'port' in headers.keys():
            headers[u'port'] = int(headers[u'port'])
        if u'ssl' in headers.keys():
            headers[u'ssl'] = bool(eval(headers[u'ssl']))
        if u'cleepdesktop' in headers.keys():
            headers[u'cleepdesktop'] = bool(eval(headers[u'cleepdesktop']))
        if u'macs' in headers.keys():
            headers[u'macs'] = json.loads(headers[u'macs'])

        return headers

    def _stop(self):
        """
        Stop module
        """
        #stop bus
        self.__stop_external_bus()

    def _custom_process(self):
        """
        Custom process for cleep bus: get new message on external bus
        """
        if self.external_bus.is_running():
            self.external_bus.run_once()

    def __start_external_bus(self):
        """
        Start external bus
        """
        self.logger.debug(u'Start external bus')
        self.external_bus.start(self.get_bus_headers())

    def __stop_external_bus(self):
        """
        Stop external bus
        """
        self.logger.debug(u'Stop external bus')
        self.external_bus.stop()

    def get_network_devices(self):
        """
        Return all Cleep devices found on the network

        Returns:
            dict: devices
        """
        #TODO return list of online devices
        return self.devices

    def __on_message_received(self, message):
        """
        Handle received message from external bus

        Args:
            message (ExternalBusMessage): external bus message instance
        """
        self.logger.debug(u'Message received on external bus: %s' % message)

        #broadcast event to all modules
        peer_infos = {
            'macs': message.peer_macs,
            'ip': message.peer_ip,
            'hostname': message.peer_hostname,
            'device_id': message.device_id
        }
        self.send_external_event(message.event, message.params, peer_infos)

    def __on_peer_connected(self, peer_id, infos):
        """
        Device is connected

        Args:
            peer_id (string): peer identifier
            infos (dict): device informations (ip, port, ssl...)
        """
        self.logger.debug(u'Peer %s connected: %s' % (peer_id, infos))

    def __on_peer_disconnected(self, peer_id):
        """
        Device is disconnected
        """
        self.logger.debug(u'Peer %s disconnected' % peer_id)

    def event_received(self, event):
        """
        Automatically broadcast received events to external bus

        Args:
            event (MessageRequest): event data
        """
        #handle received event and transfer it to external buf if necessary
        self.logger.debug(u'Received event %s' % event)

        #network events to start or stop bus properly and avoid invalid ip address in pyre bus (workaround)
        if event[u'event']==u'system.network.up' and not self.external_bus.is_running():
            #start external bus
            self.__start_external_bus()
            return
        elif event[u'event']==u'system.network.down' and self.external_bus.is_running():
            #stop external bus
            self.__stop_external_bus()
            return

        #drop startup events and system events that should stay local
        if (u'startup' in event.keys() and not event[u'startup']) and not event[u'event'].startswith(u'system.') and not event[u'event'].startswith(u'gpios.'):
            #broadcast local event to external bus
            self.external_bus.broadcast_event(event[u'event'], event[u'params'], event[u'device_id'])
        else:
            #drop current event
            self.logger.debug(u'Received event %s dropped' % event[u'event'])

