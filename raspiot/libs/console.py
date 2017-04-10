#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import time
import unittest

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

    def execute(self, command, timeout=2.0):
        """
        Execute specified command line
        @param command: command to execute
        @param timeout: wait timeout before killing process and return command result
        @return result of command (dict('error':<bool>, 'killed':<bool>, 'output':<list<string>>))
                if error occured output will contain stderr, if command is successful output will contain stdout.
        """
        #launch command
        p = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)

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
            'output': []
        }
        if not killed:
            err = self.__remove_eol(p.stderr.readlines())
            if len(err)>0:
                result['error'] = True
                result['output'] = err
            else:
                result['output'] = self.__remove_eol(p.stdout.readlines())
                        
        return result



class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.c = Console()

    def test_successful_command(self):
        res = self.c.execute('ls -lh')
        self.assertFalse(res['error'])
        self.assertFalse(res['killed'])
        self.assertIsNot(len(res['output']), 0)
    
    def test_timeout_command(self):
        res = self.c.execute('sleep 4')
        self.assertTrue(res['killed'])
        self.assertFalse(res['error'])
        self.assertIs(len(res['output']), 0)

    def test_change_timeout_command(self):
        res = self.c.execute('sleep 4', 5.0)
        self.assertFalse(res['killed'])
        self.assertFalse(res['error'])
        self.assertIs(len(res['output']), 0)

    def test_failed_command(self):
        res = self.c.execute('ls -123456')
        self.assertFalse(res['killed'])
        self.assertTrue(res['error'])
        self.assertIsNot(len(res['output']), 0)

    def test_command_lsmod(self):
        res = self.c.execute('lsmod | grep snd_bcm2835 | wc -l')
        self.assertFalse(res['killed'])
        self.assertFalse(res['error'])
        self.assertIs(res['output'][0], '3')

    def test_command_uptime(self):
        res = self.c.execute('uptime')
        self.assertFalse(res['killed'])
        self.assertFalse(res['error'])
        self.assertIs(len(res['output']), 1)
