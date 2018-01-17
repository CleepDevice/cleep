#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.alsa import Alsa
import unittest
import logging

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class AlsaTests(unittest.TestCase):

    def setUp(self):
        self.a = Alsa()

    def tearDown(self):
        pass

    def test_get_playback_devices(self):
        devs = self.a.get_playback_devices()
        #print(devs)
        self.assertNotEqual(0, len(devs.keys()))
        raspi_jack = u'bcm2835 ALSA'
        raspi_hdmi = u'bcm2835 IEC958/HDMI'
        self.assertTrue(raspi_jack in devs.keys())
        self.assertTrue(raspi_hdmi in devs.keys())
        self.assertEqual(devs[raspi_jack][u'type'], self.a.OUTPUT_TYPE_JACK)
        self.assertEqual(devs[raspi_hdmi][u'type'], self.a.OUTPUT_TYPE_HDMI)

    def test_get_capture(self):
        devs = self.a.get_capture_devices()
        #print(devs)
        #self.assertNotEqual(0, len(devs.keys()))

    def test_get_volume(self):
        volumes = self.a.get_volumes()
        self.assertEqual(2, len(volumes.keys()))
        self.assertTrue(u'playback' in volumes.keys())
        self.assertTrue(u'capture' in volumes.keys())
        self.assertIsNotNone(volumes[u'playback'])

    def test_set_volume(self):
        volumes = self.a.set_volumes(playback=25)
        self.assertEqual(2, len(volumes.keys()))
        self.assertTrue(u'playback' in volumes.keys())
        self.assertTrue(u'capture' in volumes.keys())
        self.assertEqual(25, volumes[u'playback'])
        self.assertIsNone(volumes[u'capture'])

        volumes = self.a.set_volumes(playback=50)
        self.assertEqual(50, volumes[u'playback'])

