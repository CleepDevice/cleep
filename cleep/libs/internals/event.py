#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import inspect
from cleep.common import MessageRequest
from cleep.exception import InvalidParameter

class Event():
    """
    Base event class
    """

    # Event name. Must follow following format: <appname>.<type>.<action>, with:
    #
    #   * appname is the name of application which sends event
    #   * type is the type of event (monitoring, sms, email, temperature...)
    #   * and action the event action. It is usually a verb (update, change, add...)
    EVENT_NAME = u''
    # is event a core event
    EVENT_CORE = False
    # list of event parameters
    EVENT_PARAMS = []
    # enable chart generation for this event
    EVENT_CHARTABLE = False

    def __init__(self, bus, formatters_broker):
        """
        Construtor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): FormattersBroker singleton instance
        """
        self.bus = bus
        self.formatters_broker = formatters_broker
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)
        if not hasattr(self, u'EVENT_NAME'):
            raise NotImplementedError(u'EVENT_NAME class member must be declared in "%s"' % self.__class__.__name__)
        if (not isinstance(self.EVENT_NAME, str) and not isinstance(self.EVENT_NAME, unicode)) or len(self.EVENT_NAME)==0:
            raise NotImplementedError(u'EVENT_NAME class member declared in "%s" must be a non empty string' % self.__class__.__name__)
        if not hasattr(self, u'EVENT_PARAMS'):
            raise NotImplementedError(u'EVENT_PARAMS class member must be declared in "%s"' % self.__class__.__name__)
        if not isinstance(self.EVENT_PARAMS, list):
            raise NotImplementedError(u'EVENT_PARAMS class member declared in "%s" must be a list' % self.__class__.__name__)
        if not hasattr(self, u'EVENT_CHARTABLE'):
            raise NotImplementedError(u'EVENT_CHARTABLE class member must be declared in "%s"' % self.__class__.__name__)
        if not isinstance(self.EVENT_CHARTABLE, bool):
            raise NotImplementedError(u'EVENT_CHARTABLE class member declared in "%s" must be a bool' % self.__class__.__name__)

    def _check_params(self, params):
        """
        Check event parameters

        Args:
            params (dict): event parameters

        Returns:
            bool: True if params are valid, False otherwise
        """
        if len(self.EVENT_PARAMS)==0 and (params is None or len(params)==0):
            return True

        return all(key in self.EVENT_PARAMS for key in params.keys())

    def send(self, params=None, device_id=None, to=None, render=True):
        """ 
        Push event message on bus.

        Args:
            params (dict): event parameters.
            device_id (string): device id that send event. If not specified event cannot be monitored.
            to (string): event recipient. If not specified, event will be broadcasted. (to send to ui client set 'rpc')
            render (bool): also propagate event to renderer. False to disable it

        Returns:
            bool: True if event sent successfully
        """
        # get event caller
        stack = inspect.stack()
        caller = stack[1][0].f_locals["self"]
        module = caller.__class__.__name__.lower()

        # check and prepare event
        if self._check_params(params):
            request = MessageRequest()
            request.to = to
            request.sender = module
            request.event = self.EVENT_NAME
            request.core_event = self.EVENT_CORE
            request.device_id = device_id
            request.params = params

            # render event
            if render:
                try:
                    self.render(params)
                except:
                    # can't let render call crash the process
                    self.logger.exception('Unable to render event "%s":' % self.EVENT_NAME)

            # push event to internal bus
            resp = self.bus.push(request, None)
            self.logger.trace('Send push result: %s' % resp)
            if resp[u'error']:
                self.logger.error(u'Unable to render event "%s" to "%s": %s' % (self.EVENT_NAME, to, resp[u'message']))
                return False
            return True

        else:
            raise Exception(u'Invalid event parameters specified for "%s": %s' % (self.EVENT_NAME, params))

    def render(self, params=None):
        """
        Render event to renderers

        Args:
            params (dict): list of event parameters

        Returns:
            bool: True if at least one event was renderered successfully
        """
        # get formatters
        formatters = self.formatters_broker.get_renderers_formatters(self.EVENT_NAME)
        self.logger.trace('Found formatters for event "%s": %s' % (self.EVENT_NAME, formatters))

        # handle no formatters found
        if not formatters:
            return False

        # render profiles
        result = True
        for profile_name in formatters:
            for renderer_name in formatters[profile_name]:
                if not formatters[profile_name][renderer_name].can_render_event(self.EVENT_NAME):
                    self.logger.trace(u'Event "%s" rendering disabled' % self.EVENT_NAME)
                    continue

                # format event params to profile
                profile = formatters[profile_name][renderer_name].format(params)
                if profile is None:
                    self.logger.trace(u'Profile returns None')
                    continue

                # and post profile to renderer
                request = MessageRequest()
                request.command = u'render'
                request.to = renderer_name
                request.params = {u'profile': profile}

                self.logger.trace(u'Push message to render %s' % request)
                resp = self.bus.push(request)
                if resp[u'error']:
                    self.logger.error(u'Unable to render profile "%s" to "%s": %s' % (profile_name, renderer_name, resp[u'message']))
                    result = False

        return result

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
        if not self.EVENT_CHARTABLE:
            return None

        chart_params = self.EVENT_PARAMS
        if hasattr(self, u'EVENT_CHART_PARAMS') and self.EVENT_CHART_PARAMS is not None:
            chart_params = self.EVENT_CHART_PARAMS

        return [{u'field': param, u'value': params.get(param, None)} for param in chart_params]

