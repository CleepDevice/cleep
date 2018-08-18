#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import inspect
import importlib
import re
import json
import copy
from zipfile import ZipFile, ZIP_DEFLATED
from tempfile import NamedTemporaryFile
from modulefinder import ModuleFinder
from threading import Thread
from raspiot.raspiot import RaspIotModule
from raspiot.libs.internals.task import Task
from raspiot.libs.internals.console import Console
from raspiot.utils import CommandError, MissingParameter, InvalidParameter
from raspiot.libs.internals.installmodule import FRONTEND_DIR, BACKEND_DIR, PATH_FRONTEND
from raspiot.libs.internals import __all__ as internals_libs
from raspiot.libs.externals import __all__ as externals_libs
from raspiot.libs.drivers import __all__ as drivers_libs
from raspiot.libs.configs import __all__ as configs_libs
from raspiot.libs.commands import __all__ as commands_libs
import raspiot.libs.internals.tools as Tools

__all__ = ['Developer']


class Developer(RaspIotModule):
    """
    Developer module: this module is dedicated only for developers.
    It allows implements and configures pyremotedev in raspiot ()

    Note:
        https://github.com/tangb/pyremotedev
    """
    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'1.0.0'
    MODULE_PRICE = 0
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Helps you to develop on Raspiot framework.'
    MODULE_LOCKED = False
    MODULE_TAGS = [u'developer', u'python', u'raspiot']
    MODULE_COUNTRY = None
    MODULE_URLINFO = u'https://github.com/tangb/Raspiot/wiki/Developer'
    MODULE_URLHELP = None
    MODULE_URLSITE = None
    MODULE_URLBUGS = None

    MODULE_CONFIG_FILE = u'developer.conf'

    PACKAGE_SCRIPTS = u'/opt/raspiot/scripts/'
    RASPIOT_PROFILE = u"""[raspiot]
raspiot/ = /usr/share/pyshared/raspiot/$_$/usr/lib/python2.7/dist-packages/raspiot/
bin/ = /usr/bin/$_$
log_file_path = /var/log/raspiot.log
html/ = /opt/raspiot/html/$_$"""
    RASPIOT_PROFILE_FILE = u'/root/.local/share/pyremotedev/slave.conf'

    FRONT_FILE_TYPE_DROP = u'Do not include file'
    FRONT_FILE_TYPE_SERVICE_JS = u'service-js'
    FRONT_FILE_TYPE_WIDGET_JS = u'widget-js'
    FRONT_FILE_TYPE_WIDGET_HTML = u'widget-html'
    FRONT_FILE_TYPE_WIDGET_CSS = u'widget-css'
    FRONT_FILE_TYPE_CONFIG_JS = u'config-js'
    FRONT_FILE_TYPE_CONFIG_HTML = u'config-html'
    FRONT_FILE_TYPE_CONFIG_CSS = u'config-css'
    FRONT_FILE_TYPE_RESOURCE = u'resource'

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #members
        self.__developer_uuid = None
        self.console = Console()
        self.pyremotedev_is_running = False
        self.status_task = None
        self.raspiot_path = os.path.dirname(inspect.getfile(RaspIotModule))
        self.__module_name = None
        self.__module_archive = None
        self.__module_version = None

        #events
        self.pyremotedevStartedEvent = self._get_event('developer.pyremotedev.started')
        self.pyremotedevStoppedEvent = self._get_event('developer.pyremotedev.stopped')

    def _configure(self):
        """
        Configure module
        """
        #add dummy device
        self.logger.debug('device_count=%d' % self._get_device_count())
        if self._get_device_count()==0:
            self.logger.debug(u'Add default devices')
            developer = {
                u'type': 'developer',
                u'name': 'Developer'
            }
            data = self._add_device(developer)

        #store device uuids for events
        devices = self.get_module_devices()
        self.logger.debug('devices: %s' % devices)
        for uuid in devices:
            if devices[uuid][u'type']==u'developer':
                self.__developer_uuid = uuid

        #write default pyremotedev profile
        if not os.path.exists(self.RASPIOT_PROFILE_FILE):
            #create dir tree
            if not self.cleep_filesystem.mkdirs(os.path.dirname(self.RASPIOT_PROFILE_FILE)):
                self.logger.error('Unable to create pyremote config dir tree. Unable to run developer module properly.')

            else:
                #create default profile file
                if not self.cleep_filesystem.write_data(self.RASPIOT_PROFILE_FILE, self.RASPIOT_PROFILE):
                    self.logger.error(u'Unable to write pyremotedev config. Unable to run developer module properly.')

        #start pyremotedev status task
        self.status_task = Task(10.0, self.status_pyremotedev, self.logger)
        self.status_task.start()

    def get_module_devices(self):
        """
        Return module devices
        """
        devices = super(Developer, self).get_module_devices()
        data = {
            u'running': self.pyremotedev_is_running
        }
        self.__developer_uuid = devices.keys()[0]
        devices[self.__developer_uuid].update(data)

        return devices

    def _stop(self):
        """
        Custom stop: stop pyremotedev thread
        """
        if self.status_task:
            self.status_task.stop()

    def restart_raspiot(self):
        """
        Restart raspiot
        """
        self.send_command(u'restart', u'system')

    def start_pyremotedev(self):
        """
        Start pyremotedev task
        """
        res = self.console.command(u'/bin/systemctl start pyremotedev', timeout=15.0)
        self.logger.debug('Pyremotedev console res: %s' % res)
        if not res[u'killed']:
            #no problem
            self.pyremotedev_is_running = True
            self.logger.info('Pyremotedev started')
            return True

        else:
            #unable to stop pyremotedev
            self.logger.error(u'Unable to start pyremotedev: %s' % u' '.join(res[u'stdout']).join(res[u'stderr']))
            self.pyremotedev_is_running = False
            return False

    def stop_pyremotedev(self):
        """
        Stop pyremotedev process
        """
        res = self.console.command(u'/bin/systemctl stop pyremotedev', timeout=15.0)
        self.logger.debug('Pyremotedev console res: %s' % res)
        if not res[u'killed']:
            #no problem
            self.pyremotedev_is_running = False
            self.logger.info('Pyremotedev stopped')
            return True

        else:
            #unable to stop pyremotedev
            self.logger.error(u'Unable to stop pyremotedev: %s' % u' '.join(res[u'stdout']).join(res[u'stderr']))
            self.pyremotedev_is_running = False
            return False

    def status_pyremotedev(self):
        """
        Get pyremotedev status
        """
        res = self.console.command(u'/bin/systemctl status pyremotedev')
        if not res[u'error'] and not res[u'killed']:
            output = u''.join(res[u'stdout'])
            if output.find(u'active (running)')>=0:
                #pyremotedev is running
                if not self.pyremotedev_is_running:
                    #send is running event
                    self.pyremotedevStartedEvent.send(to=u'rpc', device_id=self.__developer_uuid)
                self.pyremotedev_is_running = True

            else:
                #pyremotedev is not running
                if self.pyremotedev_is_running:
                    #send is not running event
                    self.pyremotedevStoppedEvent.send(to=u'rpc', device_id=self.__developer_uuid)
                self.pyremotedev_is_running = False

    def __analyze_module_python(self, module):
        """
        Analyze package python part

        Args:
            module (string): module name

        Return:
            dict: python package data::
                {
                    metadata (dict): module metadata,
                    files (list): list of python files (libs, module...)
                }
        """
        #init
        errors = []
        warnings = []

        #get module instance
        try:
            module_ = importlib.import_module(u'raspiot.modules.%s' % module)
            class_ = getattr(module_, module.capitalize())
        except:
            self.logger.exception(u'Unable to load module "%s". Please check your code' % module) 
            raise InvalidParameter(u'Unable to load module "%s". Please check your code' % module)

        #check module metadata
        #MODULE_DESCRIPTION
        if not hasattr(class_, u'MODULE_DESCRIPTION'):
            errors.append(u'Mandatory field MODULE_DESCRIPTION is missing')
        elif not isinstance(getattr(class_, u'MODULE_DESCRIPTION'), unicode):
            errors.append(u'Field MODULE_DESCRIPTION must be an unicode string')
        elif len(getattr(class_, u'MODULE_DESCRIPTION'))==0:
            errors.append(u'Field MODULE_DESCRIPTION must be provided')
        #MODULE_DEPS
        if not hasattr(class_, u'MODULE_DEPS'):
            errors.append(u'Mandatory field MODULE_DEPS is missing')
        elif hasattr(class_, u'MODULE_DEPS') and not isinstance(getattr(class_, u'MODULE_DEPS'), list):
            errors.append(u'Field MODULE_DEPS must be a list')
        #MODULE_VERSION
        version_pattern = re.compile('\d+\.\d+\.\d+')
        if not hasattr(class_, u'MODULE_VERSION'):
            errors.append(u'Mandatory field MODULE_VERSION is missing')
        elif not isinstance(getattr(class_, u'MODULE_VERSION'), unicode):
            errors.append(u'Field MODULE_VERSION must be an unicode string')
        elif len(getattr(class_, u'MODULE_VERSION'))==0:
            errors.append(u'Field MODULE_VERSION must be provided')
        elif version_pattern.match(getattr(class_, u'MODULE_VERSION')) is None:
            errors.append(u'Field MODULE_VERSION must match this format <number>.<number>.<number>')
        #MODULE_TAGS
        if not hasattr(class_, u'MODULE_TAGS'):
            errors.append(u'Mandatory field MODULE_TAGS is missing')
        elif not isinstance(getattr(class_, u'MODULE_TAGS'), list):
            errors.append(u'Field MODULE_TAGS must be a list')
        elif len(getattr(class_, u'MODULE_TAGS'))==0:
            warnings.append('Field MODULE_TAGS should contains strings to help finding your module')
        #MODULE_URLINFO
        if not hasattr(class_, u'MODULE_URLINFO'):
            errors.append(u'Mandatory field MODULE_URLINFO is missing')
        elif not isinstance(getattr(class_, u'MODULE_URLINFO'), unicode) and getattr(class_, u'MODULE_URLINFO') is not None:
            errors.append(u'Field MODULE_URLINFO must be an unicode string or None')
        elif getattr(class_, u'MODULE_URLINFO') is None or len(getattr(class_, u'MODULE_URLINFO'))==0:
            warnings.append('Field MODULE_URLINFO should be filled with url that describes your module')
        #MODULE_URLHELP
        if not hasattr(class_, u'MODULE_URLHELP'):
            errors.append(u'Mandatory field MODULE_URLHELP is missing')
        elif not isinstance(getattr(class_, u'MODULE_URLHELP'), unicode) and getattr(class_, u'MODULE_URLHELP') is not None:
            errors.append(u'Field MODULE_URLHELP must be an unicode string or None')
        elif getattr(class_, u'MODULE_URLHELP') is None or len(getattr(class_, u'MODULE_URLHELP'))==0:
            warnings.append('Field MODULE_URLHELP should be filled with url that gives access to your module support page')
        #MODULE_URLSITE
        if not hasattr(class_, u'MODULE_URLSITE'):
            errors.append(u'Mandatory field MODULE_URLSITE is missing')
        elif not isinstance(getattr(class_, u'MODULE_URLSITE'), unicode) and getattr(class_, u'MODULE_URLSITE') is not None:
            errors.append(u'Field MODULE_URLSITE must be an unicode string or None')
        elif getattr(class_, u'MODULE_URLSITE') is None or len(getattr(class_, u'MODULE_URLSITE'))==0:
            warnings.append('Field MODULE_URLSITE should be filled with module website url')
        #MODULE_URLBUGS
        if not hasattr(class_, u'MODULE_URLBUGS'):
            errors.append(u'Mandatory field MODULE_URLBUGS is missing')
        elif not isinstance(getattr(class_, u'MODULE_URLBUGS'), unicode) and getattr(class_, u'MODULE_URLBUGS') is not None:
            errors.append(u'Field MODULE_URLBUGS must be an unicode string or None')
        elif getattr(class_, u'MODULE_URLBUGS') is None or len(getattr(class_, u'MODULE_URLBUGS'))==0:
            warnings.append('Field MODULE_URLBUGS should be filled with module bugs tracking system url')
        #MODULE_COUNTRY
        if not hasattr(class_, u'MODULE_COUNTRY'):
            errors.append(u'Mandatory field MODULE_COUNTRY is missing')
        elif not isinstance(getattr(class_, u'MODULE_COUNTRY'), unicode) and getattr(class_, u'MODULE_COUNTRY') is not None:
            errors.append(u'Field MODULE_COUNTRY must be an unicode string or None')

        #build package metadata
        description = getattr(class_, u'MODULE_DESCRIPTION', u'')
        deps = getattr(class_, u'MODULE_DEPS', [])
        version = getattr(class_, u'MODULE_VERSION', u'')
        tags = getattr(class_, u'MODULE_TAGS', [])
        urls = {
            u'info': None,
            u'help': None,
            u'bugs': None,
            u'site': None
        }
        urls[u'info'] = getattr(class_, u'MODULE_URLINFO', u'')
        urls[u'help'] = getattr(class_, u'MODULE_URLHELP', u'')
        urls[u'site'] = getattr(class_, u'MODULE_URLSITE', u'')
        urls[u'bugs'] = getattr(class_, u'MODULE_URLBUGS', u'')
        country = getattr(class_, u'MODULE_COUNTRY', u'')
        price = getattr(class_, u'MODULE_PRICE', 0)
        author = getattr(class_, u'MODULE_AUTHOR', u'')
        metadata = {
            u'description': description,
            u'deps': deps,
            u'version': version,
            u'tags': tags,
            u'country': country,
            u'urls': urls,
            u'price': price,
            u'author': author
        }
        self.logger.debug('Module "%s" metadata: %s' % (module, metadata))

        #build main module file infos
        files = {
            u'module': None,
            u'libs': []
        }
        module_pyc = inspect.getfile(module_)
        module_py = module_pyc.replace(u'.pyc', u'.py')
        files['module'] = {
            u'fullpath': module_py,
            u'path': module_py.replace(os.path.join(self.raspiot_path, u'modules'), u'')[1:],
            u'filename': os.path.basename(module_py)
        }
        self.logger.debug('Module file infos: %s' % module_py)

        #build module dependencies infos
        finder = ModuleFinder()
        try:
            finder.run_script(module_py)
            for name, _ in finder.modules.iteritems():
                #self.logger.debug('lib name: %s' % name)
                if name.startswith(u'raspiot.'):
                    if name.find(u'.libs.')>0:
                        #add lib
                        lib = '%s.py' % os.path.join(self.raspiot_path, os.path.sep.join(name.split(u'.')[1:]))
                        if not os.path.exists(lib):
                            self.logger.debug('Lib %s not found' % lib)
                        else:
                            files[u'libs'].append({
                                u'fullpath': lib,
                                u'path': lib.replace(self.raspiot_path, u'')[1:],
                                u'filename': os.path.basename(lib),
                                u'selected': True,
                                u'systemlib': Tools.is_system_lib(lib)
                            })
        except:
            self.logger.exception('Exception occured during module dependencies finder:')

        return {
            u'data': {
                u'files': files,
                u'errors': errors,
                u'warnings': warnings
            },
            u'metadata': metadata,
        }

    def __fill_js_file_types(self, files, desc_json):
        """
        Fill file types as well as possible
        """
        #use desc.json content if possible
        if desc_json:
            #set service-js
            if u'system' in desc_json and u'services' in desc_json[u'system']:
                for key in desc_json[u'system'][u'services']:
                    if key in files:
                        files[key][u'type'] = self.FRONT_FILE_TYPE_SERVICE_JS

            #set widget-js
            if u'system' in desc_json and u'widgets' in desc_json[u'system'] and u'js' in desc_json[u'system'][u'widgets']:
                for key in desc_json[u'system'][u'widgets'][u'js']:
                    if key in files:
                        files[key][u'type'] = self.FRONT_FILE_TYPE_WIDGET_JS

            #set widget-js
            if u'system' in desc_json and u'widgets' in desc_json[u'system'] and u'html' in desc_json[u'system'][u'widgets']:
                for key in desc_json[u'system'][u'widgets'][u'html']:
                    if key in files:
                        files[key][u'type'] = self.FRONT_FILE_TYPE_WIDGET_HTML

            #set widget-js
            if u'system' in desc_json and u'widgets' in desc_json[u'system'] and u'css' in desc_json[u'system'][u'widgets']:
                for key in desc_json[u'system'][u'widgets'][u'css']:
                    if key in files:
                        files[key][u'type'] = self.FRONT_FILE_TYPE_WIDGET_CSS

            #set config-js
            if u'config' in desc_json and u'js' in desc_json[u'config']:
                for key in desc_json[u'config'][u'js']:
                    if key in files:
                        files[key][u'type'] =self.FRONT_FILE_TYPE_CONFIG_JS

            #set config-html
            if u'config' in desc_json and u'html' in desc_json[u'config']:
                for key in desc_json[u'config'][u'html']:
                    if key in files:
                        files[key][u'type'] = self.FRONT_FILE_TYPE_CONFIG_HTML

            #set config-css
            if u'config' in desc_json and u'css' in desc_json[u'config']:
                for key in desc_json[u'config'][u'css']:
                    if key in files:
                        files[key][u'type'] = self.FRONT_FILE_TYPE_CONFIG_CSS

            if u'res' in desc_json:
                for key in desc_json[u'res']:
                    if key in files:
                        files[key][u'type'] = self.FRONT_FILE_TYPE_RESOURCE

        else:
            #no desc.json file, try to guess empty types
            for key in files:
                if key==u'icon':
                    #icon field, drop
                    continue
                if files[key][u'type']!=self.FRONT_FILE_TYPE_DROP:
                    #drop already found type
                    continue

                #try to identify file type
                if key.find(u'.service.js')>0:
                    files[key][u'type'] = self.FRONT_FILE_TYPE_SERVICE_JS
                elif key.find(u'.directive.js')>0:
                    files[key][u'type'] = self.FRONT_FILE_TYPE_CONFIG_JS
                elif key.find(u'.directive.html')>0:
                    files[key][u'type'] = self.FRONT_FILE_TYPE_CONFIG_HTML
                elif key.find(u'.directive.css')>0:
                    files[key][u'type'] = self.FRONT_FILE_TYPE_CONFIG_CSS
                elif key.find(u'.widget.js')>0:
                    files[key][u'type'] = self.FRONT_FILE_TYPE_WIDGET_JS
                elif key.find(u'.widget.html')>0:
                    files[key][u'type'] = self.FRONT_FILE_TYPE_WIDGET_HTML
                elif key.find(u'.widget.css')>0:
                    files[key][u'type'] = self.FRONT_FILE_TYPE_WIDGET_CSS
                elif files[key][u'ext'] in (u'png', u'jpg', u'jpeg', u'gif'):
                    files[key][u'type'] = self.FRONT_FILE_TYPE_RESOURCE
                elif key==u'desc.json':
                    files[key][u'type'] = self.FRONT_FILE_TYPE_RESOURCE

        return files

    def __check_mdimgsrc_directive(self, js_files):
        """
        Check if developer uses md-img-src directive to display its images

        Args:
            js_files (dict): dict of js files
          
        Returns:
            list: list of warnings
        """
        #init
        images = []
        htmls = []
        cacheds = []
        warnings = []

        #get images
        for js_file in js_files:
            ext = js_files[js_file][u'ext'].lower()
            if ext in (u'jpg', u'jpeg', u'png', u'gif'):
                images.append(js_files[js_file])
            if ext in (u'html'):
                htmls.append(js_files[js_file])

        #no image, no need to go further
        if len(images)==0:
            return warnings

        #cache html files content
        for html in htmls:
            fd = self.cleep_filesystem.open(html[u'fullpath'], u'r')
            cacheds.append(u'\n'.join(fd.readlines()))
            self.cleep_filesystem.close(fd)

        #check directive usage for found images
        for image in images:
            pattern = r"mod-img-src\s*=\s*[\"']\s*%s\s*[\"']" % image[u'filename']
            found = False
            for cached in cacheds:
                matches = re.finditer(pattern, cached, re.MULTILINE)
                if len(list(matches))>0:
                    found = True
            if not found:
                warnings.append(u'Image "%s" may not be displayed properly because mod-img-src directive wasn\'t used' % image[u'filename'])

        return warnings

    def __analyze_module_js(self, module):
        """
       Analyze module js part

        Args:
            module (string): module name

        Return:
            tuple (dict, string): js data adn changelog
        """
        errors = []
        warnings = []

        #file types
        file_types = [self.FRONT_FILE_TYPE_DROP, self.FRONT_FILE_TYPE_SERVICE_JS, self.FRONT_FILE_TYPE_WIDGET_JS, self.FRONT_FILE_TYPE_WIDGET_HTML, self.FRONT_FILE_TYPE_WIDGET_CSS, self.FRONT_FILE_TYPE_CONFIG_JS, self.FRONT_FILE_TYPE_CONFIG_HTML, self.FRONT_FILE_TYPE_CONFIG_CSS, self.FRONT_FILE_TYPE_RESOURCE]

        #iterate over files in supposed js module directory
        all_files = {}
        module_path = os.path.join(PATH_FRONTEND, u'js/modules/', module)
        if not os.path.exists(module_path):
            raise CommandError(u'Module "%s" has no javascript' % module_path)
        for f in os.listdir(module_path):
            #drop some files
            if f.startswith(u'.') or f.startswith(u'~') or f.endswith(u'.tmp'):
                continue

            #get file values
            fullpath = os.path.join(module_path, f)
            filepath = fullpath.replace(module_path + os.path.sep, '')
            filename = os.path.basename(fullpath)

            #mandatory field
            mandatory = False
            type_ = self.FRONT_FILE_TYPE_DROP
            if filename==u'desc.json':
                mandatory = True
                type_ = self.FRONT_FILE_TYPE_RESOURCE

            #append file infos
            all_files[filepath] = {
                u'fullpath': fullpath,
                u'path': filepath,
                u'filename': filename,
                u'ext': os.path.splitext(fullpath)[1].replace(u'.', u''),
                u'mandatory': mandatory,
                u'type': type_
            }
        self.logger.debug('all_files: %s' % all_files)

        #load existing description file
        desc_json = u''
        desc_json_path = os.path.join(PATH_FRONTEND, u'js/modules/', module, u'desc.json')
        self.logger.debug('desc.json path: %s' % desc_json_path)
        if os.path.exists(desc_json_path):
            desc_json = self.cleep_filesystem.read_json(desc_json_path)

        #fill file types if possible
        all_files = self.__fill_js_file_types(all_files, desc_json)
        
        #fill changelog
        changelog = u''
        if desc_json and u'changelog' in desc_json:
            changelog = desc_json[u'changelog']

        #set icon
        icon = u'bookmark'
        if desc_json and u'icon' in desc_json:
            icon = desc_json[u'icon']

        #check usage of mod-img-src directive in front source code
        warnings = self.__check_mdimgsrc_directive(all_files)

        return {
            u'data': {
                u'files': all_files.values(),
                u'filetypes': file_types,
                u'errors': errors,
                u'warnings': warnings
            },
            u'icon': icon,
            u'changelog': changelog
        }

    def analyze_module(self, module):
        """
        Analyze specified module package and return archive name and filename to download it

        Args:
            module (string): module name

        Return:
            dict: archive infos::
                {
                    url (string): archive url,
                    name (string): archive name (usually name of module)
                }
        """
        #check parameters
        if module is None or len(module)==0:
            raise MissingParameter(u'Parameter "module" is missing')
        module_path = os.path.join(self.raspiot_path, u'modules', '%s.py' % module)
        if not os.path.exists(module_path):
            raise InvalidParameter(u'Module "%s" does not exist' % module)

        #analyze python part
        analyze_python = self.__analyze_module_python(module)

        #analyze front part
        analyze_js = self.__analyze_module_js(module)

        #check scripts existence
        script_preinst = os.path.join(self.PACKAGE_SCRIPTS, module, u'preinst.sh')
        script_postinst = os.path.join(self.PACKAGE_SCRIPTS, module, u'postinst.sh')
        script_preuninst = os.path.join(self.PACKAGE_SCRIPTS, module, u'preuninst.sh')
        script_postuninst = os.path.join(self.PACKAGE_SCRIPTS, module, u'postuninst.sh')

        return {
            u'python': analyze_python[u'data'],
            u'js': analyze_js[u'data'],
            u'scripts': {
                u'preinst': os.path.exists(script_preinst),
                u'postinst': os.path.exists(script_postinst),
                u'preuninst': os.path.exists(script_preuninst),
                u'posuntinst': os.path.exists(script_postuninst)
            },
            u'changelog': analyze_js[u'changelog'],
            u'icon': analyze_js[u'icon'],
            u'metadata': analyze_python[u'metadata']
        }

    def generate_desc_json(self, js_files, icon):
        """
        Generate desc.json file inside module directory

        Args:
            js_files (dict): js.files part of data returned by analyze_module command
            icon (string): module icon string

        Return:
            bool: True if file generated successfully
        """
        content = {
            u'icon': icon,
            u'system': {
                u'services': [],
                u'widgets': {
                    u'js': [],
                    u'html': [],
                    u'css': []
                }
            },
            u'config': {
                u'js': [],
                u'html': [],
                u'css': []
            },
            u'res': []
        }
        
        #iterates over files
        for f in js_files:
            if f[u'type']==self.FRONT_FILE_TYPE_SERVICE_JS:
                content[u'system'][u'services'].append(f[u'path'])
            elif f[u'type']==self.FRONT_FILE_TYPE_WIDGET_JS:
                content[u'system'][u'widgets'][u'js'].append(f[u'path'])
            elif f[u'type']==self.FRONT_FILE_TYPE_WIDGET_HTML:
                content[u'system'][u'widgets'][u'html'].append(f[u'path'])
            elif f[u'type']==self.FRONT_FILE_TYPE_WIDGET_CSS:
                content[u'system'][u'widgets'][u'css'].append(f[u'path'])
            elif f[u'type']==self.FRONT_FILE_TYPE_CONFIG_JS:
                content[u'config'][u'js'].append(f[u'path'])
            elif f[u'type']==self.FRONT_FILE_TYPE_CONFIG_HTML:
                content[u'config'][u'html'].append(f[u'path'])
            elif f[u'type']==self.FRONT_FILE_TYPE_CONFIG_CSS:
                content[u'config'][u'css'].append(f[u'path'])
            elif f[u'type']==self.FRONT_FILE_TYPE_RESOURCE:
                content[u'res'].append(f[u'path'])
        self.logger.debug(u'Generated desc.json content: %s' % content)

        #write json file to js module directory
        if len(js_files)>0:
            js_path = os.path.join(js_files[0][u'fullpath'].replace(js_files[0][u'path'], u''), u'desc.json')
            self.logger.debug(u'js_path=%s' % js_path)
            return self.cleep_filesystem.write_json(js_path, content)
            
        else:
            self.logger.warning(u'Nothing to write to desc.json file')
            return False

    def build_package(self, module, data):
        """
        Build module package archive in zip format.
        Archive is not protected by password

        Args:
            data (dict): data returned by analyze_module command

        Return:
            string: url of archive to download or None if error occured
        """
        #init
        self.__module_archive = None
        self.__module_name = None
        self.__module_version = None

        #build desc.json
        if not self.generate_desc_json(data[u'js'][u'files'], data[u'icon']):
            raise CommandError(u'Unable to generate desc.json file. Please check logs and sent data')

        #build module description file (module.json)
        fd = NamedTemporaryFile(delete=False)
        module_json = fd.name
        metadata = copy.deepcopy(data[u'metadata'])
        metadata[u'icon'] = data[u'icon']
        metadata[u'changelog'] = data[u'changelog']
        fd.write(json.dumps(metadata))
        fd.close()

        #build zip archive
        fd = NamedTemporaryFile(delete=False)
        module_archive = fd.name
        self.logger.debug('Archive filepath: %s' % module_archive)
        archive = ZipFile(fd, u'w', ZIP_DEFLATED)
        #add js files
        for f in data[u'js'][u'files']:
            if f[u'type']!=self.FRONT_FILE_TYPE_DROP:
                archive.write(f[u'fullpath'], os.path.join(FRONTEND_DIR, u'js', u'modules', module, f['path']))
        #add python files
        for f in data[u'python'][u'files'][u'libs']:
            if f[u'selected']:
                archive.write(f[u'fullpath'], os.path.join(BACKEND_DIR, f[u'path']))
        archive.write(data[u'python'][u'files'][u'module'][u'fullpath'], os.path.join(BACKEND_DIR, u'modules', data[u'python'][u'files'][u'module'][u'path']))
        #add module.json
        archive.write(module_json, u'module.json')
        #add pre and post scripts
        script_preinst = os.path.join(self.PACKAGE_SCRIPTS, module, u'preinst.sh')
        script_postinst = os.path.join(self.PACKAGE_SCRIPTS, module, u'postinst.sh')
        script_preuninst = os.path.join(self.PACKAGE_SCRIPTS, module, u'preuninst.sh')
        script_postuninst = os.path.join(self.PACKAGE_SCRIPTS, module, u'postuninst.sh')
        if os.path.exists(script_preinst):
            archive.write(script_preinst, u'preinst.sh')
        if os.path.exists(script_postinst):
            archive.write(script_postinst, u'postinst.sh')
        if os.path.exists(script_preuninst):
            archive.write(script_preuninst, u'preuninst.sh')
        if os.path.exists(script_postuninst):
            archive.write(script_postuninst, u'postuninst.sh')
        #close archive
        archive.close()

        #clean some stuff
        if os.path.exists(module_json):
            os.remove(module_json)

        #save now related package infos to make sure everything is completed successfully
        self.__module_archive = module_archive
        self.__module_name = module
        self.__module_version = data[u'metadata'][u'version']

        return True

    def download_package(self):
        """
        Download latest generated package

        Return:
            dict: archive infos::
                {
                    data: filepath
                    filename: new filename
                }
        """
        self.logger.debug(u'Download_package')
        if self.__module_name is None or self.__module_archive is None or self.__module_version is None:
            raise CommandError(u'No module package generated')

        return {
            u'filepath': self.__module_archive,
            u'filename': u'raspiot_%s_%s.zip' % (self.__module_name, self.__module_version)
        }

