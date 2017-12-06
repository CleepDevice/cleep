#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import importlib
import inspect
from utils import MissingParameter, InvalidParameter, CommandError

__all__ = [u'EventsFactory']

class EventsFactory():
    """
    Events factory
    The goal of this factory is to centralize events to make only used ones available in ui.
    It is also used to check event content before posting them and make sure it is compatible with system.
    """

    #FORMATTERS_PATH = u'rendering'

    def __init__(self, debug_enabled):
        """
        Constructor

        Args:
            debug_enabled (bool): debug status
        """
        #members
        self.events_by_event = {}
        self.events_by_module = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)
        #self.renderer_profiles = {}
        #self.renderers = {}
        #self.formatters = {}
        self.bus = None
        self.formatters_factory = None

    def configure(self, bootstrap):
        """
        Configure factory loading needed objects (formatters, events...)

        Args:
            bootstrap (dict): bootstrap objects
        """
        self.bus = bootstrap[u'message_bus']
        self.formatters_factory = bootstrap[u'formatters_factory']
        self.__load_events()
        #self.__load_formatters()

    #def __load_formatters(self):
    #    """
    #    Load all available formatters
    #    """
    #    #list all formatters in formatters folder
    #    path = os.path.join(os.path.dirname(__file__), self.FORMATTERS_PATH)
    #    if not os.path.exists(path):
    #        raise CommandError(u'Invalid formatters path')
    #
    #    #iterates over formatters
    #    for f in os.listdir(path):
    #        #build path
    #        fpath = os.path.join(path, f)
    #        (formatter, ext) = os.path.splitext(f)
    #        self.logger.debug(u'formatter=%s ext=%s' % (formatter, ext))
    #
    #        #filter files
    #        if os.path.isfile(fpath) and ext==u'.py' and formatter not in [u'__init__', u'formatter', u'profiles']:
    #
    #            formatters_ = importlib.import_module(u'raspiot.%s.%s' % (self.FORMATTERS_PATH, formatter))
    #            for name, class_ in inspect.getmembers(formatters_):
    #
    #                #filter imports
    #                if name is None:
    #                    continue
    #                if not unicode(class_).startswith(u'raspiot.%s.%s.' % (self.FORMATTERS_PATH, formatter)):
    #                    continue
    #                instance_ = class_()
    #
    #                #save formatter
    #                self.logger.debug(u'Found class %s in %s' % (unicode(class_), formatter) )
    #                if not self.formatters.has_key(instance_.input_event):
    #                    self.formatters[instance_.input_event] = {}
    #                self.formatters[instance_.input_event][instance_.output_profile] = instance_
    #                self.logger.debug(u'  %s => %s' % (instance_.input_event, instance_.output_profile.__class__.__name__))
    #
    #    self.logger.debug(u'FORMATTERS: %s' % self.formatters)

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
                    u'instance': class_(self.bus, self.formatters_factory),
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
        used_events = {}
        for ev in self.events_by_event:
            if self.events_by_event[ev][u'used']:
                used_events[ev] = self.events_by_event[ev][u'modules'] 

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

    #def register_renderer(self, type, profiles, command_sender):
    #    """
    #    Register new renderer
    #
    #    Args:
    #        type (string): renderer type (ie: alert for sms/push/email renderer)
    #        profiles (list of data): used to describe renderer capabilities (ie: screen can have 1 or 2 lines,
    #            renderer must adapts posted data according to this capabilities)
    #        command_sender (string): value automatically added by raspiot
    #
    #    Returns:
    #        bool: True
    #
    #    Raises:
    #        MissingParameter, InvalidParameter
    #    """
    #    self.logger.debug(u'Register new renderer %s' % (type))
    #    #check values
    #    if type is None or len(type)==0:
    #        raise MissingParameter(u'Type parameter is missing')
    #    if profiles is None:
    #        raise MissingParameter(u'Profiles is missing')
    #    if len(profiles)==0:
    #        raise InvalidParameter(u'Profiles must contains at least one profile')
    #
    #    #update renderers list
    #    if not self.renderers.has_key(type):
    #        self.renderers[type] = []
    #    self.renderers[type].append(command_sender)
    #
    #    #update renderer profiles list
    #    for profile in profiles:
    #        profile_name = profile.__class__.__name__
    #        if not self.renderer_profiles.has_key(command_sender):
    #            self.renderer_profiles[command_sender] = []
    #        self.renderer_profiles[command_sender].append(profile_name)
    #
    #    self.logger.debug(u'RENDERERS: %s' % self.renderers)
    #    self.logger.debug(u'RENDERERS PROFILES: %s' % self.renderer_profiles)
    #
    #    return True
    
    #def get_renderers(self):
    #    """
    #    Returns list of renderers
    #    
    #    Returns:
    #        list: list of renderers by type::
    #            {
    #                'type1': {
    #                    'subtype1':  {
    #                        <profile name>: <profile instance>,
    #                        ...
    #                    }
    #                    'subtype2': ...
    #                },
    #                'type2': {
    #                    <profile name>: <renderer instance>
    #                },
    #                ...
    #            }
    #    """
    #    return self.renderers

    #def has_renderer(self, type):
    #    """
    #    Return True if at least one renderer is registered for specified type
    #
    #    Args:
    #        type (string): renderer type
    #    
    #    Returns:
    #        bool: True if renderer exists or False otherwise
    #    """
    #    if len(self.renderers)>0 and self.renderers.has_key(type) and len(self.renderers[type])>0:
    #        return True
    #
    #    return False

