#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from raspiot.utils import MessageRequest, InvalidParameter

class Event():
    """
    Base event class
    """

    def __init__(self, bus, formatters_factory, events_factory):
        """
        Construtor

        Args:
            bus (MessageBus): message bus instance
        """
        self.bus = bus
        self.formatters_factory = formatters_factory
        self.events_factory = events_factory
        self.logger = logging.getLogger(self.__class__.__name__)
        if not hasattr(self, u'EVENT_NAME'):
            raise NotImplementedError(u'EVENT_NAME class member must be declared')

    def _check_params(self, params):
        """
        Check event parameters

        Args:
            params (dict): event parameters

        Return:
            bool: True if params are valid, False otherwise
        """
        raise NotImplementedError(u'_check_params method must implemented')

    def send(self, params=None, device_id=None, to=None):
        """ 
        Push event message on bus.

        Args:
            params (dict): event parameters.
            device_id (string): device id that send event. If not specified event cannot be monitored.
            to (string): event recipient. If not specified, event will be broadcasted. (to send to ui client set 'rpc')

        Returns:
            None: event always returns None.
        """
        if self._check_params(params):
            request = MessageRequest()
            request.to = to
            request.event = self.EVENT_NAME
            request.device_id = device_id
            request.params = params

            return self.bus.push(request, None)

        else:
            raise Exception(u'Invalid event parameters specified: %s' % (params.keys()))

    def render(self, event_values, types):
        """
        Render event to renderer types

        Note:
            TODO remove types?

        Args:
            types (list<string>): existing renderer type
        """
        if not isinstance(types, list):
            raise InvalidParameter(u'Types must be a list')

        #iterates over registered types
        for type in types:
            if self.formatters_factory.has_renderer(type):
                #renderer exists for current type

                #get formatters
                self.logger.debug(u'Searching formatters...')
                formatters = {}
                for formatter in self.formatters_factory.formatters:
                    if formatter.endswith(self.EVENT_NAME):
                        formatters.update(self.formatters_factory.formatters[formatter])

                if len(formatters)==0:
                    #no formatter found, exit
                    self.logger.debug(u'No formatter found for event %s' % self.EVENT_NAME)
                    return False

                #find match with formatters and renderer profiles
                for renderer in self.formatters_factory.renderers[type]:
                    for profile in self.formatters_factory.renderer_profiles[renderer]:
                        if profile in formatters:
                            self.logger.debug(u'Found match, post profile to renderer %s' % renderer)

                            #check if event is not configured to not be rendered
                            if not self.events_factory.can_render_event(self.EVENT_NAME, renderer):
                                self.logger.debug(u' -> Event %s is configured to not be rendered on renderer %s' % (self.EVENT_NAME, renderer))
                                continue

                            #found match, format event to profile
                            profile = formatters[profile].format(event_values)

                            #handle no profile
                            if profile is None:
                                continue

                            #and post profile to renderer
                            try:
                                request = MessageRequest()
                                request.command = u'render'
                                request.to = renderer
                                request.params = {u'profile': profile}

                                resp = self.bus.push(request, timeout)
                                if resp[u'error']:
                                    self.logger.error(u'Unable to post profile to "%s" renderer: %s' % (renderer, resp[u'message']))

                            except:
                                self.logger.exception(u'Unable to render event %s:' % self.EVENT_NAME)

            else:
                #no renderer for current type
                self.logger.debug(u'No renderer registered for %s' % type)

