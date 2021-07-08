#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from ip import Ip
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from mock import Mock, patch


class IpTests(unittest.TestCase):

    SAMPLE_IP_A = """1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
inet 127.0.0.1/8 scope host lo
valid_lft forever preferred_lft forever
inet6 ::1/128 scope host
valid_lft forever preferred_lft forever
2: enxb827eb729ebf: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
link/ether b8:27:eb:72:9e:bf brd ff:ff:ff:ff:ff:ff
inet 192.168.1.232/24 brd 192.168.1.255 scope global enxb827eb729ebf
valid_lft forever preferred_lft forever
inet6 fe80::c91d:2bd7:28ed:64ed/64 scope link
valid_lft forever preferred_lft forever
3: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
link/ether b8:27:eb:27:cb:ea brd ff:ff:ff:ff:ff:ff
inet 192.168.1.245/24 brd 192.168.1.255 scope global wlan0
valid_lft forever preferred_lft forever
inet6 fe80::fba7:532b:6249:b63a/64 scope link
valid_lft forever preferred_lft forever"""

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')
        self.i = Ip()

    def tearDown(self):
        pass

    def test_is_installed(self):
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            self.assertTrue(self.i.is_installed())

        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            self.assertFalse(self.i.is_installed())

    def test_get_status(self):
        self.i.command = Mock(return_value={
            'returncode': 0,
            'stdout': self.SAMPLE_IP_A.split('\n'),
            'stderr': [],
            'killed': False
        })
        status = self.i.get_status()
        logging.debug('Status: %s' % status)

        self.maxDiff = None
        self.assertDictEqual(status, {
            'enxb827eb729ebf': {
                'interface': 'enxb827eb729ebf',
                'ipv4': '192.168.1.232',
                'netmask': '255.255.255.0',
                'ipv6': 'fe80::c91d:2bd7:28ed:64ed',
                'prefixlen': 64,
                'mac': 'b8:27:eb:72:9e:bf',
            },
            'wlan0': {
                'interface': 'wlan0',
                'ipv4': '192.168.1.245',
                'netmask': '255.255.255.0',
                'ipv6': 'fe80::fba7:532b:6249:b63a',
                'prefixlen': 64,
                'mac': 'b8:27:eb:27:cb:ea',
            },
        })

    def test_restart_interface(self):
        self.i.command = Mock(return_value={
            'returncode': 0,
            'stdout': [],
            'stderr': [],
            'killed': False
        })

        self.assertTrue(self.i.restart_interface('interface1'))

    def test_restart_interface(self):
        self.i.command = Mock(return_value={
            'returncode': 1,
            'stdout': [],
            'stderr': [],
            'killed': False
        })

        self.assertFalse(self.i.restart_interface('interface1'))

if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_ip.py; coverage report -m -i
    unittest.main()
