#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.raspiot import RaspIotModule
from raspiot.libs.externalbus import PyreBus
import raspiot
import time

__all__ = [u'Cleepbus']


class Cleepbus(RaspIotModule):

    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Add your device to Cleep home network'
    MODULE_LOCKED = True
    MODULE_URL = None
    MODULE_TAGS = ['bus']
    MODULE_COUNTRY = 'any'

    def __init__(self, bus, debug_enabled):
        """
        Constructor

        Args:
            bus (MessageBus): MessageBus instance
            debug_enabled (bool): flag to set debug level to logger
        """
        RaspIotModule.__init__(self, bus, debug_enabled)
        self.logger.debug('Debug value: %s' % debug_enabled)

        #members
        self.external_bus = PyreBus(self.__on_message_received, self.__on_peer_connected, self.__on_peer_disconnected, debug_enabled, None)
        self.devices = {}

    def _start(self):
        """
        Start module
        """
        self.logger.debug('_start %s' % self.external_bus)
        if self.external_bus:
            version = '0.0.0'
            hostname = 'hostname'
            port = 80
            ssl = False
            self.external_bus.configure(version, hostname, port, ssl, False)

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
        self.logger.debug('_custom_process')
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
        """
        #TODO
        pass

    def __on_peer_connected(self, peer_id, infos):
        """
        Device is connected

        Args:
            peer_id (string): peer identifier
            infos (dict): device informations (ip, port, ssl...)
        """
        self.logger.debug('Peer %s connected: %s' % (peer_id, infos))

    def __on_peer_disconnected(self, peer_id):
        """
        Device is disconnected
        """
        self.logger.debug('Peer %s disconnected' % peer_id)

    def event_received(self, event):
        """
        Watch for specific event

        Args:
            event (MessageRequest): event data
        """
        #handle received event and transfer it to external buf if necessary
        pass


