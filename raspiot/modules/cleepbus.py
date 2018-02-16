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

__all__ = [u'Cleepbus']


class Cleepbus(RaspIotModule):

    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Enable communications between all your Cleep devices through your home network'
    MODULE_LOCKED = True
    MODULE_TAGS = [u'bus']
    MODULE_COUNTRY = None
    MODULE_LINK = u'https://github.com/tangb/Raspiot/wiki/Cleepbus'

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
        self.hostname = Hostname()

    def get_bus_headers(self):
        """
        Headers to send at bus connection (values must be in string format)

        Return:
            dict: dict of headers (only string supported)
        """
        macs = self.external_bus.get_mac_addresses()
        #TODO handle port and ssl when security implemented
        headers = {
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

    def _configure(self):
        """
        Configure module
        """
        if self.external_bus:
            self.external_bus.configure(self.get_bus_headers())

    def _stop(self):
        """
        Stop module
        """
        #stop bus
        if self.external_bus:
            self.external_bus.stop()

    def _custom_process(self):
        """
        Custom process for cleep bus: get new message on external bus
        """
        self.external_bus.run_once()

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

        #drop startup events and system events that should stay local
        if (u'startup' in event.keys() and not event[u'startup']) and not event[u'event'].startswith(u'system.') and not event[u'event'].startswith(u'gpios.'):
            #broadcast local event to external bus
            self.external_bus.broadcast_event(event[u'event'], event[u'params'], event[u'device_id'])
        else:
            #drop current event
            self.logger.debug(u'Received event %s dropped' % event[u'event'])


