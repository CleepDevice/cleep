#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import io
import shutil
import json
import locale
import importlib
from distutils.dir_util import copy_tree
from queue import Queue
from threading import Lock
from cleep.libs.internals.task import Task


class CriticalResources():
    """
    Class to handle critical resources such as audio hardware resource or something else that mustn't
    be called twice at the same time.

    This class only offers a smart resource lock mechanism for developers. It does not garantee to really
    lock a resource if another application wants to use directly the same (hardware or software) resource.

    Refer to Cleep resources directory to know available resources. Feel free to make pull request to add
    new ones.
    
    A typical exemple of resource lock is audio capture. 2 applications can't access at the same time
    the microphone which results of problem during program execution. This class try to resolve that problem
    giving a possibilty to acquire the resource, release it and acquire it again if necessary.
    """

    PYTHON_CLEEP_IMPORT_PATH = u'cleep.resources.'
    RESOURCES_DIR = u'../../resources'

    def __init__(self, debug_enabled):
        """
        Constructor
        """
        #logger
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled: # pragma: no cover
            self.logger.setLevel(logging.DEBUG)

        #members
        self.__mutex = Lock()
        self.crash_report = None
        #resource data:
        # - permanent: module requires permanent access to the resource.
        #              It will be automatically re-acquired when other module release the resource.
        #              Only one module can require permanent access
        # - waiting: module that is waiting for resource acquisition
        # - using: module that is using the resource at this time
        self.resources = {}
        #list of callbacks by module
        self.callbacks = {}

        #load defined resources
        self.__load_resources()

    def set_crash_report(self, crash_report):
        """
        Set crash report

        Args:
            crash_report (CrashReport): CrashReport instance
        """
        self.crash_report = crash_report

    def __report_exception(self, *args, **kwargs):
        """
        Report exception using crash report instance if configured
        """
        if self.crash_report:
            self.crash_report.report_exception(args=args, kwargs=kwargs)

    def __load_resources(self):
        """
        Load existing resources
        """
        path = os.path.join(os.path.dirname(__file__), self.RESOURCES_DIR)
        if not os.path.exists(path):
            self.__report_exception({
                u'message': u'Invalid resources path',
                u'path': path
            })  
            raise Exception(u'Invalid resources path "%s"' % path)

        try:
            for f in os.listdir(path):
                fullpath = os.path.abspath(os.path.join(path, f))
                self.logger.trace('Found resource file "%s"' % fullpath)
                (resource, ext) = os.path.splitext(f)
                self.logger.trace('Resource=%s ext=%s' % (resource, ext))
                if os.path.isfile(fullpath) and ext==u'.py' and resource!=u'__init__' and resource!=u'resource':
                    self.logger.debug('Loading "%s"' % u'%s%s' % (self.PYTHON_CLEEP_IMPORT_PATH, resource))
                    mod_ = importlib.import_module(u'%s%s' % (self.PYTHON_CLEEP_IMPORT_PATH, resource))

                    resource_class_name = self.__get_resource_class_name(resource, mod_)
                    self.logger.trace('resource_class_name=%s' % resource_class_name)
                    if resource_class_name:
                        class_ = getattr(mod_, resource_class_name)
                        self.resources[class_.RESOURCE_NAME] = {
                            u'using': None,
                            u'waiting': [],
                            u'permanent': None,
                        }
                    else:
                        self.logger.error(u'Resource class must have the same name than filename')
                        raise AttributeError('Invalid resource "%s" tryed to be loaded' % resource)

        except AttributeError:
            self.logger.exception(u'Resource "%s" has surely invalid name, please refer to coding rules:' % resource)
            raise Exception('Invalid resource "%s" tryed to be loaded' % resource)

        except:
            self.logger.exception(u'Resource "%s" wasn\'t imported successfully. Please check event source code.' % resource)
            raise Exception('Error occured trying to load resource "%s"' % resource)

    def __get_resource_class_name(self, filename, module):
        """ 
        Search for resource class name trying to match filename with item in module

        Args:
            filename (string): filename (without extension)
            module (module): python module
        """
        return next((item for item in dir(module) if item.lower()==filename.lower()), None)

    def get_resources(self):
        """
        Returns list of existing resources

        Returns:
            list: list of resource names
        """
        return self.resources.keys()

    def __is_resource_referenced(self, resource_name):
        """
        Check if resource name is referenced

        Args:
            resource_name (string): resource name

        Returns:
            bool: True if resource is referenced, False otherwise
        """
        return True if resource_name in self.resources else False

    def register_resource(self, module_name, resource_name, acquired_callback, need_release_callback, permanent=False):
        """
        Register single resource usage

        Args:
            module_name (string): module name which registers the resource
            resource_name (string): resource name (format: <resource> or <resource>.<subresource>)
            acquired_callback (function): function called when resource is acquired
            need_release_callback (function): function called when resource needs to be release
            permanent (bool): True if module declares the need to use the resource permanently.
                              If other module needs to acquire the resource, the permanent module
                              will release temporarly the resource and acquire it again automatically.

        Raises:
            Exception: if resource does not exist or resource already have permanent module configured
        """
        if not self.__is_resource_referenced(resource_name):
            raise Exception(u'Resource "%s" does not exists' % resource_name)
        if not callable(acquired_callback) or not callable(need_release_callback):
            raise Exception(u'Callbacks must be functions')
        self.logger.debug('Registering resource "%s" for module "%s" (permanent=%s)' % (resource_name, module_name, permanent))

        #check if resource already registered and if it's not already have a permanent module
        if self.resources[resource_name][u'permanent'] is not None and permanent is True:
            raise Exception(u'Resource "%s" already has permanent module "%s" configured. Only one allowed' % (resource_name, self.resources[resource_name][u'permanent']))

        #save callbacks
        if module_name not in self.callbacks:
            self.callbacks[module_name] = {}
        self.callbacks[module_name][resource_name] = {
            u'acquired_callback': acquired_callback,
            u'need_release_callback': need_release_callback,
        }
        
        #acquire resource right now if permanent
        if permanent:
            self.resources[resource_name][u'permanent'] = module_name
            self.acquire_resource(module_name, resource_name)

    def is_resource_permanently_acquired(self, resource_name):
        """
        Returns True if specified resource is permanently acquired

        Args:
            resource_name (string): resource name

        Returns:
            bool: True if permanently acquired
        """
        if not self.__is_resource_referenced(resource_name):
            raise Exception(u'Resource "%s" does not exists' % resource_name)

        return True if self.resources[resource_name][u'permanent'] is not None else False

    def acquire_resource(self, module_name, resource_name):
        """
        Try to acquire resource. It will call acquired_resource callback once resource acquired
    
        Args:
            resource_name (string): existing resource name

        Returns:
            Task: acquire resource task

        Raises:
            Exception: if resource does not exist
        """
        if not self.__is_resource_referenced(resource_name):
            raise Exception(u'Resource "%s" does not exists' % resource_name)
        if module_name not in self.callbacks:
            raise Exception(u'Module "%s" try to acquire resource "%s" which it is not registered on' % (module_name, resource_name))

        self.__mutex.acquire()

        self.logger.trace(u'Module "%s" is acquiring resource "%s"' % (module_name, resource_name))
        try:
            if self.resources[resource_name][u'using']==None:
                #resource is not used at this time, acquire it right now
                self.logger.debug(u'Resource "%s" is available, "%s" acquire it right now' % (resource_name, module_name))
                self.resources[resource_name][u'using'] = module_name
                task = Task(None, self.callbacks[module_name][resource_name][u'acquired_callback'], self.logger, [resource_name])
                task.start()

            elif self.resources[resource_name]['using']==module_name:
                self.logger.debug(u'Module "%s" is trying to acquire resource "%s" already acquired by itself. Drop request' % (module_name, resource_name))

            else:
                #resource is not free, add module to waiting queue
                if module_name not in self.resources[resource_name][u'waiting']:
                    self.logger.debug(u'Resource "%s" is in use by "%s", queue module "%s" (queue size=%s)' % (resource_name, self.resources[resource_name]['using'], module_name, len(self.resources[resource_name][u'waiting'])))
                    self.resources[resource_name][u'waiting'].insert(0, module_name)

                #and inform module that is using resource it must releases it
                self.logger.debug(u'Inform module "%s" its acquired resource "%s" is needed by another module' % (self.resources[resource_name][u'using'], resource_name))
                task = Task(None, self.callbacks[self.resources[resource_name][u'using']][resource_name][u'need_release_callback'], self.logger, [resource_name])
                task.start()
                return task

        except:
            self.logger.exception(u'Error occured acquiring critical resource "%s"' % resource_name)
            self.__report_exception({
                u'error': 'Error acquiring critical resource "%s"' % resource_name,
                u'resource_name': resource_name,
                u'module_name': module_name
            })

        finally:
            self.__mutex.release()

    def release_resource(self, module_name, resource_name):
        """
        Release specified resource

        Args:
            module_name (string): module name that releases the resource
            resource_name (string): resource name to release

        Returns:
            Task: release resource task

        Raises:
            Exception: if resource does not exist
        """
        if not self.__is_resource_referenced(resource_name) or not resource_name in self.resources:
            raise Exception(u'Resource "%s" does not exists' % resource_name)

        if not self.resources[resource_name][u'using']:
            #no module has acquired the resource
            self.logger.warning(u'Unable to release not acquired resource "%s"' % resource_name)
            return False

        if self.resources[resource_name][u'using']!=module_name:
            #module is not using resource at this time, it can't release it
            self.logger.warning(u'Module "%s" can\'t release resource "%s" not acquired by it' % (module_name, resource_name))
            return False

        self.__mutex.acquire()

        self.logger.trace(u'Module "%s" is releasing resource "%s"' % (module_name, resource_name))
        try:
            #get next module that wants to acquire resource
            next_module = None
            if len(self.resources[resource_name][u'waiting'])>0:
                next_module = self.resources[resource_name][u'waiting'].pop()
            elif self.resources[resource_name][u'permanent'] is not None:
                next_module = self.resources[resource_name][u'permanent']

            #configure new resource acquirer
            self.resources[resource_name][u'using'] = next_module
            self.logger.trace(u'callbacks: %s' % self.callbacks)
            self.logger.trace(u'next_module: %s' % next_module)
            if next_module:
                self.logger.debug(u'Request next module "%s" for resource "%s" acquisition' % (next_module, resource_name))
                task = Task(None, self.callbacks[next_module][resource_name][u'acquired_callback'], self.logger, [resource_name])
                task.start()
                return task

        except:
            self.logger.exception(u'Error occuring releasing critical resource "%s"' % resource_name)
            self.__report_exception({
                u'error': 'Error releasing critical resource "%s"' % resource_name,
                u'resource_name': resource_name,
                u'module_name': module_name
            })

        finally:
            self.__mutex.release()
