#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import time
from raspiot.utils import InvalidParameter
import unittest
from threading import Timer, Thread
import os
import signal
import logging

class InfiniteConsole(Thread):
    """
    Helper class to execute long command line (system update...)
    This kind of console doesn't kill command line after timeout. It just let command line running
    until end of it or if user explicitely requests to kill (or stop) it.
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
            raise InvalidParameter('Timeout is mandatory and must be greater than 0')

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
            'error': False,
            'killed': killed,
            'stdout': [],
            'stderr': []
        }
        if not killed:
            err = self.__remove_eol(p.stderr.readlines())
            if len(err)>0:
                result['error'] = True
                result['stderr'] = err
            else:
                result['stdout'] = self.__remove_eol(p.stdout.readlines())

        #make sure process is really killed
        try:
            subprocess.Popen('/bin/kill -9 %s' % pid, shell=True)
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




class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.c = Console()

    def test_invalid_none_timeout(self):
        self.assertRaises(InvalidParameter, self.c.command, 'ls -lh', None)

    def test_invalid_timeout(self):
        self.assertRaises(InvalidParameter, self.c.command, 'ls -lh', 0.0)

    def test_successful_command(self):
        res = self.c.command('ls -lh')
        self.assertFalse(res['error'])
        self.assertFalse(res['killed'])
        self.assertIsNot(len(res['stdout']), 0)
    
    def test_timeout_command(self):
        res = self.c.command('sleep 4')
        self.assertTrue(res['killed'])
        self.assertFalse(res['error'])
        self.assertIs(len(res['stdout']), 0)

    def test_change_timeout_command(self):
        res = self.c.command('sleep 4', 5.0)
        self.assertFalse(res['killed'])
        self.assertFalse(res['error'])
        self.assertIs(len(res['stdout']), 0)

    def test_failed_command(self):
        res = self.c.command('ls -123456')
        self.assertFalse(res['killed'])
        self.assertTrue(res['error'])
        self.assertIsNot(len(res['stderr']), 0)

    def test_command_lsmod(self):
        res = self.c.command('lsmod | grep snd_bcm2835 | wc -l')
        self.assertFalse(res['killed'])
        self.assertFalse(res['error'])
        self.assertIs(res['stdout'][0], '3')

    def test_command_uptime(self):
        res = self.c.command('uptime')
        self.assertFalse(res['killed'])
        self.assertFalse(res['error'])
        self.assertIs(len(res['stdout']), 1)

    def test_complex_command(self):
        res = self.c.command('cat /proc/partitions | awk -F " " \'$2==0 { print $4}\'')
        self.assertIsNot(len(res), 0)


