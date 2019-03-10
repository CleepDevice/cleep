#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import importlib
import inspect
from utils import MissingParameter, InvalidParameter, CommandError
from libs.internals.tools import full_path_split

__all__ = [u'FormattersFactory']

class FormattersFactory():
    """
    Formatters factory is in charge of centralizing all formatters
    It also ensures formatters use exiting events
    """

    def __init__(self, debug_enabled):
        """
        Constructor

        Args:
            debug_enabled (bool): debug flag
        """
        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)
        self.events_factory = None
        self.renderers = []
        self.renderer_profiles = {}
        self.formatters = {}
        self.crash_report = None

    def configure(self, bootstrap):
        """
        Configure factory

        Args:
            bootstrap (dict): bootstrap objects
        """
        #set members
        self.events_factory = bootstrap[u'events_factory']

        #configure crash report
        self.crash_report = bootstrap[u'crash_report']

        #load formatters
        self.__load_formatters()

    def __get_formatter_class_name(self, filename, module):
        """
        Search for formatter class name trying to match filename with item in module

        Args:
            filename (string): filename (without extension)
            module (module): python module
        """
        return next((item for item in dir(module) if item.lower()==filename.lower()), None)

    def __load_formatters(self):
        """ 
        Load all available formatters
        """
        path = os.path.join(os.path.dirname(__file__), u'modules')
        if not os.path.exists(path):
            self.crash_report.report_exception({
                u'message': 'Invalid module path',
                u'path': path
            })
            raise Exception(u'Invalid modules path')

        for root, _, filenames in os.walk(path):
            for filename in filenames:
                try:
                    fullpath = os.path.join(root, filename)
                    (formatter, ext) = os.path.splitext(filename)
                    parts = full_path_split(fullpath)
                    if ext==u'.py' and filename.lower().endswith(u'formatter'):
                        mod_ = importlib.import_module(u'raspiot.modules.%s.%s' % (parts[-2], formatter))
                        formatter_class_name = self.__get_formatter_class_name(formatter, mod_)
                        if formatter_class_name:
                            class_ = getattr(mod_, formatter_class_name)
                            instance_ = class_(self.events_factory)
                            if not self.formatters.has_key(instance_.event_name):
                                self.formatters[instance_.event_name] = {}
                            self.formatters[instance_.event_name][instance_.profile_name] = instance_
                            self.logger.debug(u'  %s => %s' % (instance_.event_name, instance_.profile_name))
                        else:
                            self.logger.error(u'Event class must have the same name than filename')

                except AttributeError:
                    self.logger.exception(u'Formatter "%s" not loaded: it has surely invalid name, please refer to coding rules:' % formatter)

                except:
                    self.logger.exception(u'Formatter "%s" not loaded: it has some problem from inside. Please check code.' % formatter)

    def register_renderer(self, module_name, profiles):
        """ 
        Register new renderer

        Args:
            module_name (string): name of renderer (module name)
            profiles (list): profiles supported by renderer

        Returns:
            bool: True

        Raises:
            MissingParameter, InvalidParameter
        """
        self.logger.debug(u'Register new renderer "%s"' % module_name)
        #check values
        if profiles is None:
            raise MissingParameter(u'Profiles is missing')
        if len(profiles)==0:
            raise InvalidParameter(u'Profiles must contains at least one profile')

        #update renderers list
        self.renderers.append(module_name)

        #update renderer profiles list
        for profile in profiles:
            profile_name = profile.__name__
            if not self.renderer_profiles.has_key(module_name):
                self.renderer_profiles[module_name] = []
            self.renderer_profiles[module_name].append(profile_name)

        self.logger.debug(u'RENDERERS: %s' % self.renderers)
        self.logger.debug(u'RENDERERS PROFILES: %s' % self.renderer_profiles)
     
        return True

    def get_renderers_profiles(self):
        """
        Return list of profiles handled by renderers

        Return:
            list: list of profile handled by renderers
        """
        return self.renderer_profiles

    def get_renderers(self):
        """
        Returns list of renderers
        
        Returns:
            list: list of renderers
        """
        return self.renderers

