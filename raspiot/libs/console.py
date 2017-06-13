#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import time
from raspiot.utils import InvalidParameter
from threading import Timer, Thread
import os
import signal
import logging

class EndlessConsole(Thread):
    """
    Helper class to execute long command line (system update...)
    This kind of console doesn't kill command line after timeout. It just let command line running
    until end of it or if user explicitely requests to stop (or kill) it.
    """

    def __init__(self, command, callback, logger):
        """
        Constructor

        Args:
            command (string): command to execute
            callback (function): callback when message is received
            logger (Logger): logger
        """
        Thread.__init__(self)
        Thread.daemon = True

        #members
        self.logger = logger
        self.running = True

    def __del__(self):
        """
        Destructor
        """
        self.stop()

    def __log(self, message, level):
        """
        Log facility

        Args:
            message (string): message to log
            level (int): log level
        """
        if self.logger:
            if level==logging.DEBUG:
                self.logger.debug(message)
            if level==logging.INFO:
                self.logger.info(message)
            if level==logging.WARN:
                self.logger.warn(message)
            if level==logging.ERROR:
                self.logger.error(message)

    def stop(self):
        """
        Stop command line execution (kill it)
        """
        self.running = False

    def kill(self):
        """
        Stop command line execution
        """
        self.running = False

    def run(self):
        """
        Console process
        """
        #launch command
        p = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        pid = p.pid

        #wait for end of command line
        while not done:
            #check if command has finished
            p.poll()

            #read outputs and launch callbacks
            if self.callback:
                (stdout, stderr) = p.communicate()
                if len(stdout)>0 or len(stderr)>0:
                    self.callback(stdout, stderr)

            #check end of command
            if p.returncode is not None:
                break
            
            #kill on demand
            if not self.running:
                p.kill()
                break

            #pause
            time.sleep(0.125)

        #make sure process is killed
        os.kill(pid, signal.SIGKILL)


class Console():
    """
    Helper class to execute command lines
    """

    def __remove_eol(self, lines):
        """
        Remove end of line char for given lines
        
        Args:
            lines (list): list of lines
        
        Results:
            list: input list of lines with eol removed
        """
        for i in range(len(lines)):
            lines[i] = lines[i].rstrip()
        return lines

    def command(self, command, timeout=2.0):
        """
        Execute specified command line with auto kill after timeout
        
        Args:
            command (string): command to execute
            timeout (float): wait timeout before killing process and return command result

        Returns:
            dict: result of command::
                {
                    'error': True if error occured,
                    'killed': True if command was killed,
                    'stdout': command line output (list(string))
                    'stderr': command line error (list(string))
                }
        """
        #check params
        if timeout is None or timeout<=0.0:
            raise InvalidParameter(u'Timeout is mandatory and must be greater than 0')

        #launch command
        p = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        pid = p.pid

        #wait for end of command line
        done = False
        start = time.time()
        killed = False
        while not done:
            #check if command has finished
            p.poll()
            if p.returncode is not None:
                #command executed
                done = True
                break
            
            #check timeout
            if time.time()>(start + timeout):
                #timeout is over, kill command
                p.kill()
                killed = True
                break

            #pause
            time.sleep(0.125)
       
        #prepare result
        result = {
            u'error': False,
            u'killed': killed,
            u'stdout': [],
            u'stderr': []
        }
        if not killed:
            err = self.__remove_eol(p.stderr.readlines())
            if len(err)>0:
                result[u'error'] = True
                result[u'stderr'] = err
            else:
                result[u'stdout'] = self.__remove_eol(p.stdout.readlines())

        #make sure process is really killed
        try:
            subprocess.Popen(u'/bin/kill -9 %s' % pid, shell=True)
        except:
            pass

        return result

    def command_delayed(self, command, delay, timeout=2.0):
        """
        Execute specified command line after specified delay

        Args:
            command (string): command to execute
            delay (int): time to wait before executing command (milliseconds)
            timeout (float): timeout before killing command

        Note:
            Command function to have more details
        
        Returns:
            bool: True if command delayed succesfully or False otherwise
        """
        timer = Timer(delay, self.command, [command])
        timer.start()



