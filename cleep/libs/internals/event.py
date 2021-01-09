#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import inspect
from cleep.common import MessageRequest

class Event():
    """
    Base event class
    """

    # Event name. Must follow following format: <appname>.<type>.<action>, with:
    #
    #   * appname is the name of application which sends event
    #   * type is the type of event (monitoring, sms, email, temperature...)
    #   * and action the event action. It is usually a verb (update, change, add...)
    EVENT_NAME = ''
    # is event can be propagated out of the device
    EVENT_PROPAGATE = False
    # list of event parameters
    EVENT_PARAMS = []
    # enable chart generation for this event
    EVENT_CHARTABLE = False

    def __init__(self, params):
        """
        Construtor

        Args:
            params (dict): should contains event parameters
        """
        # check params content
        if len(set(['internal_bus', 'formatters_broker', 'get_external_bus_name']).intersection(params.keys())) != 3:
            raise Exception('Invalid "%s" event, please check constructor parameters' % self.EVENT_NAME)

        # set members
        self.internal_bus = params.get('internal_bus')
        self.formatters_broker = params.get('formatters_broker')
        self.events_broker = params.get('events_broker')
        self.__get_external_bus_name = params.get('get_external_bus_name', lambda: None)
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)
        if not hasattr(self, 'EVENT_NAME'):
            raise NotImplementedError('EVENT_NAME class member must be declared in "%s"' % self.__class__.__name__)
        if not isinstance(self.EVENT_NAME, str) or len(self.EVENT_NAME) == 0:
            raise NotImplementedError(
                'EVENT_NAME class member declared in "%s" must be a non empty string' % self.__class__.__name__
            )
        if not hasattr(self, 'EVENT_PARAMS'):
            raise NotImplementedError('EVENT_PARAMS class member must be declared in "%s"' % self.__class__.__name__)
        if not isinstance(self.EVENT_PARAMS, list):
            raise NotImplementedError('EVENT_PARAMS class member declared in "%s" must be a list' % self.__class__.__name__)
        if not hasattr(self, 'EVENT_CHARTABLE'):
            raise NotImplementedError('EVENT_CHARTABLE class member must be declared in "%s"' % self.__class__.__name__)
        if not isinstance(self.EVENT_CHARTABLE, bool):
            raise NotImplementedError('EVENT_CHARTABLE class member declared in "%s" must be a bool' % self.__class__.__name__)

    def _check_params(self, params):
        """
        Check event parameters

        Args:
            params (dict): event parameters

        Returns:
            bool: True if params are valid, False otherwise
        """
        if len(self.EVENT_PARAMS) == 0 and (params is None or len(params) == 0):
            return True

        return all(key in self.EVENT_PARAMS for key in params.keys())

    def __get_event_caller(self):
        """
        Get module that calls the event

        Returns:
            string: name of the event caller
        """
        stack = inspect.stack()
        caller = stack[2][0].f_locals['self']
        return caller.__class__.__name__.lower()

    def send(self, params=None, device_id=None, to=None, render=True):
        """
        Push event message on bus.

        Args:
            params (dict): event parameters.
            device_id (string): device id that send event. If not specified event cannot be monitored.
            to (string): event recipient. If not specified, event will be broadcasted. (to send to ui client set 'rpc')
            render (bool): also propagate event to renderer. False to disable it

        Raises:
            Exception if parameters are invalid
        """
        # check params
        if not self._check_params(params):
            raise Exception('Invalid event parameters specified for "%s": %s' % (self.EVENT_NAME, params))
        
        # get event caller
        caller_name = self.__get_event_caller()

        # prepare event
        request = MessageRequest()
        request.to = to
        request.sender = caller_name
        request.event = self.EVENT_NAME
        request.propagate = self.EVENT_PROPAGATE
        request.device_id = device_id
        request.params = params

        # render event
        if render:
            try:
                self.render(params)
            except Exception:
                # can't let render call crash the process
                self.logger.exception('Unable to render event "%s":' % self.EVENT_NAME)

        # push event to internal bus (no response awaited for event)
        self.internal_bus.push(request, None)

    def send_to_peer(self, peer_uuid, params=None, device_id=None):
        """
        Push event to peer through external bus

        Args:
            peer_uuid (string): peer uuid
            params (dict): event parameters

        Raises:
            Exception if parameters are invalid
        """
        # check params
        if not self._check_params(params):
            raise Exception('Invalid event parameters specified for "%s": %s' % (self.EVENT_NAME, params))

        # get event caller
        caller_name = self.__get_event_caller()

        # prepare request
        request = MessageRequest()
        request.to = self.__get_external_bus_name()
        request.sender = caller_name
        request.event = self.EVENT_NAME
        request.propagate = False
        request.device_id = device_id
        request.params = params

        # push event to internal bus (no response awaited for event)
        self.internal_bus.push(request, None)

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
        self.logger.debug('Found formatters for event "%s": %s' % (self.EVENT_NAME, formatters))

        # handle no formatters found
        if not formatters:
            return False

        # render profiles
        result = True
        for renderer_name, formatter in formatters.items():
            if not self.events_broker.is_event_renderable(self.EVENT_NAME, renderer_name):
                self.logger.debug('Event "%s" rendering disabled for "%s" renderer' % (self.EVENT_NAME, renderer_name))
                continue

            # format event params to profile
            profile = formatter.format(params)
            if profile is None:
                self.logger.warning(
                    'Profile "%s" is supposed to return data after format function call' % profile.__class__.__name__
                )
                continue

            # and post profile to renderer
            request = MessageRequest()
            request.command = 'render'
            request.to = renderer_name
            request.params = {
                'profile': profile.__class__.__name__,
                'params': profile.to_dict()
            }

            self.logger.debug('Push message to renderer "%s": %s' % (renderer_name, request))
            resp = self.internal_bus.push(request)
            if resp.error:
                self.logger.error('Unable to render profile "%s" for "%s": %s' % (
                    profile.__class__.__name__,
                    renderer_name,
                    resp.message,
                ))
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

        chart_params = getattr(self, 'EVENT_CHART_PARAMS', None) or self.EVENT_PARAMS

        return [{'field': param, 'value': params.get(param, None)} for param in chart_params]

