#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append('/root/cleep/raspiot/libs/commands')
from alsa import Alsa
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
from raspiot.exceptions import MissingParameter, InvalidParameter, CommandError
from raspiot.libs.tests.lib import TestLib
import unittest
import logging
from pprint import pformat


class AlsaTests(unittest.TestCase):

    PLAYBACK_PATTERN = (u'Mono', r'\[(\d*)%\]') #code from bcm2835 driver in audio app
    WAV_TEST = '/root/cleep/medias/sounds/connected.wav'

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')
        self.fs = CleepFilesystem()
        self.a = Alsa(self.fs)

    def tearDown(self):
        pass

    def test_get_playback_devices(self):
        devs = self.a.get_playback_devices()
        logging.debug(devs)
        self.assertNotEqual(0, len(devs.keys()))
        raspi_jack = u'bcm2835 ALSA'
        raspi_hdmi = u'bcm2835 IEC958/HDMI'

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
        devs = self.a.get_capture_devices()
        logging.debug(pformat(devs))
        #record feature may not be available
        #self.assertEqual(0, len(devs))

    def test_get_volume(self):
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
        old_volume = self.a.get_volume('PCM', self.PLAYBACK_PATTERN)
        volume = self.a.set_volume('PCM', self.PLAYBACK_PATTERN, 25)
        self.assertEqual(25, volume)
        #restore old volume
        self.a.set_volume('PCM', self.PLAYBACK_PATTERN, old_volume)

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
        device = self.a.get_selected_device()
        logging.debug(device)
        self.assertTrue('name' in device)
        self.assertTrue('devices' in device)
        self.assertGreaterEqual(len(device['devices']), 2)

    def test_get_device_infos(self):
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
        #numid 3: PCM playback route
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
        self.assertTrue(cm.exception.message.startswith(u'Sound file doesn\'t exist'))
    
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
    #coverage run --omit="/usr/local/lib/python2.7/*","test_*" --concurrency=thread test_alsa.py; coverage report -m
    unittest.main()
