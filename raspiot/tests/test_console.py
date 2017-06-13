#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.console import Console
from raspiot.utils import InvalidParameter
import unittest
import os

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


