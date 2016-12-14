#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from bus import MessageRequest, MessageResponse, InvalidParameter
from raspiot import RaspIot
import time
from threading import Thread
from collections import deque
import time
from task import Task

__all__ = ['Action']

class Script(Thread):
    def __init__(self, script, bus_push, disabled, test=False):
        """
        Constructor
        @param script: full script path
        @param bus_push: bus push function
        @param test: set to True to execute this script once
        """
        #init
        Thread.__init__(self)
        self.logger = logging.getLogger(os.path.basename(script))

        #members
        self.__test = test
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
        @return timestamp
        """
        return self.last_execution

    def set_debug_level(self, level):
        """
        Set debug level
        @param level: use logging.<INFO|ERROR|WARN|DEBUG>
        """
        self.logger_level = level

    def set_disabled(self, disabled):
        """
        Disable/enable script
        """
        self.__disabled = disabled

    def is_disabled(self):
        """
        Return disabled status
        """
        return self.__disabled

    def push_event(self, event):
        """
        Event received
        """
        self.__events.appendleft(event)

    def __exec_script(self):
        """
        Execute script
        """

    def run(self):
        #configure logger
        self.logger.setLevel(self.logger_level)

        #push message helper
        def action(command, to, params=None):
            request = MessageRequest()
            request.command = command
            request.to = to
            request.params = params
            #push message and reduce timeout to 1 sec
            resp = self.__bus_push(request, timeout=1.0)
            if resp!=None and isinstance(resp, MessageResponse):
                return resp.to_dict()
            else:
                return resp

        #logger helper
        logger = self.logger

        if self.__test:
            #event in queue, get event
            event = self.__events.pop()
            self.logger.info('exec script')

            #and execute file
            try:
                execfile(self.script)
                self.last_execution = int(time.time())
            except:
                self.logger.exception('Fatal error in script "%s"' % self.script)
                self.__exec_script()
        else:
            #loop forever
            while self.__continu:
                if self.__disabled:
                    #script is disabled
                    time.sleep(1.0)

                elif len(self.__events)>0:
                    #event in queue, process it
                    event = self.__events.pop()
                    self.logger.info('exec script')
                    
                    #and execute file
                    try:
                        execfile(self.script)
                        self.last_execution = int(time.time())
                    except:
                        self.logger.exception('Fatal error in script "%s"' % self.script)

                else:
                    #no event, pause
                    time.sleep(0.25)


class Action(RaspIot):

    MODULE_CONFIG_FILE = 'action.conf'
    MODULE_DEPS = []

    SCRIPTS_PATH = '/var/opt/raspiot/scripts'
    DATA_FILE = 'raspiot.data.conf'
    DEFAULT_CONFIG = {
        'scripts': {}
    }

    def __init__(self, bus):
        #init
        RaspIot.__init__(self, bus)
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.logger.setLevel(logging.DEBUG)

        #check config
        self._check_config(Action.DEFAULT_CONFIG)

        #scripts threads
        self.__scripts = {}
        self.__load_scripts()

        #refresh scripts task
        self.__refresh_thread = Task(60.0, self.__load_scripts)
        self.__refresh_thread.start()

    def stop(self):
        #stop raspiot
        RaspIot.stop(self)

        #stop refresh thread
        self.__refresh_thread.stop()

        #stop all scripts
        for script in self.__scripts:
            self.__scripts[script].stop()

    def __load_scripts(self):
        """
        Launch dedicated thread for each found script
        """
        #remove stopped threads (script was removed?)
        for script in self.__scripts.keys():
            if not self.__scripts[script].is_alive():
                self.logger.debug('Thread for script "%s" is dead. Purge it' % script)
                del self.__scripts[script]
                config = self._get_config()
                if config['scripts'].has_key(script):
                    del config['scripts'][script]
                    self._save_config(config)

        #launch thread for new script
        for root, dirs, scripts in os.walk(Action.SCRIPTS_PATH):
            for script in scripts:
                if not self.__scripts.has_key(script):
                    self.logger.debug('Discover new script "%s"' % script)
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

    def event_received(self, event):
        """
        Event received
        """
        self.logger.debug('Event received %s' % str(event))
        #push event to all script threads
        for script in self.__scripts:
            self.__scripts[script].push_event(event)

    def get_scripts(self):
        """
        Return scripts
        @return array of scripts
        """
        scripts = []
        for script in self.__scripts:
            script = {
                'name': script,
                'last_execution': self.__scripts[script].get_last_execution(),
                'disabled': self.__scripts[script].is_disabled()
            }
            scripts.append(script)
        return scripts

    def disable_script(self, script, disabled):
        """
        Enable/disable specified script
        @param script: script name
        @param disable: bool
        """
        if not self.__scripts.has_key(script):
            raise InvalidParameter('Script not found')

        #enable/disable script
        config = self._get_config()
        config['scripts'][script]['disabled'] = disabled
        self._save_config(config)
        self.__scripts[script].set_disabled(disabled)

        return True

    def del_script(self, script):
        """
        Delete specified script
        """
        for root, dirs, scripts in os.walk(Action.SCRIPTS_PATH):
            for script_ in scripts:
                if script==script_:
                    #script found, remove from filesystem
                    os.remove(os.path.join(Action.SCRIPTS_PATH, script))
                    #no need to del config entry, it will be deleted automatically with __load_scripts
                    return True

        return False

    def add_script(self, filepath):
        """
        Add new script
        """
        #check parameters
        file_ext = os.path.splitext(filepath)
        if file_ext[1][1:]=='py':
            raise bus.InvalidParameter('Invalid script file uploaded (only python script are supported)')

        #move file to valid dir
        if os.path.exists(filepath):
            name = os.path.basename(filepath)
            path = os.path.join(Action.SCRIPTS_PATH, name)
            logger.debug('Name=%s path=%s' % (name, path))
            shutil.move(filepath, path)
            logger.info('File "%s" uploaded successfully' % name)
        else:
            #file doesn't exists
            logger.error('Script file "%s" doesn\'t exist' % filepath)
            raise Exception('Script file "%s"  doesn\'t exists' % filepath)

        return True 

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
