#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import importlib
import inspect
from raspiot.utils import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.internals.formatter import Formatter
from raspiot.libs.internals.tools import full_path_split

__all__ = [u'EventsBroker']

class EventsBroker():
    """
    Events broker
    The goal of this broker is to centralize events to reference all them all in the core.
    It is also used to check event content before posting them and make sure it is compatible with core.
    """

    PYTHON_RASPIOT_IMPORT_PATH = u'raspiot.modules.'
    MODULES_DIR = u'../../modules'

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
        self.bus = None
        self.formatters_broker = None
        self.crash_report = None

    def configure(self, bootstrap):
        """
        Configure broker loading needed objects (formatters, events...)

        Args:
            bootstrap (dict): bootstrap objects
        """
        #set members
        self.bus = bootstrap[u'message_bus']
        self.formatters_broker = bootstrap[u'formatters_broker']

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
            u'profiles': [],
        }

    def __load_events_from_modules_dir(self):
        """
        Load existing events from modules directory
        """
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), self.MODULES_DIR))
        self.logger.trace(u'Loading events from modules dir "%s"' % path)
        if not os.path.exists(path):
            self.crash_report.report_exception({
                u'message': u'Invalid modules path',
                u'path': path
            })
            raise Exception(u'Invalid modules path "%s"' % path)

        for root, _, filenames in os.walk(path):
            for filename in filenames:
                self.logger.trace('Analyzing file "%s"' % filename)
                try:
                    fullpath = os.path.join(root, filename)
                    (event, ext) = os.path.splitext(filename)
                    parts = full_path_split(fullpath)
                    if filename.lower().find(u'event')>=0 and ext==u'.py':
                        self.logger.debug('Loading "%s"' % u'%s%s.%s' % (self.PYTHON_RASPIOT_IMPORT_PATH, parts[-2], event))
                        mod_ = importlib.import_module(u'%s%s.%s' % (self.PYTHON_RASPIOT_IMPORT_PATH, parts[-2], event))
                        event_class_name = self.__get_event_class_name(event, mod_)
                        self.logger.trace('Found event class name: %s' % event_class_name)
                        if event_class_name:
                            class_ = getattr(mod_, event_class_name)
                            self.__save_event(class_)
                        else:
                            self.logger.error(u'Event class must have the same name than the filename')

                except AttributeError: # pragma: no cover
                    self.logger.exception(u'Event "%s" has surely invalid name, please refer to coding rules:' % event)
                    continue

                except:
                    self.logger.exception(u'Event "%s" wasn\'t imported successfully. Please check event source code.' % event)
                    continue

    def get_event_instance(self, event_name):
        """
        Return event instance according to event name
        It also register event callers for event

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
            caller = stack[1][0].f_locals[u'self']
            module = None
            formatter = None
            if issubclass(caller.__class__, Formatter):
                #formatter registers event
                formatter = caller.__class__.__name__.lower()
                self.logger.debug(u'Formatter %s registers event %s' % (formatter, event_name))
            else:
                #module registers event
                module = caller.__class__.__name__.lower()
                self.logger.debug(u'Module %s registers event %s' % (module, event_name))

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

            return self.events_by_event[event_name][u'instance'](self.bus, self.formatters_broker)

        raise Exception(u'Event "%s" does not exist' % event_name)

    def get_used_events(self):
        """
        Return dict of used events

        Returns:
            dict: dict of used events::

                {
                    event1: {
                        modules (list): list of modules that reference the event,
                        profiles (Event): list of profiles that references the event
                    },
                    ...
                }

        """
        return { k:{u'modules':v[u'modules'], u'profiles':v[u'profiles']} for k,v in self.events_by_event.iteritems() if v['used']}

    def get_modules_events(self):
        """
        Return dict of modules events

        Returns:
            dict: dict of events::

                {
                    module1 (list): [event_name (string), event_name (string), ...],
                    ...
                }

        """
        return self.events_by_module

    def get_module_events(self, module_name):
        """
        Return list of events handled by specified module

        Args:
            module_name (string): module name

        Returns:
            list: list of events

        Raises:
            Exception if module name does not exist
        """
        if module_name not in self.events_by_module.keys():
            raise Exception(u'Module name "%s" is not referenced in raspiot' % module_name)

        return self.events_by_module[module_name]

