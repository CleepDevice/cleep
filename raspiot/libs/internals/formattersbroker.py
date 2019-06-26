#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import importlib
import inspect
from raspiot.utils import MissingParameter, InvalidParameter, CommandError, SYSTEM_MODULES
from raspiot.libs.internals.tools import full_path_split

__all__ = [u'FormattersBroker']

class FormattersBroker():
    """
    Formatters broker is in charge of centralizing all formatters
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
        self.events_broker = None
        #list of renderer module names with format:
        #[
        #   'renderer_module_name1',
        #   'renderer_module_name2',
        #   ...
        #]
        self.__renderers = []
        #dict of formatters sorted by event->profile->module
        #{
        #   "event#1": {
        #       "profile#1": {
        #           "module#1": formatter_instance#1,
        #           ...
        #       },
        #       "profile#2": {
        #           "module#1": formatter_instance#1
        #           "module#3": formatter_instance#3
        #       }
        #   },
        #   "event#2": {
        #       "profile#1": ...,
        #       "profile#3": ...
        #   },
        #   ...
        #}
        self.__loaded_formatters = {}
        self.__formatters = {}
        #mapping list of referenced renderer module profiles with format:
        #{
        #   "module_name1": [
        #       "profile_name1",
        #       "profile_name2",
        #   ],
        #   "module_name2": [
        #       "profile_name3,
        #       ...
        #   ],
        #   ...
        #}
        self.__renderers_profiles = {}
        self.crash_report = None

    def configure(self, bootstrap):
        """
        Configure broker

        Args:
            bootstrap (dict): bootstrap objects
        """
        #set members
        self.events_broker = bootstrap[u'events_broker']

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
        Load all formatters available in current Cleep installation

        Raises:
            Exception if internal error occured
        """
        path = os.path.join(os.path.dirname(__file__), u'../..', u'modules')
        if not os.path.exists(path):
            self.crash_report.report_exception({
                u'message': 'Invalid module path',
                u'path': path
            })
            raise Exception(u'Invalid modules path')

        self.logger.debug(u'Loading formatters:')
        for root, _, filenames in os.walk(path):
            for filename in filenames:
                try:
                    fullpath = os.path.join(root, filename)
                    (formatter, ext) = os.path.splitext(filename)
                    parts = full_path_split(fullpath)
                    module_name = parts[-2]
                    if ext==u'.py' and formatter.lower().endswith(u'formatter'):
                        self.logger.debug(' Found "%s"' % formatter)
                        mod_ = importlib.import_module(u'raspiot.modules.%s.%s' % (module_name, formatter))
                        formatter_class_name = self.__get_formatter_class_name(formatter, mod_)
                        if formatter_class_name:
                            formatter_class_ = getattr(mod_, formatter_class_name)
                            formatter_instance_ = formatter_class_(self.events_broker)

                            #save reference on module where formatter was found
                            if formatter_instance_.event_name not in self.__loaded_formatters:
                                self.__loaded_formatters[formatter_instance_.event_name] = {}
                            if formatter_instance_.profile_name not in self.__loaded_formatters[formatter_instance_.event_name]:
                                self.__loaded_formatters[formatter_instance_.event_name][formatter_instance_.profile_name] = {}
                            self.__loaded_formatters[formatter_instance_.event_name][formatter_instance_.profile_name][module_name] = formatter_instance_
                            self.logger.debug(u' Set formatter "%s" for event "%s" for module "%s"' % (formatter_class_name, formatter_instance_.event_name, module_name))
                        else:
                            self.logger.error(u'Formatter class name must have the same name than filename in "%s"' % formatter)

                except AttributeError:
                    self.logger.exception(u'Formatter in "%s" not loaded: it has surely invalid name. Please refer to coding rules.' % formatter)

                except:
                    self.logger.exception(u'Formatter in "%s" not loaded: it has some problem from inside. Please check code.' % formatter)

        self.__dump_formatters_content(self.__loaded_formatters)

    def __dump_formatters_content(self, formatters):
        """
        Dump specified formatters content. Debug purpose only

        Args:
            formatters (dict): dict of formatters
        """
        if self.logger.getEffectiveLevel()==logging.DEBUG:
            self.logger.debug('Formatters collection:')
            for event in formatters:
                self.logger.debug('%s {' % event)
                for profile in formatters[event]:
                    self.logger.debug('\t%s {' % profile)
                    for renderer in formatters[event][profile]:
                        self.logger.debug('\t\t%s: %s' % (renderer, formatters[event][profile][renderer].__class__.__name__))
                    self.logger.debug('\t}')
                self.logger.debug('}')

    def register_renderer(self, module_name, profiles):
        """ 
        Register new renderer

        Args:
            module_name (string): name of renderer (module name)
            profiles (list): profiles supported by renderer

        Raises:
            MissingParameter, InvalidParameter
        """
        self.logger.debug(u'Register new renderer "%s" with profiles: %s' % (module_name, [profile.__name__ for profile in profiles]))
        #check values
        if profiles is None:
            raise MissingParameter(u'Profiles is missing')
        if not isinstance(profiles, list):
            raise InvalidParameter(u'Profiles must be a list')
        if len(profiles)==0:
            raise InvalidParameter(u'Profiles must contains at least one profile')

        #update renderers list
        self.__renderers.append(module_name)

        #update renderers profiles names list (not instance!)
        self.__renderers_profiles[module_name] = [profile.__name__ for profile in profiles]

        #update renderer profiles list
        for profile in profiles:
            for event_name in self.__loaded_formatters:
                for profile_name in self.__loaded_formatters[event_name]:
                    found_formatter = None
                    if profile_name==profile.__name__:
                        if module_name not in self.__loaded_formatters[event_name][profile_name]:
                            #no formatter for current renderer, set one of existing formatter for this renderer
                            #first_key = self.__loaded_formatters[event_name][profile_name].keys()[0]
                            #self.logger.debug('----> %s' % self.__loaded_formatters[event_name][profile_name].keys())
                            #found_formatter = self.__loaded_formatters[event_name][profile_name][first_key]
                            found_formatter = self.__get_best_formatter(module_name, self.__loaded_formatters[event_name][profile_name])
                            self.logger.debug(u'Found formatter "%s" for renderer "%s" for "%s" event' % (found_formatter.__class__.__name__, module_name, event_name))
                        else:
                            #custom formatter found
                            found_formatter = self.__loaded_formatters[event_name][profile_name][module_name]
                            self.logger.debug(u'Found custom formatter "%s" for renderer "%s" for "%s" event' % (found_formatter.__class__.__name__, module_name, event_name))

                    #save formatter if possible
                    if found_formatter:
                        if event_name not in self.__formatters:
                            self.__formatters[event_name] = {}
                        if profile_name not in self.__formatters[event_name]:
                            self.__formatters[event_name][profile_name] = {}
                        if module_name in self.__formatters[event_name][profile_name]:
                            self.logger.warning(u'Renderer "%s" has already "%s" formatter for "%s" event. Formatter "%s" dropped.' % (module_name, self.__formatters[event_name][profile_name][module_name].__class__.__name__, event_name, found_formatter.__class__.__name__))
                        else:
                            self.__formatters[event_name][profile_name][module_name] = found_formatter

        self.__dump_formatters_content(self.__formatters)

    def __get_best_formatter(self, module_name, module_formatters):
        """
        Return best formatters selecting firstly formatters provided by system modules then next available
        """
        system_formatter = None
        for module in module_formatters:
            if module in SYSTEM_MODULES:
                #system modules provides a formatter, save it to fallback on it
                system_formatter = module_formatters[module]
            elif module_name==module:
                #current module provides a formatter use it in priority
                return module_formatters[module]

        #fallback to system formatter
        return system_formatter

    def get_renderers_profiles(self):
        """
        Return list of profiles handled by renderers

        Return:
            list: list of profile handled by renderers
        """
        return self.__renderers_profiles

    def get_renderers(self):
        """
        Returns list of renderers
        
        Returns:
            list: list of renderers
        """
        return self.__renderers

    def get_renderers_formatters(self, event_name):
        """
        Return all formatters by modules that are loaded

        Args:
            event_name (string): event name to search formatters for

        Returns:
            Formatter instances for specified event for each modules that implement it or None if no formatter for this event
        """
        if event_name in self.__formatters:
            return self.__formatters[event_name]

        return None

