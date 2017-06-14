#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.console import Console
from raspiot.utils import InvalidParameter
import unittest
import os
import time

class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.c = Console()
        self.now = None

    def test_invalid_none_timeout(self):
        self.assertRaises(InvalidParameter, self.c.command, u'ls -lh', None)

    def test_invalid_timeout(self):
        self.assertRaises(InvalidParameter, self.c.command, u'ls -lh', 0.0)

    def test_successful_command(self):
        res = self.c.command(u'ls -lh')
        self.assertFalse(res[u'error'])
        self.assertFalse(res[u'killed'])
        self.assertNotEqual(len(res[u'stdout']), 0)
    
    def test_timeout_command(self):
        res = self.c.command(u'sleep 4')
        self.assertTrue(res[u'killed'])
        self.assertFalse(res[u'error'])
        self.assertEqual(len(res[u'stdout']), 0)

    def test_change_timeout_command(self):
        res = self.c.command(u'sleep 4', 5.0)
        self.assertFalse(res[u'killed'])
        self.assertFalse(res[u'error'])
        self.assertEqual(len(res[u'stdout']), 0)

    def test_failed_command(self):
        res = self.c.command(u'ls -123456')
        self.assertFalse(res[u'killed'])
        self.assertTrue(res[u'error'])
        self.assertNotEqual(len(res[u'stderr']), 0)

    def test_command_lsmod(self):
        res = self.c.command(u'lsmod | grep snd_bcm2835 | wc -l')
        self.assertFalse(res[u'killed'])
        self.assertFalse(res[u'error'])
        self.assertEqual(res[u'stdout'][0], u'3')

    def test_command_uptime(self):
        res = self.c.command(u'uptime')
        self.assertFalse(res[u'killed'])
        self.assertFalse(res[u'error'])
        self.assertEqual(len(res[u'stdout']), 1)

    def test_complex_command(self):
        res = self.c.command(u'cat /proc/partitions | awk -F " " \'$2==0 { print $4}\'')
        self.assertNotEqual(len(res), 0)

    def callback(self, result):
        now = time.time()
        self.assertTrue(now-self.now>=1.5)

    def test_delayed_command(self):
        self.now = time.time()
        self.c.command_delayed(u'uptime', 1.5, callback=self.callback)
        time.sleep(2.0)

    def test_unicode_stdout(self):
        msg = u'comment ça va, pas trop chaud l\'été'
        res = self.c.command(u'echo "%s"' % msg)
        self.assertFalse(res[u'error'])
        self.assertEqual(msg, res[u'stdout'][0].strip())

