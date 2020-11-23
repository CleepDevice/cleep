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
        self.__not_renderable_for = []
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

    def set_renderable(self, renderer_name, renderable):
        """
        Disable event rendering for specified renderer

        Args:
            renderer_name (string): renderer name
            renderable (bool): True to render event for specified renderer, False to disable rendering
        """
        if renderable and renderer_name in self.__not_renderable_for:
            self.__not_renderable_for.remove(renderer_name)
        elif not renderable and renderer_name not in self.__not_renderable_for:
            self.__not_renderable_for.append(renderer_name)

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
            self.bus.push(request, None)
            return True

        raise Exception('Invalid event parameters specified for "%s": %s' % (self.EVENT_NAME, params))

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
        for profile_name in formatters:
            for renderer_name in formatters[profile_name]:
                if renderer_name in self.__not_renderable_for:
                    self.logger.debug('Event "%s" rendering disabled for "%s" renderer' % (self.EVENT_NAME, renderer_name))
                    continue

                # format event params to profile
                profile = formatters[profile_name][renderer_name].format(params)
                if profile is None:
                    self.logger.debug('Profile returns None')
                    continue

                # and post profile to renderer
                request = MessageRequest()
                request.command = 'render'
                request.to = renderer_name
                request.params = {'profile': profile}

                self.logger.debug('Push message to renderer "%s": %s' % (renderer_name, request))
                resp = self.bus.push(request)
                if resp['error']:
                    self.logger.error('Unable to render profile "%s" to "%s": %s' % (
                        profile_name,
                        renderer_name,
                        resp['message']
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

