#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import importlib
import inspect
from utils import MissingParameter, InvalidParameter, CommandError

__all__ = [u'FormattersFactory']

class FormattersFactory():
    """
    Formatters factory is in charge of centralizing all formatters
    It also ensures formatters use exiting events
    """

    FORMATTERS_PATH = u'formatters'

    def __init__(self, debug_enabled):
        """
        Constructor

        Args:
            events_factory (EventsFactory): events factory instance
            debug_enabled (bool): debug flag
        """
        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)
        self.events_factory = None
        self.renderers = {}
        self.renderer_profiles = {}
        self.formatters = {}

    def configure(self, bootstrap):
        """
        Configure factory

        Args:
            bootstrap (dict): bootstrap objects
        """
        self.events_factory = bootstrap[u'events_factory']
        self.__load_formatters()

    def __load_formatters(self):
        """ 
        Load all available formatters
        """
        #list all formatters in formatters folder
        path = os.path.join(os.path.dirname(__file__), self.FORMATTERS_PATH)
        if not os.path.exists(path):
            raise CommandError(u'Invalid formatters path')

        #iterates over formatters
        for f in os.listdir(path):
            #build path
            fpath = os.path.join(path, f)
            (formatter, ext) = os.path.splitext(f)
            self.logger.debug(u'Formatter=%s ext=%s' % (formatter, ext))

            #filter files
            if os.path.isfile(fpath) and ext==u'.py' and formatter not in [u'__init__', u'formatter', u'profiles']:

                formatters_ = importlib.import_module(u'raspiot.%s.%s' % (self.FORMATTERS_PATH, formatter))
                for name, class_ in inspect.getmembers(formatters_):

                    #filter imports
                    if name is None:
                        continue
                    if not unicode(class_).startswith(u'raspiot.%s.%s.' % (self.FORMATTERS_PATH, formatter)):
                        continue

                    #create formatter instance
                    instance_ = class_(self.events_factory)

                    #save formatter
                    self.logger.debug(u'Found class %s in %s' % (unicode(class_), formatter) )
                    if not self.formatters.has_key(instance_.event_name):
                        self.formatters[instance_.event_name] = {}
                    self.formatters[instance_.event_name][instance_.profile_name] = instance_
                    self.logger.debug(u'  %s => %s' % (instance_.event_name, instance_.profile_name))

        self.logger.debug(u'FORMATTERS: %s' % self.formatters) 

    def register_renderer(self, type, profiles, command_sender):
        """ 
        Register new renderer

        Args:
            type (string): renderer type (ie: alert for sms/push/email renderer)
            profiles (list of data): used to describe renderer capabilities (ie: screen can have 1 or 2 lines,
                renderer must adapts posted data according to this capabilities)
            command_sender (string): value automatically added by raspiot

        Returns:
            bool: True

        Raises:
            MissingParameter, InvalidParameter
        """
        self.logger.debug(u'Register new renderer %s' % (type))
        #check values
        if type is None or len(type)==0:
            raise MissingParameter(u'Type parameter is missing')
        if profiles is None:
            raise MissingParameter(u'Profiles is missing')
        if len(profiles)==0:
            raise InvalidParameter(u'Profiles must contains at least one profile')

        #update renderers list
        if not self.renderers.has_key(type):
            self.renderers[type] = []
        self.renderers[type].append(command_sender)

        #update renderer profiles list
        for profile in profiles:
            profile_name = profile.__class__.__name__
            if not self.renderer_profiles.has_key(command_sender):
                self.renderer_profiles[command_sender] = []
            self.renderer_profiles[command_sender].append(profile_name)

        self.logger.debug(u'RENDERERS: %s' % self.renderers)
        self.logger.debug(u'RENDERERS PROFILES: %s' % self.renderer_profiles)
     
        return True

    def get_renderers(self):
        """
        Returns list of renderers
        
        Returns:
            list: list of renderers by type::
                {
                    'type1': {
                        'subtype1':  {
                            <profile name>: <profile instance>,
                            ...
                        }
                        'subtype2': ...
                    },
                    'type2': {
                        <profile name>: <renderer instance>
                    },
                    ...
                }
        """
        return self.renderers

    def has_renderer(self, type):
        """
        Return True if at least one renderer is registered for specified type

        Args:
            type (string): renderer type
        
        Returns:
            bool: True if renderer exists or False otherwise
        """
        if len(self.renderers)>0 and self.renderers.has_key(type) and len(self.renderers[type])>0:
            return True

        return False

