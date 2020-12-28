#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from rfkill import Rfkill
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import Mock, patch

OUTPUT_GENERIC = """{
   "": [
      {"device":"phy0", "id":0, "type":"wlan", "type-desc":"Wireless LAN", "soft": "blocked", "hard": "unblocked"},
      {"device":"hci0", "id":1, "type":"bluetooth", "type-desc":"Bluetooth", "soft": "unblocked", "hard": "unblocked"}
   ]
}"""
OUTPUT_NO_WLAN = """{
   "": [
      {"device":"hci0", "id":1, "type":"bluetooth", "type-desc":"Bluetooth", "soft": "unblocked", "hard": "unblocked"}
   ]
}"""
OUTPUT_NO_BLUETOOTH = """{
   "": [
      {"device":"phy0", "id":0, "type":"wlan", "type-desc":"Wireless LAN", "soft": "blocked", "hard": "unblocked"}
   ]
}"""

class TestsRfkill(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.r = Rfkill()

    def tearDown(self):
        pass

    def make_command_resp(self, return_code=0, stdout=[]):
        return {
            'returncode': return_code,
            'killed': False,
            'error': False,
            'stderr': [],
            'stdout': stdout,
        }

    @patch('rfkill.os.path.exists')
    def test_is_installed(self, mock_exists):
        mock_exists.return_value = True

        self.assertTrue(self.r.is_installed())

    @patch('rfkill.os.path.exists')
    def test_is_installed(self, mock_exists):
        mock_exists.return_value = False

        self.assertFalse(self.r.is_installed())

    def test_get_wifi_infos(self):
        self.r.command = Mock(return_value=self.make_command_resp(stdout=OUTPUT_GENERIC.split('\n')))

        infos = self.r.get_wifi_infos()
        logging.debug('Infos: %s' % infos)

        self.assertDictEqual(infos, {
            'device': 'phy0',
            'id': 0,
            'desc': 'Wireless LAN',
            'blocked': True
        })

    def test_get_wifi_command_failed(self):
        self.r.command = Mock(return_value=self.make_command_resp(return_code=1))

        infos = self.r.get_wifi_infos()
        logging.debug('Infos: %s' % infos)

        self.assertIsNone(infos)

    def test_get_wifi_no_wlan(self):
        self.r.command = Mock(return_value=self.make_command_resp(stdout=OUTPUT_NO_WLAN))

        infos = self.r.get_wifi_infos()
        logging.debug('Infos: %s' % infos)

        self.assertIsNone(infos)

    def test_get_bluetooth_infos(self):
        self.r.command = Mock(return_value=self.make_command_resp(stdout=OUTPUT_GENERIC.split('\n')))

        infos = self.r.get_bluetooth_infos()
        logging.debug('Infos: %s' % infos)

        self.assertDictEqual(infos, {
            'device': 'hci0',
            'id': 1,
            'desc': 'Bluetooth',
            'blocked': False
        })

    def test_get_bluetooth_command_failed(self):
        self.r.command = Mock(return_value=self.make_command_resp(return_code=1))

        infos = self.r.get_bluetooth_infos()
        logging.debug('Infos: %s' % infos)

        self.assertIsNone(infos)

    def test_get_bluetooth_no_bluetooth(self):
        self.r.command = Mock(return_value=self.make_command_resp(stdout=OUTPUT_NO_BLUETOOTH))

        infos = self.r.get_bluetooth_infos()
        logging.debug('Infos: %s' % infos)

        self.assertIsNone(infos)

    def test_private_block_device_block_device(self):
        self.r.command = Mock(return_value=self.make_command_resp(return_code=0))

        self.assertTrue(self.r._Rfkill__block_device(0, True))

        self.r.command.assert_called_with('/usr/sbin/rfkill block 0')

    def test_private_block_device_unblock_device(self):
        self.r.command = Mock(return_value=self.make_command_resp(return_code=0))

        self.assertTrue(self.r._Rfkill__block_device(1, False))

        self.r.command.assert_called_with('/usr/sbin/rfkill unblock 1')

    def test_private_block_device_unblock_all(self):
        self.r.command = Mock(return_value=self.make_command_resp(return_code=0))

        self.assertTrue(self.r._Rfkill__block_device(None, False))

        self.r.command.assert_called_with('/usr/sbin/rfkill unblock all')

    def test_private_block_device_command_failed(self):
        self.r.command = Mock(return_value=self.make_command_resp(return_code=1))

        self.assertFalse(self.r._Rfkill__block_device(0, True))

    def test_block_device(self):
        self.r._Rfkill__block_device = Mock(return_value=True)

        self.assertTrue(self.r.block_device(0))
        self.r._Rfkill__block_device.assert_called_with(0, True)

    def test_block_device(self):
        self.r._Rfkill__block_device = Mock(return_value=True)

        self.assertTrue(self.r.block_device(None))
        self.r._Rfkill__block_device.assert_called_with(None, True)

    def test_unblock_device(self):
        self.r._Rfkill__block_device = Mock(return_value=True)

        self.assertTrue(self.r.unblock_device(0))
        self.r._Rfkill__block_device.assert_called_with(0, False)

    def test_unblock_device(self):
        self.r._Rfkill__block_device = Mock(return_value=True)

        self.assertTrue(self.r.unblock_device(None))
        self.r._Rfkill__block_device.assert_called_with(None, False)


if __name__ == '__main__':
    # coverage run --omit="*lib/python*/*","*test_*.py" --concurrency=thread test_rfkill.py; coverage report -m -i
    unittest.main()
