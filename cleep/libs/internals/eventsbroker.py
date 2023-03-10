#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import importlib
import inspect
from cleep.libs.internals.profileformatter import ProfileFormatter
from cleep.libs.internals.tools import full_split_path

__all__ = ["EventsBroker"]


class EventsBroker:
    """
    Events broker
    The goal of this broker is to centralize events to reference all them all in the core.
    It is also used to check event content before posting them and make sure it is compatible with core.
    """

    PYTHON_CLEEP_APPS_IMPORT_PATH = "cleep.modules."
    PYTHON_CLEEP_CORE_EVENTS_IMPORT_PATH = "cleep.events."
    MODULES_DIR = "../../modules"
    CORE_EVENTS_DIR = "../../events"

    def __init__(self, debug_enabled):
        """
        Constructor

        Args:
            debug_enabled (bool): debug status
        """
        # members
        self.events_by_event = {}
        self.events_by_module = {}
        self.events_not_renderable = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)
        self.internal_bus = None
        self.formatters_broker = None
        self.crash_report = None
        self.bootstrap = {}

    def configure(self, bootstrap):
        """
        Configure broker loading needed objects (formatters, events...)

        Args:
            bootstrap (dict): bootstrap objects
        """
        # set members
        self.bootstrap = bootstrap
        self.internal_bus = bootstrap["internal_bus"]
        self.formatters_broker = bootstrap["formatters_broker"]
        self.crash_report = bootstrap["crash_report"]

        # load events
        self.__load_events()

    def __get_external_bus_name(self):
        """
        Return external bus name from boostrap object

        Returns:
            string: external bus name
        """
        return self.bootstrap.get("external_bus", None)

    def __get_event_class_name(self, filename, module):
        """
        Search for event class name trying to match filename with item in module

        Args:
            filename (string): filename (without extension)
            module (module): python module
        """
        return next(
            (item for item in dir(module) if item.lower() == filename.lower()), None
        )

    def __load_events(self):
        """
        Load existing events
        """
        self.__load_events_from_core()
        self.__load_events_from_modules_dir()

        self.logger.debug(
            "Found %d events: %s",
            len(self.events_by_event), self.events_by_event.keys()
        )

    def __save_event(self, class_):
        """
        Save event entry in internal members

        Args:
            class_ (class): event class ready to be instanciated
        """
        self.events_by_event[class_.EVENT_NAME] = {
            "class": class_,
            "used": False,
            "modules": [],
            "formatters": [],
            "profiles": [],
        }

    def __load_events_from_core(self):
        """
        Load existing events from core
        Create an event instance (singleton) for each ones
        """
        path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), self.CORE_EVENTS_DIR)
        )
        self.logger.debug('Loading events from core dir "%s"', path)
        if not os.path.exists(path):
            self.crash_report.report_exception(
                {"message": "Invalid core events path", "path": path}
            )
            raise Exception(f'Invalid core events path "{path}"')

        for root, _, filenames in os.walk(path):
            for filename in filenames:
                self.logger.trace('Analyzing file "%s"', filename)
                try:
                    fullpath = os.path.join(root, filename)
                    (event, ext) = os.path.splitext(filename)
                    if filename.lower().find("event") >= 0 and ext == ".py":
                        self.logger.trace(
                            'Loading "%s%s"',
                            self.PYTHON_CLEEP_CORE_EVENTS_IMPORT_PATH,
                            event
                        )
                        mod_ = importlib.import_module(
                            f"{self.PYTHON_CLEEP_CORE_EVENTS_IMPORT_PATH}{event}"
                        )
                        event_class_name = self.__get_event_class_name(event, mod_)
                        self.logger.trace(
                            "Found event class name: %s", event_class_name
                        )
                        if event_class_name:
                            class_ = getattr(mod_, event_class_name)
                            self.__save_event(class_)
                            self.logger.debug(
                                'Core event "%s" registered', event_class_name
                            )
                        else:
                            self.logger.error(
                                'Event class must have the same name than the filename "%s"',
                                fullpath
                            )

                except AttributeError:  # pragma: no cover
                    self.logger.exception(
                        'Event "%s" has surely invalid name, please refer to coding rules:',
                        event
                    )
                    continue

                except Exception:
                    self.logger.exception(
                        'Event "%s" wasn\'t imported successfully. Please check event source code.',
                        event
                    )
                    continue

    def __load_events_from_modules_dir(self):
        """
        Load existing events from modules directory.
        Create an event instance (singleton) for each ones.
        """
        path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), self.MODULES_DIR)
        )
        self.logger.debug('Loading events from modules dir "%s"', path)
        if not os.path.exists(path):
            self.crash_report.report_exception(
                {"message": "Invalid modules path", "path": path}
            )
            raise Exception(f'Invalid modules path "{path}"')

        for root, _, filenames in os.walk(path):
            for filename in filenames:
                self.logger.trace('Analyzing file "%s"', filename)
                try:
                    fullpath = os.path.join(root, filename)
                    (event, ext) = os.path.splitext(filename)
                    parts = full_split_path(fullpath)
                    if filename.lower().find("event") >= 0 and ext == ".py":
                        self.logger.debug(
                            'Loading "%s%s.%s"',
                            self.PYTHON_CLEEP_APPS_IMPORT_PATH,
                            parts[-2],
                            event
                        )
                        mod_ = importlib.import_module(
                            f"{self.PYTHON_CLEEP_APPS_IMPORT_PATH}{parts[-2]}.{event}"
                        )
                        event_class_name = self.__get_event_class_name(event, mod_)
                        self.logger.trace(
                            "Found event class name: %s", event_class_name
                        )
                        if event_class_name:
                            class_ = getattr(mod_, event_class_name)
                            self.__save_event(class_)
                            self.logger.debug(
                                'Module event "%s" registered', event_class_name
                            )
                        else:
                            self.logger.error(
                                'Event class must have the same name than the filename "%s"',
                                fullpath
                            )

                except AttributeError:  # pragma: no cover
                    self.logger.exception(
                        'Event "%s" has surely invalid name, please refer to coding rules:',
                        event
                    )
                    continue

                except Exception:
                    self.logger.exception(
                        'Event "%s" wasn\'t imported successfully. Please check event source code.',
                        event
                    )
                    continue

    def get_event_instance(self, event_name):
        """
        Return new event instance according to event name
        It also register event callers for event

        Args:
            event_name (string): full event name (xxx.xxx.xxx)

        Returns:
            Event instance

        Raise:
            Exception if event not exists
        """
        if event_name in self.events_by_event:
            # get module caller
            stack = inspect.stack()
            caller = stack[1][0].f_locals["self"]
            module = None
            formatter = None
            if issubclass(caller.__class__, ProfileFormatter):
                # formatter registers event
                formatter = caller.__class__.__name__.lower()
                self.logger.debug(
                    "Formatter %s registers event %s",formatter, event_name
                )
            else:
                # module registers event
                module = caller.__class__.__name__.lower()
                self.logger.debug("Module %s registers event %s",module, event_name)

            # update events by event dict
            self.events_by_event[event_name]["used"] = True
            if module:
                self.events_by_event[event_name]["modules"].append(module)
            if formatter:
                self.events_by_event[event_name]["formatters"].append(formatter)
                profile_name = caller.profile.__class__.__name__
                if profile_name not in self.events_by_event[event_name]["profiles"]:
                    self.events_by_event[event_name]["profiles"].append(profile_name)

            # update events by module dict
            if module:
                if module not in self.events_by_module:
                    self.events_by_module[module] = []
                self.events_by_module[module].append(event_name)

            return self.events_by_event[event_name]["class"](
                {
                    "internal_bus": self.internal_bus,
                    "formatters_broker": self.formatters_broker,
                    "get_external_bus_name": self.__get_external_bus_name,
                    "events_broker": self,
                }
            )

        raise Exception(f'Event "{event_name}" does not exist')

    def get_used_events(self):
        """
        Return dict of used events

        Returns:
            dict: dict of used events::

                {
                    event1: {
                        modules (list): list of modules that reference the event,
                        profiles (list[Event]): list of profiles that references the event
                    },
                    ...
                }

        """
        return {
            k: {"modules": v["modules"], "profiles": v["profiles"]}
            for k, v in self.events_by_event.items()
            if v["used"]
        }

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
            raise Exception(f'Module name "{module_name}" is not referenced in Cleep')

        return self.events_by_module[module_name]

    def set_event_renderable(self, event_name, renderer_name, renderable):
        """
        Set event renderable or not for specified renderer

        Args:
            event_name (string): event name
            renderer_name (string): renderer name
            renderable (bool): True if event is renderable
        """
        if (
            renderable
            and event_name in self.events_not_renderable
            and renderer_name in self.events_not_renderable[event_name]
        ):
            # event is now renderable for renderer, remove entry
            self.events_not_renderable[event_name].remove(renderer_name)
        elif not renderable and event_name not in self.events_not_renderable:
            # event is not renderable, add entry
            self.events_not_renderable[event_name] = [renderer_name]
        elif (
            not renderable
            and event_name in self.events_not_renderable
            and renderer_name not in self.events_not_renderable[event_name]
        ):
            # event is not renderable, append entry
            self.events_not_renderable[event_name].append(renderer_name)

    def is_event_renderable(self, event_name, renderer_name):
        """
        Check if specified event is renderable for specified renderer

        Args:
            event_name (string): event name
            renderer_name (string): renderer name

        Returns:
            bool: True if event is renderable for this renderer
        """
        if event_name not in self.events_not_renderable:
            return True

        return renderer_name not in self.events_not_renderable[event_name]
