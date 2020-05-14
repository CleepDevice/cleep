#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from audiodriver import AudioDriver
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.exception import MissingParameter, InvalidParameter, CommandError
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from cleep.libs.internals.task import Task
from unittest.mock import Mock
import time


class AudioDriverTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.fs = CleepFilesystem()
        self.fs.enable_write = Mock()
        self.fs.disable_write = Mock()

        self.a = AudioDriver(self.fs, 'dummy', 'dummyname')
        self.a.alsa = Mock()
        self.a.alsa.get_device_infos = Mock(return_value={
            'name': 'dummycard',
            'devices': [{
                'cardname': 'dummycard',
                'cardid': 0,
                'deviceid': 6,
            }]
        })
        self.a.get_card_name = Mock(return_value='dummycard')
        self.a.get_card_capabilities = Mock(return_value=(True, False))

    def tearDown(self):
        pass

    def test_get_device_infos(self):
        infos = self.a.get_device_infos()
        self.assertTrue(self.a.get_card_name.called)
        self.assertTrue(self.a.get_card_capabilities.called)
        self.assertTrue(self.a.alsa.get_device_infos.called)

        self.assertTrue('cardname' in infos)
        self.assertTrue('cardid' in infos)
        self.assertTrue('deviceid' in infos)
        self.assertTrue('playback' in infos)
        self.assertTrue('capture' in infos)
        self.assertEqual(infos['cardname'], 'dummycard')
        self.assertEqual(infos['cardid'], 0)
        self.assertEqual(infos['deviceid'], 6)
        self.assertEqual(infos['playback'], True)
        self.assertEqual(infos['capture'], False)

    def test_is_card_enabled(self):
        self.a.alsa.get_selected_device = Mock(return_value={
            'name': 'dummycard',
            'devices': [{
                'cardname': 'dummycard',
                'cardid': 0,
                'deviceid': 6,
            }]
        })
        self.assertTrue(self.a.is_card_enabled())

        self.a.alsa.get_selected_device = Mock(return_value={
            'name': 'dummycardxxx',
            'devices': [{
                'cardname': 'dummycard',
                'cardid': 0,
                'deviceid': 6,
            }]
        })
        self.assertFalse(self.a.is_card_enabled())

    def test_get_cardid_device_id(self):
        self.assertEqual(self.a.get_cardid_deviceid(), (0, 6))

        self.a.alsa.get_device_infos = Mock(return_value=None)
        self.assertEqual(self.a.get_cardid_deviceid(), (None, None))


if __name__ == '__main__':
    #coverage run --omit="/usr/local/lib/python*/*","*test_*.py" --concurrency=thread test_audiodriver.py; coverage report -m -i
    unittest.main()

