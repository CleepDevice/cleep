#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import importlib
import inspect
from utils import MissingParameter, InvalidParameter, CommandError
from events.formatter import Formatter
from libs.internals.tools import full_path_split

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
        self.crash_report = None

    def configure(self, bootstrap):
        """
        Configure factory loading needed objects (formatters, events...)

        Args:
            bootstrap (dict): bootstrap objects
        """
        #set members
        self.bus = bootstrap[u'message_bus']
        self.formatters_factory = bootstrap[u'formatters_factory']

        #configure crash report
        self.crash_report = bootstrap[u'crash_report']

        #load events
        self.__load_events()

    def __get_event_class_name(self, filename, module):
        """
        Search for event class name trying to match filename with item in module

        Args:
            filename (string): filename (without extension)
            module (module): python module
        """
        return next((item for item in dir(module) if item.lower()==filename.lower()), None)

    def __load_events(self):
        """
        Load existing events
        """
        #self.__load_events_from_events_dir()
        self.__load_events_from_modules_dir()

        self.logger.debug('Found %d events: %s' % (len(self.events_by_event), self.events_by_event.keys()))

    def __save_event(self, class_):
        """
        Save event entry in internal members

        Args:
            class_ (class): event class ready to be instanciated
        """
        self.events_by_event[class_.EVENT_NAME] = {
            u'instance': class_,
            u'used': False,
            u'modules': [],
            u'formatters': [],
            u'profiles': []
        }

    def __load_events_from_modules_dir(self):
        """
        Load existing events from modules directory
        """
        path = os.path.join(os.path.dirname(__file__), u'modules')
        if not os.path.exists(path):
            self.crash_report.report_exception({
                u'message': u'Invalid modules path',
                u'path': path
            })
            raise Exception(u'Invalid modules path')

        try:
            for root, _, filenames in os.walk(path):
                for filename in filenames:
                    fullpath = os.path.join(root, filename)
                    (event, ext) = os.path.splitext(filename)
                    parts = full_path_split(fullpath)
                    if filename.lower().find(u'event')>=0 and ext==u'.py':
                        self.logger.debug('Loading "%s"' % u'raspiot.modules.%s.%s' % (parts[-2], event))
                        mod_ = importlib.import_module(u'raspiot.modules.%s.%s' % (parts[-2], event))
                        event_class_name = self.__get_event_class_name(event, mod_)
                        if event_class_name:
                            class_ = getattr(mod_, event_class_name)
                            self.__save_event(class_)
                        else:
                            self.logger.error(u'Event class must have the same name than filename')

        except AttributeError:
            self.logger.exception(u'Event "%s" has surely invalid name, please refer to coding rules:' % event)
            raise Exception('Invalid event tryed to be loaded')

    def __load_events_from_events_dir(self):
        """
        Load existing events from events directory
        """
        path = os.path.join(os.path.dirname(__file__), u'events')
        if not os.path.exists(path):
            self.crash_report.report_exception({
                u'message': u'Invalid events path',
                u'path': path
            })
            raise Exception(u'Invalid events path')

        try:
            for f in os.listdir(path):
                fullpath = os.path.join(path, f)
                (event, ext) = os.path.splitext(f)
                if os.path.isfile(fullpath) and ext==u'.py' and event!=u'__init__' and event!=u'event':
                    mod_ = importlib.import_module(u'raspiot.events.%s' % event)
                    event_class_name = self.__get_event_class_name(event, mod_)
                    if event_class_name:
                        class_ = getattr(mod_, event.capitalize())
                        self.__save_event(class_)
                    else:
                        self.logger.error(u'Event class must have the same name than filename')

        except AttributeError:
            self.logger.exception(u'Event "%s" has surely invalid name, please refer to coding rules:' % event)
            raise Exception('Invalid event tryed to be loaded')

    def get_event_instance(self, event_name):
        """
        Return event instance according to event name

        Args:
            event_name (string): full event name (xxx.xxx.xxx)

        Returns:
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

        raise Exception(u'Event "%s" does not exist' % event_name)

    def get_used_events(self):
        """
        Return dict of used events

        Returns:
            dict: dict of used events::

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
        Return dict of modules events

        Returns:
            dict: dict of events::

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

        Returns:
            bool: True if event can be rendered, False otherwise
        """
        for item in self.events_not_rendered:
            if item[u'event']==event and item[u'rendered']==renderer:
                return False

        return True


