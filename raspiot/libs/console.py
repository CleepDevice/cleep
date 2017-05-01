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

class NoEndCommand(Thread):
    def __init__(self, command, callback, logger):
        """
        Constructor
        @param command: command to execute
        @param callback: callback when message is received
        @param logger: logger
        """
        Thread.__init__(self)
        Thread.daemon = True

        #members
        self.logger = logger
        self.running = True

    def __del__(self):
        self.stop()

    def __log(self, message, level):
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

    def run(self):
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
        @param lines: list of lines
        @result: list of lines with eol removed
        """
        for i in range(len(lines)):
            lines[i] = lines[i].rstrip()
        return lines

    def command(self, command, timeout=2.0):
        """
        Execute specified command line with auto kill after timeout
        @param command: command to execute
        @param timeout: wait timeout before killing process and return command result
        @return result of command (dict('error':<bool>, 'killed':<bool>, 'output':<list<string>>))
                if error occured output will contain stderr, if command is successful output will contain stdout.
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
        @param command: command to execute (string)
        @param delay: time to wait before executing command (milliseconds)
        @param timeout: timeout before killing command
        @see command function to have more details
        @return True if command delayed succesfully or False otherwise
        """
        timer = Timer(delay, self.command, [command])
        timer.start()

    def command_noend(self, command, timeout=None):
        """
        Execute specified command.
        The main goal of this function is to execute command that requires some time to end (ie download file using wget, system update...)
        This function returns as soon as command is launched and send event when something is read on console stdout/stderr
        A timeout can be set to secure command execution (the command is killed after timeout)
        @param command : command to execute
        @param timeout: if specified kill command after timeout
        @return True if command is launched successfully, False otherwise
        """
        pass




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


