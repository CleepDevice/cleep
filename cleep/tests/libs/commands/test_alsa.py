#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from alsa import Alsa
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.exception import MissingParameter, InvalidParameter, CommandError
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pformat
from mock import patch, Mock

class TestsAlsa(unittest.TestCase):

    PLAYBACK_PATTERN = ('Mono', r'\[(\d*)%\]') #code from bcm2835 driver in audio app
    WAV_TEST = '/root/cleep/medias/sounds/connected.wav'

    SAMPLE_PLAYBACK_DEVICES = """**** List of PLAYBACK Hardware Devices ****
card 0: ALSA [bcm2835 ALSA], device 0: bcm2835 ALSA [bcm2835 ALSA]
  Subdevices: 7/7
  Subdevice #0: subdevice #0
  Subdevice #1: subdevice #1
  Subdevice #2: subdevice #2
  Subdevice #3: subdevice #3
  Subdevice #4: subdevice #4
  Subdevice #5: subdevice #5
  Subdevice #6: subdevice #6
card 0: ALSA [bcm2835 ALSA], device 1: bcm2835 IEC958/HDMI [bcm2835 IEC958/HDMI]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 0: ALSA [bcm2835 ALSA], device 2: bcm2835 IEC958/HDMI1 [bcm2835 IEC958/HDMI1]
  Subdevices: 1/1
  Subdevice #0: subdevice #0"""
    SAMPLE_RECORD_DEVICES = """**** List of CAPTURE Hardware Devices ****
card 0: IXP [ATI IXP], device 0: ATI IXP AC97 [ATI IXP AC97]
  Subdevices: 1/1
  Subdevice #0: subdevice #0"""
    SAMPLE_GET_VOLUME = """Simple mixer control 'PCM',0
  Capabilities: pvolume pvolume-joined pswitch pswitch-joined
  Playback channels: Mono
  Limits: Playback -10239 - 400
  Mono: Playback -2046 [77%] [-20.46dB] [on]"""
    SAMPLE_SET_VOLUME = """Simple mixer control 'PCM',0
  Capabilities: pvolume pvolume-joined pswitch pswitch-joined
  Playback channels: Mono
  Limits: Playback -10239 - 400
  Mono: Playback -7579 [25%] [-75.79dB] [on]"""
    SAMPLE_GET_CONTROL = """numid=3,iface=MIXER,name='PCM Playback Route'
    ; type=INTEGER,access=rw------,values=1,min=0,max=3,step=0
    : values=0"""
    SAMPLE_GET_INFOS = """Card default 'ALSA'/'bcm2835 ALSA'"""
    SAMPLE_SCONTROLS = """Simple mixer control 'PCM',0"""
    SAMPLE_CONTROLS = """numid=3,iface=MIXER,name='PCM Playback Route'
numid=2,iface=MIXER,name='PCM Playback Switch'
numid=1,iface=MIXER,name='PCM Playback Volume'
numid=5,iface=PCM,name='IEC958 Playback Con Mask'
numid=4,iface=PCM,name='IEC958 Playback Default'"""

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format='%(asctime)s %(name)s %(levelname)s : %(message)s')
        self.fs = CleepFilesystem()
        self.a = Alsa(self.fs)

    def tearDown(self):
        pass

    def make_command_result(self, return_code=0, error=False, killed=False, stdout='', stderr=''):
        return {
            'returncode': return_code,
            'error': error,
            'killed': killed,
            'stdout': stdout.split('\n'),
            'stderr': stderr.split('\n'),
        }

    def test_get_simple_controls(self):
        self.a.command = Mock(return_value=self.make_command_result(stdout=self.SAMPLE_SCONTROLS))
        controls = self.a.get_simple_controls()
        logging.debug('controls: %s' % controls)

        self.assertListEqual(controls, ['PCM'])

    def test_get_controls(self):
        self.a.command = Mock(return_value=self.make_command_result(stdout=self.SAMPLE_CONTROLS))
        controls = self.a.get_controls()
        logging.debug('controls: %s'% controls)

        self.assertCountEqual(controls, [
            {'numid': 1, 'iface': 'MIXER', 'name': 'PCM Playback Volume'},
            {'numid': 2, 'iface': 'MIXER', 'name': 'PCM Playback Switch'},
            {'numid': 3, 'iface': 'MIXER', 'name': 'PCM Playback Route'},
            {'numid': 4, 'iface': 'PCM', 'name': 'IEC958 Playback Default'},
            {'numid': 5, 'iface': 'PCM', 'name': 'IEC958 Playback Con Mask'},
        ])

    def test_get_playback_devices(self):
        self.a.command = Mock(return_value=self.make_command_result(stdout=self.SAMPLE_PLAYBACK_DEVICES))
        devs = self.a.get_playback_devices()
        logging.debug(devs)
        self.assertNotEqual(0, len(devs.keys()))
        raspi_jack = 'bcm2835 ALSA'
        raspi_hdmi = 'bcm2835 IEC958/HDMI'

        #get default sound card
        raspi_devices = None
        for _, dev in devs.items():
            logging.debug(pformat(dev))
            if dev['name']==raspi_jack:
                raspi_devices = dev['devices']
                break
        self.assertIsNotNone(raspi_devices, 'Default audio device not found')
        self.assertTrue(raspi_devices[0]['name']==raspi_jack, 'Audio jack not found')
        self.assertTrue(raspi_devices[0]['cardid']==0, 'Audio jack cardid invalid')
        self.assertTrue(raspi_devices[0]['deviceid']==0, 'Audio jack deviceid invalid')
        self.assertTrue(raspi_devices[1]['name']==raspi_hdmi, 'Audio HDMI not found')
        self.assertTrue(raspi_devices[1]['cardid']==0, 'Audio HDMI cardid invalid')
        self.assertTrue(raspi_devices[1]['deviceid']==1, 'Audio HDMI deviceid invalid')

    def test_get_capture_devices(self):
        self.a.command = Mock(return_value=self.make_command_result(stdout=self.SAMPLE_RECORD_DEVICES))
        devs = self.a.get_capture_devices()
        logging.debug(pformat(devs))

        self.assertEqual(1, len(devs))
        self.assertEqual(devs[0]['devices'][0]['name'], 'ATI IXP AC97')

    def test_get_volume(self):
        self.a.command = Mock(return_value=self.make_command_result(stdout=self.SAMPLE_GET_VOLUME))
        volume = self.a.get_volume('PCM', self.PLAYBACK_PATTERN)
        logging.debug('Volume: %s' % volume)
        self.assertTrue(isinstance(volume, int))

    def test_get_volume_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.a.get_volume(None, self.PLAYBACK_PATTERN)
        self.assertEqual(cm.exception.message, 'Parameter "control" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.a.get_volume('', self.PLAYBACK_PATTERN)
        self.assertEqual(cm.exception.message, 'Parameter "control" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.a.get_volume('PCM', None)
        self.assertEqual(cm.exception.message, 'Parameter "pattern" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.a.get_volume('PCM', '')
        self.assertEqual(cm.exception.message, 'Parameter "pattern" is missing')

    def test_get_volume_invalid_control(self):
        volume = self.a.get_volume('TEST', self.PLAYBACK_PATTERN)
        self.assertIsNone(volume, 'Volume should be None')

    def test_set_volume(self):
        self.a.command = Mock(return_value=self.make_command_result(stdout=self.SAMPLE_SET_VOLUME))
        volume = self.a.set_volume('PCM', self.PLAYBACK_PATTERN, 25)
        self.assertEqual(25, volume)

    def test_set_volume_invalid_parameters(self):
        with self.assertRaises(MissingParameter) as cm:
            self.a.set_volume(None, self.PLAYBACK_PATTERN, 12)
        self.assertEqual(cm.exception.message, 'Parameter "control" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.a.set_volume('', self.PLAYBACK_PATTERN, 12)
        self.assertEqual(cm.exception.message, 'Parameter "control" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.a.set_volume('PCM', None, 12)
        self.assertEqual(cm.exception.message, 'Parameter "pattern" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.a.set_volume('PCM', '', 12)
        self.assertEqual(cm.exception.message, 'Parameter "pattern" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.set_volume('PCM', self.PLAYBACK_PATTERN, -1)
        self.assertEqual(cm.exception.message, 'Parameter "volume" must be 0...100')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.set_volume('PCM', self.PLAYBACK_PATTERN, 101)
        self.assertEqual(cm.exception.message, 'Parameter "volume" must be 0...100')
        with self.assertRaises(MissingParameter) as cm:
            self.a.set_volume('PCM', self.PLAYBACK_PATTERN, None)
        self.assertEqual(cm.exception.message, 'Parameter "volume" is missing')

    def test_set_volume_invalid_control(self):
        volume = self.a.set_volume('TEST', self.PLAYBACK_PATTERN, 25)
        self.assertIsNone(volume, 'Volume should be None')

    def test_get_selected_device(self):
        self.a.command = Mock(side_effect=[
            self.make_command_result(stdout=self.SAMPLE_GET_INFOS),
            self.make_command_result(stdout=self.SAMPLE_PLAYBACK_DEVICES),
        ])
        device = self.a.get_selected_device()
        logging.debug(device)
        self.assertTrue('name' in device)
        self.assertTrue('devices' in device)
        self.assertGreaterEqual(len(device['devices']), 2)

    def test_get_device_infos(self):
        self.a.command = Mock(return_value=self.make_command_result(stdout=self.SAMPLE_PLAYBACK_DEVICES))
        device = self.a.get_device_infos('bcm2835 ALSA')
        logging.debug(device)
        self.assertTrue('name' in device)
        self.assertTrue('devices' in device)
        self.assertGreaterEqual(len(device['devices']), 2)

    def test_get_device_infos_invalid_name(self):
        device = self.a.get_device_infos('')
        self.assertIsNone(device, 'Function should return None')
        device = self.a.get_device_infos(None)
        self.assertIsNone(device, 'Function should return None')

    def test_amixer_control_get(self):
        self.a.command = Mock(return_value=self.make_command_result(stdout=self.SAMPLE_GET_CONTROL))
        # numid 3: xxx playback route
        value = self.a.amixer_control(Alsa.CGET, 3)
        logging.debug('value=%s' % value)
        self.assertTrue('iface' in value)
        self.assertTrue('name' in value)
        self.assertTrue('min' in value)
        self.assertTrue('max' in value)
        self.assertTrue('step' in value)
        self.assertTrue('values' in value)

    def test_amixer_control_invalid_params(self):
        with self.assertRaises(MissingParameter) as cm:
            self.a.amixer_control(None, 3)
        self.assertEqual(cm.exception.message, 'Parameter "command" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.amixer_control(4, 3)
        self.assertEqual(cm.exception.message, 'Parameter "command" must be Alsa.CGET or Alsa.CSET')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.amixer_control('TEST', 3)
        self.assertEqual(cm.exception.message, 'Parameter "command" must be Alsa.CGET or Alsa.CSET')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.amixer_control(Alsa.CGET, 'TEST')
        self.assertEqual(cm.exception.message, 'Parameter "numid" must be a string')
        with self.assertRaises(MissingParameter) as cm:
            self.a.amixer_control(Alsa.CSET, 3, None)
        self.assertEqual(cm.exception.message, 'Parameter "value" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.amixer_control(Alsa.CSET, 3, 6.7)
        self.assertEqual(cm.exception.message, 'Parameter "value" is invalid. Int or str awaited')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.amixer_control(Alsa.CSET, 3, ['ced'])
        self.assertEqual(cm.exception.message, 'Parameter "value" is invalid. Int or str awaited')

    def test_play_sound(self):
        self.assertTrue(self.a.play_sound(self.WAV_TEST), 'Unable to play valid sound file')

    def test_play_sound_invalid_params(self):
        with self.assertRaises(MissingParameter) as cm:
            self.a.play_sound(None)
        self.assertEqual(cm.exception.message, 'Parameter "path" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.play_sound('invalid/path/to/waw/file')
        self.assertTrue(cm.exception.message.startswith('Sound file doesn\'t exist'))
    
    def test_record_sound(self):
        record_path = None
        try:
            record_path = self.a.record_sound(timeout=1.0)
            #record feature available
            self.assertTrue(os.path.exists(record_path))

        except Exception as e:
            # no record feature available
            self.assertTrue(isinstance(e, CommandError))
            self.assertEqual(str(e), 'Unable to record audio')

        finally:
            if record_path:
                os.remove(record_path)

    def test_record_sound_invalid_params(self):
        with self.assertRaises(MissingParameter) as cm:
            self.a.record_sound(None, Alsa.RATE_44K, Alsa.FORMAT_S32LE, 1.0)
        self.assertEqual(cm.exception.message, 'Parameter "channels" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.record_sound('', Alsa.RATE_44K, Alsa.FORMAT_S32LE, 1.0)
        self.assertEqual(cm.exception.message, 'Parameter "channels" is invalid. Please check supported value.')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.record_sound(4, Alsa.RATE_44K, Alsa.FORMAT_S32LE, 1.0)
        self.assertEqual(cm.exception.message, 'Parameter "channels" is invalid. Please check supported value.')

        with self.assertRaises(MissingParameter) as cm:
            self.a.record_sound(Alsa.CHANNELS_STEREO, None, Alsa.FORMAT_S32LE, 1.0)
        self.assertEqual(cm.exception.message, 'Parameter "rate" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.record_sound(Alsa.CHANNELS_STEREO, '', Alsa.FORMAT_S32LE, 1.0)
        self.assertEqual(cm.exception.message, 'Parameter "rate" is invalid. Please check supported value.')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.record_sound(Alsa.CHANNELS_STEREO, 10000, Alsa.FORMAT_S32LE, 1.0)
        self.assertEqual(cm.exception.message, 'Parameter "rate" is invalid. Please check supported value.')

        with self.assertRaises(MissingParameter) as cm:
            self.a.record_sound(Alsa.CHANNELS_STEREO, Alsa.RATE_44K, None, 1.0)
        self.assertEqual(cm.exception.message, 'Parameter "format" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.record_sound(Alsa.CHANNELS_STEREO, Alsa.RATE_44K, '', 1.0)
        self.assertEqual(cm.exception.message, 'Parameter "format" is invalid. Please check supported value.')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.record_sound(Alsa.CHANNELS_STEREO, Alsa.RATE_44K, 'test', 1.0)
        self.assertEqual(cm.exception.message, 'Parameter "format" is invalid. Please check supported value.')
        with self.assertRaises(InvalidParameter) as cm:
            self.a.record_sound(Alsa.CHANNELS_STEREO, Alsa.RATE_44K, 5, 1.0)
        self.assertEqual(cm.exception.message, 'Parameter "format" is invalid. Please check supported value.')

    def test_save(self):
        self.assertTrue(self.a.save(), 'Configuration not saved')

if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_alsa.py; coverage report -m -i
    unittest.main()
