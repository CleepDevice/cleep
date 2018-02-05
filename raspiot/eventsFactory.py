#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import importlib
import inspect
from utils import MissingParameter, InvalidParameter, CommandError
from formatters.formatter import Formatter

__all__ = [u'EventsFactory']

class EventsFactory():
    """
    Events factory
    The goal of this factory is to centralize events to make only used ones available in ui.
    It is also used to check event content before posting them and make sure it is compatible with system.
    """

    def __init__(self, debug_enabled):
        """
        Constructor

        Args:
            debug_enabled (bool): debug status
        """
        #members
        self.events_by_event = {}
        self.events_by_module = {}
        self.events_by_formatter = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)
        self.bus = None
        self.formatters_factory = None
        self.events_not_rendered = []

    def configure(self, bootstrap):
        """
        Configure factory loading needed objects (formatters, events...)

        Args:
            bootstrap (dict): bootstrap objects
        """
        self.bus = bootstrap[u'message_bus']
        self.formatters_factory = bootstrap[u'formatters_factory']
        self.__load_events()

    def __load_events(self):
        """
        Load existing events
        """
        path = os.path.join(os.path.dirname(__file__), u'events')
        if not os.path.exists(path):
            raise Exception(u'Invalid events path')

        for f in os.listdir(path):
            fpath = os.path.join(path, f)
            (event, ext) = os.path.splitext(f)
            if os.path.isfile(fpath) and ext==u'.py' and event!=u'__init__' and event!=u'event':
                event_ = importlib.import_module(u'raspiot.events.%s' % event)
                class_ = getattr(event_, event.capitalize())

                #save event
                self.logger.debug('Init %s' % event)
                self.events_by_event[class_.EVENT_NAME] = {
                    u'instance': class_,
                    u'used': False,
                    u'modules': [],
                    u'formatters': [],
                    u'profiles': []
                }

        self.logger.debug('Found %d events' % len(self.events_by_event))

    def get_event_instance(self, event_name):
        """
        Return event instance according to event name

        Args:
            event_name (string): full event name (xxx.xxx.xxx)

        Return:
            Event instance

        Raise:
            Exception if event not exists
        """
        if event_name in self.events_by_event.keys():
            #get module caller
            stack = inspect.stack()
            caller = stack[1][0].f_locals["self"]
            module = None
            formatter = None
            if issubclass(caller.__class__, Formatter):
                #formatter registers event
                formatter = caller.__class__.__name__.lower()
                self.logger.debug('Formatter %s registers event %s' % (formatter, event_name))
            else:
                #module registers event
                module = caller.__class__.__name__.lower()
                self.logger.debug('Module %s registers event %s' % (module, event_name))

            #update events by event dict
            self.events_by_event[event_name][u'used'] = True
            if module:
                self.events_by_event[event_name][u'modules'].append(module)
            if formatter:
                self.events_by_event[event_name][u'formatters'].append(formatter)
                self.events_by_event[event_name][u'profiles'].append(caller.profile.__class__.__name__)

            #update events by module dict
            if module:
                if module not in self.events_by_module:
                    self.events_by_module[module] = []
                self.events_by_module[module].append(event_name)

            return self.events_by_event[event_name][u'instance'](self.bus, self.formatters_factory, self)

        raise Exception(u'Event %s does not exist' % event_name)

    def get_used_events(self):
        """
        Return list of used events

        Return:
            list: list of used events::
                {
                    event1: {
                        used (bool),
                        modules (list),
                        instance (Event)
                    },
                    ...
                }
        """
        used_events = {}
        for ev in self.events_by_event:
            if self.events_by_event[ev][u'used']:
                used_events[ev] = {
                    u'modules': self.events_by_event[ev][u'modules'],
                    u'profiles': self.events_by_event[ev][u'profiles']
                }

        return used_events

    def get_modules_events(self):
        """
        Return list of modules events

        Return:
            dict: list of events::
                {
                    module1: [event1, event2,...],
                    module2: [event1],
                    ...
                }
        """
        return self.events_by_module

    def update_events_not_rendered(self, events_not_rendered):
        """
        Update events to not render

        Args:
            events_not_rendered (list): list of events to not render (see system module)
        """
        self.events_not_rendered = events_not_rendered

    def can_render_event(self, event, renderer):
        """
        Return True if event can be rendered on specified renderer

        Return:
            bool: True if event can be rendered, False otherwise
        """
        for item in self.events_not_rendered:
            if item[u'event']==event and item[u'rendered']==renderer:
                return False

        return True


