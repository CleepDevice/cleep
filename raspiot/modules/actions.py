#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.utils import MessageRequest, MessageResponse, InvalidParameter, NoResponse, CommandError, InvalidModule
from raspiot.raspiot import RaspIotModule
import time
from threading import Thread, Lock
from collections import deque
import time
from raspiot.libs.task import Task
import shutil
import re
import traceback

__all__ = ['Actions']

class ScriptDebugLogger():
    """
    Logger instance for script debugging
    """

    def __init__(self, bus_push):
        """
        Constructor
        
        Params:
            bus_push (function) callback to bus push function
        """
        self.__bus_push = bus_push

    def __add_message(self, message, level):
        """
        Emit debug message event.

        Params:
            message (string): message
            level (string): log level
        """
        #push message
        request = MessageRequest()
        request.event = 'actions.debug.message'
        request.params = {
            'message': message,
            'level': level.upper(),
            'timestamp': time.time()
        }

        #push message
        resp = None
        try:
            resp = self.__bus_push(request)
        except:
            pass

    def debug(self, message):
        """
        Info message

        Params:
            message (string): message
        """
        self.__add_message(message, 'DEBUG')

    def info(self, message):
        """
        Info message

        Params:
            message (string): message
        """
        self.__add_message(message, 'INFO')

    def warning(self, message):
        """
        Warning message

        Params:
            message (string): message
        """
        self.__add_message(message, 'WARNING')

    def warn(self, message):
        """
        Warning message

        Params:
            message (string): message
        """
        self.__add_message(message, 'WARNING')

    def error(self, message):
        """
        Error message

        Params:
            message (string): message
        """
        self.__add_message(message, 'ERROR')

    def fatal(self, message):
        """
        Critical message

        Params:
            message (string): message
        """
        self.__add_message(message, 'CRITICAL')

    def critical(self, message):
        """
        Critical message

        Params:
            message (string): message
        """
        self.__add_message(message, 'CRITICAL')

    def exception(self, message):
        """
        Handle exception message
        """
        lines = traceback.format_exc().split('\n')
        self.__add_message(message, 'EXCEPTION')
        for line in lines:
            if len(line.strip())>0:
                self.__add_message(line, 'EXCEPTION')




class Script(Thread):
    """
    Script class launches isolated thread for an action
    It handles 2 kinds of process:
     - if debug parameter is True, Script instance runs action once and allows you to get output traces
     - if debug parameter is False, Script instance runs undefinitely (until end of raspiot)
    """

    def __init__(self, script, bus_push, disabled, debug=False, debug_event=None):
        """
        Constructor

        Args:
            script (string): full script path
            bus_push (callback): bus push function
            disabled (bool): script disabled status
            debug (bool): set to True to execute this script once
            debug_event (MessageRequest): event that trigger script
        """
        #init
        Thread.__init__(self)
        self.logger = logging.getLogger(os.path.basename(script))

        #members
        self.__debug = debug
        if debug:
            self.__debug_logger = ScriptDebugLogger(bus_push)
        self.script = script
        self.__bus_push = bus_push
        self.__events = deque()
        self.__continu = True
        self.__disabled = disabled
        self.last_execution = None
        self.logger_level = logging.INFO

    def stop(self):
        """
        Stop script execution
        """
        self.__continu = False

    def get_last_execution(self):
        """
        Get last script execution

        Returns:
            int: timestamp
        """
        return self.last_execution

    def set_debug_level(self, level):
        """
        Set debug level

        Args:
            level (int): use logging.<INFO|ERROR|WARN|DEBUG>
        """
        self.logger_level = level

    def set_disabled(self, disabled):
        """
        Disable/enable script

        Args:
            disabled (bool): True to disable script exection
        """
        self.__disabled = disabled

    def is_disabled(self):
        """
        Return disabled status

        Returns:
            bool: True if script execution disabled
        """
        return self.__disabled

    def push_event(self, event):
        """
        Event received

        Args:
            event (MessageRequest): message instance
        """
        self.__events.appendleft(event)

    def __exec_script(self):
        """
        Execute script
        """
        pass

    def run(self):
        """
        Script execution process
        """
        #configure logger
        self.logger.setLevel(self.logger_level)
        self.logger.debug('Thread started')

        #send command helper
        def command(command, to, params=None):
            request = MessageRequest()
            request.command = command
            request.to = to
            request.params = params

            #push message
            resp = MessageResponse()
            try:
                resp = self.__bus_push(request)
            except InvalidModule:
                raise Exception('Module "%" does not exit (loaded?)' % to)
            except NoResponse:
                #handle long response
                raise Exception('No response from "%s" module' % to)

            if resp!=None and isinstance(resp, MessageResponse):
                return resp.to_dict()
            else:
                return resp

        if self.__debug:
            #event in queue, get event
            self.logger.debug('Script execution')

            #special logger for debug to store trace
            logger = self.__debug_logger

            #and execute file
            try:
                execfile(self.script)
            except:
                logger.exception('Fatal error in script "%s"' % self.script)

            #send end event
            request = MessageRequest()
            request.event = 'actions.debug.end'
            resp = self.__bus_push(request)

        else:
            #logger helper
            logger = self.logger

            #loop forever
            while self.__continu:
                if len(self.__events)>0:
                    #check if file exists
                    if not os.path.exists(self.script):
                        self.logger.error('Script does not exist. Stop thread')
                        break

                    #event in queue, process it
                    current_event = self.__events.pop()

                    #drop script execution if script disabled
                    if self.__disabled:
                        #script is disabled
                        self.logger.debug('Script is disabled. Drop execution')
                        continue

                    #event helpers
                    event = current_event['event']
                    event_values = current_event['params']
                    
                    #and execute file
                    self.logger.debug('Script execution')
                    try:
                        execfile(self.script)
                        self.last_execution = int(time.time())
                    except:
                        self.logger.exception('Fatal error in script "%s"' % self.script)

                else:
                    #no event, pause
                    time.sleep(0.25)

        self.logger.debug('Thread is stopped')



        
class Actions(RaspIotModule):
    """
    Action allows user to execute its own python scripts interacting with RaspIot
    """

    MODULE_CONFIG_FILE = 'actions.conf'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = 'Helps you trigger custom action to fit your needs'
    MODULE_LOCKED = False
    MODULE_URL = None
    MODULE_TAGS = []

    SCRIPTS_PATH = '/var/opt/raspiot/scripts'
    DATA_FILE = 'raspiot.data.conf'
    DEFAULT_CONFIG = {
        'scripts': {}
    }

    def __init__(self, bus, debug_enabled):
        """
        Constructor

        Args:
            bus (MessageBus): MessageBus instance
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotModule.__init__(self, bus, debug_enabled)

        #make sure sounds path exists
        if not os.path.exists(Actions.SCRIPTS_PATH):
            os.makedirs(Actions.SCRIPTS_PATH)

        #init members
        self.__scripts = {}
        self.__load_scripts_lock = Lock()

    def _start(self):
        """
        Start module
        """
        #launch scripts threads
        self.__load_scripts()

        #refresh scripts task
        self.__refresh_thread = Task(60.0, self.__load_scripts)
        self.__refresh_thread.start()

    def _stop(self):
        """
        Stop module
        """
        #stop refresh thread
        self.__refresh_thread.stop()

        #stop all scripts
        for script in self.__scripts:
            self.__scripts[script].stop()

    def __load_scripts(self):
        """
        Launch dedicated thread for each script found
        """
        self.__load_scripts_lock.acquire()

        #remove stopped threads (script was removed?)
        for script in self.__scripts.keys():
            #check file existance
            if not os.path.exists(os.path.join(Actions.SCRIPTS_PATH, script)):
                #file doesn't exist from filesystem, clear config entry
                self.logger.info('Delete infos from removed script "%s"' % script)

                if self.__scripts.has_key(script):
                    #stop running thread if necessary
                    if self.__scripts[script].is_alive():
                        self.__scripts[script].stop()

                    #clear config entry
                    del self.__scripts[script]
                    config = self._get_config()
                    if config['scripts'].has_key(script):
                        del config['scripts'][script]
                        self._save_config(config)
                    
        #launch thread for new script
        for root, dirs, scripts in os.walk(Actions.SCRIPTS_PATH):
            for script in scripts:
                #drop files that aren't python script
                ext = os.path.splitext(script)[1]
                if ext!='.py':
                    self.logger.debug('Drop bad extension file "%s"' % script)
                    continue

                if not self.__scripts.has_key(script):
                    self.logger.info('Discover new script "%s"' % script)
                    #get disable status
                    disabled = False
                    if self._config['scripts'].has_key(script):
                        disabled = self._config['scripts'][script]['disabled']
                    else:
                        config = self._get_config()
                        config['scripts'][script] = {
                            'disabled': disabled
                        }
                        self._save_config(config)

                    #start new thread
                    self.__scripts[script] = Script(os.path.join(root, script), self.push, disabled)
                    self.__scripts[script].start()

        self.__load_scripts_lock.release()

    def get_module_config(self):
        """
        Return full module configuration

        Returns:
            dict: module configuration
        """
        config = {}
        config['scripts'] = self.get_scripts()
        return config

    def event_received(self, event):
        """
        Event received

        Args:
            event (MessageRequest): an event
        """
        self.logger.debug('Event received %s' % str(event))
        #push event to all script threads
        for script in self.__scripts:
            self.__scripts[script].push_event(event)

    def get_script(self, script):
        """
        Return a script

        Params:
            script (string): script name

        Returns:
            dict: script data::
                {
                    visual (string): visual editor used to edit file or None if no editor used
                    code (string): source code
                    header (string): source file header (can contains necessary infos for visual editor)
                }

        Raises:
            InvalidParameter: if script not found
            CommandError: if error occured processing script
        """
        if not self.__scripts.has_key(script):
            raise InvalidParameter('Unknown script "%s"' % script)
        path = os.path.join(Actions.SCRIPTS_PATH, script)
        if not os.path.exists(path):
            raise InvalidParameter('Script "%s" does not exist' % script)

        output = {
            'visual': None,
            'code': None,
            'header': None
        }

        #read file content
        self.logger.debug('Loading script: %s' % path)
        fd = open(path)
        content = fd.read()
        fd.close()

        #parse file
        groups = re.findall('^(?:\"\"\"(.*)\"\"\"\s)?(.*)$', content, re.S)
        if len(groups)==1:
            #seems good
            try:
                output['header'] = groups[0][0].strip()
                output['code'] = groups[0][1].strip()
                groups = re.findall('^editor:(.*?)?\s(.*)$', output['header'])
                output['visual'] = None
                if groups and len(groups)==1:
                    output['visual'] = groups[0][0]
                    output['header'] = groups[0][1]
            except Exception as e:
                self.logger.exception('Exception when loading script %s:' % path)
                raise CommandError('Unable to load script')
        else:
            self.logger.warning('Unhandled source code: %s' % groups)

        return output

    def save_script(self, script, editor, header, code):
        """
        Save script content. If script name if not found, it will create new script

        Params:
            script (string): script name
            editor (string): editor name
            header (string): script header (header comments, may contains editor specific stuff)
            code (string): source code

        Returns:
            bool: True if script saved successfully

        Raises:
            MissingParameter: if parameter is missing
            CommandError: if error processing script
        """
        if not script or len(script)==0:
            raise InvalidParameter('Script parameter is missing')
        if not editor or len(editor)==0:
            raise InvalidParameter('editor parameter is missing')
        if not header or len(header)==0:
            raise InvalidParameter('Header parameter is missing')
        if not code or len(code)==0:
            raise InvalidParameter('Code parameter is missing')

        #open script for writing
        path = os.path.join(Actions.SCRIPTS_PATH, script)
        self.logger.debug('Opening script: %s' % path)
        fd = open(path, 'w')
        
        #write content
        content = '"""\neditor:%s\n%s\n"""\n%s' % (editor, header, code)
        fd.write(content)
        fd.close()

    def get_scripts(self):
        """
        Return scripts
        
        Returns:
            list: list of scripts::
                [
                    {
                        name (string): script name
                        lastexecution (timestamp): last execution time
                        disabled (bool): True if script is disabled
                    },
                    ...
                ]
        """
        scripts = []
        for script in self.__scripts:
            script = {
                'name': script,
                'lastexecution': self.__scripts[script].get_last_execution(),
                'disabled': self.__scripts[script].is_disabled()
            }
            scripts.append(script)

        return scripts

    def disable_script(self, script, disabled):
        """
        Enable/disable specified script
        
        Args:
            script (string): script name
            disable (bool): disable flag

        Raises:
            InvalidParameter: if parameter is invalid
        """
        if not self.__scripts.has_key(script):
            raise InvalidParameter('Script not found')

        #enable/disable script
        config = self._get_config()
        config['scripts'][script]['disabled'] = disabled
        self._save_config(config)
        self.__scripts[script].set_disabled(disabled)

    def delete_script(self, script):
        """
        Delete specified script

        Args:
            script (string): script name
        """
        for root, dirs, scripts in os.walk(Actions.SCRIPTS_PATH):
            for script_ in scripts:
                if script==script_:
                    #script found, remove from filesystem
                    os.remove(os.path.join(Actions.SCRIPTS_PATH, script))
                    #force script loading
                    self.__load_scripts()
                    return True

        return False

    def add_script(self, filepath):
        """
        Add new script using rpc upload

        Args:
            filepath (string): script full path

        Raises:
            InvalidParameter: if invalid parameter is specified
            Exception: if error occured
        """
        #check parameters
        file_ext = os.path.splitext(filepath)
        self.logger.info('uploaded file extension: %s - %s' % (str(file_ext), str(file_ext[1])))
        if file_ext[1]!='.py':
            self.logger.info('uploaded file extension: %s' % str(file_ext[1][1:]))
            raise InvalidParameter('Invalid script file uploaded (only python script are supported)')

        #move file to valid dir
        if os.path.exists(filepath):
            name = os.path.basename(filepath)
            path = os.path.join(Actions.SCRIPTS_PATH, name)
            self.logger.info('Name=%s path=%s' % (name, path))
            shutil.move(filepath, path)
            self.logger.info('File "%s" uploaded successfully' % name)
            #reload scripts
            self.__load_scripts()
        else:
            #file doesn't exists
            self.logger.error('Script file "%s" doesn\'t exist' % filepath)
            raise Exception('Script file "%s"  doesn\'t exists' % filepath)

    def download_script(self, script):
        """
        Download specified script

        Args:
            script (string): script name to download

        Returns:
            string: script full path

        Raises:
            Exception: if error occured
        """
        filepath = os.path.join(Actions.SCRIPTS_PATH, script)
        if os.path.exists(filepath):
            #script is valid, return full filepath
            return filepath
        else:
            #script doesn't exist, raise exception
            raise Exception('Script "%s" doesn\'t exist' % script)

    def debug_script(self, script, event_name=None, event_values=None):
        """
        Launch script debugging. Script output will be send to message bus as event

        Params:
            script (string): script name
            event_name (string): event name
            event_values (dict): event values

        Raises:
            InvalidParameter
        """
        if not self.__scripts.has_key(script):
            raise InvalidParameter('Unknown script "%s"' % script)
        path = os.path.join(Actions.SCRIPTS_PATH, script)
        if not os.path.exists(path):
            raise InvalidParameter('Script "%s" does not exist' % script)
        
        #TODO handle event
        debug = Script(os.path.join(Actions.SCRIPTS_PATH, script), self.push, False, True)
        debug.start()

