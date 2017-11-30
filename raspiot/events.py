#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os

__all__ = []

class EventFactory():
    """
    Event factory
    """

    def __init__(self):
        """
        Constructor
        """
        self.events = {}

    def _load_events(self):
        """
        Load existing events
        """
        path = os.path.join(os.path.dirname(__file__), u'events')
        if not os.path.exists(path):
            rasie Exception(u'Invalid events path')

        for f in os.listdir(path):
            fpath = os.path.join(path, f)
            (event, ext) = os.path.splitext(f)
            if os.path.isfile(fpath) and ext==u'.py' and event!=u'__init__' and event!=u'event':
                event_ = importlib.import_module(u'raspiot.events.%s' % event)
                class_ = getattr(event_, event.capitalize())

                #save event
                self.events[class_.EVENT_NAME] = {
                    u'instance': class_(),
                    u'used': False
                }

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
        if event_name in self.events.keys():
            self.events[event_name][u'used'] = True
            return self.events[event_name][u'instance']

        raise Exception(u'Event %s does not exist' % event_name)

    def get_used_events(self):
        """
        Return list of used events

        Return:
            list: list of used events
            
        """
        return [ev for ev in self.events if ev[u'used']]



