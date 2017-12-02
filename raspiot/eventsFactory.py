#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import importlib
import inspect

__all__ = [u'EventsFactory']

class EventsFactory():
    """
    Events factory
    The goal of this factory is to centralize events to make only used ones available in ui.
    It is also used to check event content before posting them and make sure it is compatible with system.
    """

    def __init__(self, bus):
        """
        Constructor

        Args:
            bus (MessageBus): message bus instance
        """
        #members
        self.events_by_event = {}
        self.events_by_module = {}
        self.bus = bus
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

    def load_events(self):
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
                    u'instance': class_(self.bus),
                    u'used': False,
                    u'modules': []
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
            caller = stack[1][0].f_locals["self"].__class__.__name__
            self.logger.debug('===> %s' % caller)
            #module = caller.split('.')[2]
            module = caller.lower()
            self.logger.debug('Module %s registers event %s' % (module, event_name))

            #update events by event dict
            self.events_by_event[event_name][u'used'] = True
            self.events_by_event[event_name][u'modules'].append(module)

            #update events by module dict
            if module not in self.events_by_module:
                self.events_by_module[module] = []
            self.events_by_module[module].append(event_name)

            return self.events_by_event[event_name][u'instance']

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
        return [ev for ev in self.events_by_event if ev[u'used']]

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


