#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import inspect
from raspiot.utils import MessageRequest, InvalidParameter

class Event():
    """
    Base event class
    """

    #event name. Must follow following format: <appname>.<type>.<action>, with:
    # - appname is the name of application which sends event
    # - type is the type of event (monitoring, sms, email, temperature...)
    # - and action the event action. It is usually a verb (update, change, add...)
    EVENT_NAME = u''
    #is event a system event
    EVENT_SYSTEM = False
    #list of event params
    EVENT_PARAMS = []
    #enable chart generation for this event
    EVENT_CHARTABLE = False

    def __init__(self, bus, formatters_broker, events_broker):
        """
        Construtor

        Args:
            bus (MessageBus): message bus instance
        """
        self.bus = bus
        self.formatters_broker = formatters_broker
        self.events_broker = events_broker
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)
        if not hasattr(self, u'EVENT_NAME') or len(self.EVENT_NAME)==0:
            raise NotImplementedError(u'EVENT_NAME class member must be declared in "%s"' % self.__class__.__name__)

    def _check_params(self, params):
        """
        Check event parameters

        Args:
            params (dict): event parameters

        Return:
            bool: True if params are valid, False otherwise
        """
        try:
            if len(self.EVENT_PARAMS)==0 and params is None:
                return True

            return all(key in self.EVENT_PARAMS for key in params.keys())
        except:
            self.logger.exception(u'Invalid EVENT_PARAMS for event "%s"' % self.EVENT_NAME)
        
        return False

    def send(self, params=None, device_id=None, to=None, render=True):
        """ 
        Push event message on bus.

        Args:
            params (dict): event parameters.
            device_id (string): device id that send event. If not specified event cannot be monitored.
            to (string): event recipient. If not specified, event will be broadcasted. (to send to ui client set 'rpc')
            render (bool): also propagate event to renderer. False to disable it

        Returns:
            None: event always returns None.
        """
        #get event caller
        stack = inspect.stack()
        caller = stack[1][0].f_locals["self"]
        module = caller.__class__.__name__.lower()

        #check and prepare event
        if self._check_params(params):
            request = MessageRequest()
            request.to = to
            request.from_ = module
            request.event = self.EVENT_NAME
            request.eventsystem = self.EVENT_SYSTEM
            request.device_id = device_id
            request.params = params

            #render event
            if render:
                try:
                    self.render(params)
                except:
                    self.logger.exception('Unable to render event "%s":' % self.EVENT_NAME)

            #pus event to internal bus
            return self.bus.push(request, None)

        else:
            raise Exception(u'Invalid event parameters specified for "%s": %s' % (self.EVENT_NAME, params))

    def render(self, params=None):
        """
        Render event to renderers

        Args:
            params (dict): list of event parameters
        """
        #get formatters
        formatters = self.formatters_broker.get_renderers_formatters(self.EVENT_NAME)
        self.logger.debug('Found formatters for event "%s": %s' % (self.EVENT_NAME, formatters))

        #handle no formatters found
        if not formatters:
            return False

        #render profiles
        for profile_name in formatters:
            for module_name in formatters[profile_name]:
                #format event params to profile
                profile = formatters[profile_name][module_name].format(params)
                if profile is None:
                    continue

                #and post profile to renderer
                try:
                    request = MessageRequest()
                    request.command = u'render'
                    request.to = module_name
                    request.params = {u'profile': profile}

                    resp = self.bus.push(request)
                    if resp[u'error']:
                        self.logger.error(u'Unable to post profile to "%s" renderer: %s' % (renderer, resp[u'message']))

                except:
                    self.logger.exception(u'Unable to push event "%s" to bus:' % self.EVENT_NAME)

    def get_chart_values(self, params):
        """
        Returns chart values
        
        Args:
            params (dict): event parameters

        Returns:
            list: list of field+value or None if no value ::

                [
                    {
                        field (string): field name,
                        value (any): value
                    },
                    ...
                ]
             
        """
        try:
            if not self.EVENT_CHARTABLE:
                return None

            return [{u'field': param, u'value': params.get(param, None)} for param in self.EVENT_PARAMS]
        except:
            self.logger.exception(u'Invalid EVENT_PARAMS for event "%s"' % self.EVENT_NAME)
        
        return []
