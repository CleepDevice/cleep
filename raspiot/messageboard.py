#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import bus
from raspiot import RaspIot
from datetime import datetime
import time

__all__ = ['Messageboard']

#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO);

class Message():
    def __init__(self, message=None, begin=None, end=None):
        self.message = message
        self.begin = begin
        self.end = end


class Messageboard(RaspIot):
    CONFIG_FILE = 'messageboard.conf'
    DEPS = []

    def __init__(self, bus):
        RaspIot.__init__(self, bus)

    def stop(self):
        RaspIot.stop(self)

    def add_advertisment(self, message, begin, end):
        """
        Add advertisment (scrolling message) to display
        @param message: message to display
        @param begin: date to start displaying message from
        @param end: date to stop displaying message
        """
        pass

    def add_message(self, message, begin, end):
        """
        Add message to display
        @param message: message to display
        @param begin: date to start displaying message from
        @param end: date to stop displaying message
        """
        pass
       
    def event_received(self, event):
        """
        Event received
        """
        logger.debug(' *** event received: %s' % str(event))

        if event['event']=='event.time':
            #convert received time to object
            now = datetime.fromtimestamp(event['timestamp'])
            
            #check message to display now
            messages_to_display = []
            config = self._get_config()
            if config['messages'] and len(config['messages'])>0:
                for message in config['messages']:
                    if message['begin']<=now and now<=message['end']:
                        #message can be displayed
                        pass
