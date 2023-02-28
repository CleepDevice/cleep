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
from unittest.mock import Mock, patch
import time
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class TestAudioDriver(unittest.TestCase):

    PLAYBACK_DEVICES = {
        0: {
            'name': 'Headphones',
            'desc': 'bcm2835 Headphones',
            'devices': {
                0: {
                    'cardid': 0,
                    'deviceid': 0,
                    'name': 'bcm2835 Headphones',
                    'desc': 'bcm2835 Headphones',
                }
            }
        },
    }
    CONTROLS = [
        {'numid': 2, 'iface': 'MIXER', 'name': 'Headphone Playback Switch'},
        {'numid': 1, 'iface': 'MIXER', 'name': 'Headphone Playback Volume'},
    ]

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

        self.fs = Mock()
        self.a = AudioDriver('dummy')
        self.a.cleep_filesystem = self.fs

    def tearDown(self):
        pass

    @patch('audiodriver.CleepAudio')
    @patch('audiodriver.Alsa')
    def test__on_registered(self, alsa_mock, cleepaudio_mock):
        self.a._on_audio_registered = Mock()
        self.a._get_card_name = Mock(return_value='dummy-card')

        self.a._on_registered()
        logging.debug('Card name: %s', self.a._AudioDriver__card_name)
        
        self.assertEqual(self.a._AudioDriver__card_name, 'dummy-card')
        self.a._on_audio_registered.assert_called()
        alsa_mock.assert_called_with(self.fs)
        cleepaudio_mock.assert_called_with(self.fs)

    def test__get_card_name(self):
        alsa_mock = Mock()
        alsa_mock.get_playback_devices.return_value = self.PLAYBACK_DEVICES
        self.a.alsa = alsa_mock
        self.a._get_card_name = Mock(return_value='Headphones')

        card_name = self.a._AudioDriver__get_card_name()

        self.assertEqual(card_name, 'Headphones')
        self.a._get_card_name.assert_called_with([
            {'card_name': 'Headphones', 'card_desc': 'bcm2835 Headphones', 'device_name': 'bcm2835 Headphones', 'device_desc': 'bcm2835 Headphones'}
        ])

    def test_get_card_name(self):
        self.a._AudioDriver__card_name = 'Headphones'

        card_name = self.a.get_card_name()

        self.assertEqual(card_name, 'Headphones')

    def test_get_device_infos(self):
        self.a._AudioDriver__card_name = 'Headphones'
        self.a.get_alsa_infos = Mock(return_value=self.PLAYBACK_DEVICES[0])
        self.a.get_card_capabilities = Mock(return_value=(True, False))

        infos = self.a.get_device_infos()
        logging.debug('infos: %s', infos)

        self.assertDictEqual(infos, {
            'cardname': 'Headphones',
            'cardid': 0,
            'deviceid': 0,
            'playback': True,
            'capture': False
        })
        self.a.get_card_capabilities.assert_called()

    def test_get_device_infos_no_card_name(self):
        self.a._AudioDriver__card_name = None

        with self.assertRaises(Exception) as cm:
            self.a.get_device_infos()
        self.assertEqual(str(cm.exception), 'No hardware found for driver "AudioDriver"')

    def test_is_card_enabled(self):
        self.a._AudioDriver__card_name = 'Headphones'
        alsa_mock = Mock()
        alsa_mock.get_selected_device.return_value = self.PLAYBACK_DEVICES[0]
        self.a.alsa = alsa_mock
        self.a._set_volumes_controls = Mock()

        self.assertTrue(self.a.is_card_enabled())

        self.a._set_volumes_controls.assert_called()

    def test_is_card_enabled_not_enabled(self):
        self.a._AudioDriver__card_name = 'dummy'
        alsa_mock = Mock()
        alsa_mock.get_selected_device.return_value = self.PLAYBACK_DEVICES[0]
        self.a.alsa = alsa_mock
        self.a._set_volumes_controls = Mock()

        self.assertFalse(self.a.is_card_enabled())

        self.assertFalse(self.a._set_volumes_controls.called)

    def test_get_cardid_device_id(self):
        self.a.get_alsa_infos = Mock(return_value=self.PLAYBACK_DEVICES[0])

        self.assertEqual(self.a.get_cardid_deviceid(), (0, 0))

    def test_get_cardid_device_id_not_enabled(self):
        self.a.get_alsa_infos = Mock(return_value=None)

        self.assertEqual(self.a.get_cardid_deviceid(), (None, None))

    def test_get_alsa_infos(self):
        self.a._AudioDriver__card_name = 'dummy'
        alsa_mock = Mock()
        alsa_mock.get_device_infos.return_value = self.PLAYBACK_DEVICES[0]
        self.a.alsa = alsa_mock

        infos = self.a.get_alsa_infos()
        logging.debug('infos: %s', infos)

        self.assertDictEqual(infos, self.PLAYBACK_DEVICES[0])
        alsa_mock.get_device_infos.assert_called_with('dummy')

    def test_get_alsa_infos_card_not_found(self):
        self.a._AudioDriver__card_name = 'dummy'
        alsa_mock = Mock()
        alsa_mock.get_device_infos.return_value = None
        self.a.alsa = alsa_mock

        infos = self.a.get_alsa_infos()
        logging.debug('infos: %s', infos)

        self.assertIsNone(infos)
        alsa_mock.get_device_infos.assert_called_with('dummy')

    def test_get_control_numid(self):
        alsa_mock = Mock()
        alsa_mock.get_controls.return_value = self.CONTROLS
        self.a.alsa = alsa_mock
        
        numid = self.a.get_control_numid(self.CONTROLS[1]['name'])

        self.assertEqual(numid, self.CONTROLS[1]['numid'])

    def test_get_control_numid_not_found(self):
        alsa_mock = Mock()
        alsa_mock.get_controls.return_value = self.CONTROLS
        self.a.alsa = alsa_mock
        
        numid = self.a.get_control_numid('dummy')

        self.assertIsNone(numid)


if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_audiodriver.py; coverage report -m -i
    unittest.main()

