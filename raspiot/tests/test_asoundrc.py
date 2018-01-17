#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.asoundrc import Asoundrc
import unittest
import logging
import os

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class AsoundrcTests(unittest.TestCase):

    def setUp(self):
        self.a = Asoundrc
        #fake asoundrc file
        self.fake = '/tmp/fake_asoundrc'
        fd = open(self.fake, 'w')
        fd.write("""
        pcm.!default {
            type hw
            card 0
            device 0
        }

        ctl.!default {
            type hw           
            card 0
        }""")
        fd.close()
        self.a.CONF = self.fake
        self.a = self.a()

    def tearDown(self):
        if os.path.exists(self.fake):
            os.remove(self.fake)

    def test_get_configuration(self):
        config = self.a.get_configuration()
        #print(config)

        self.assertNotEqual(0, len(config.keys()))

        self.assertTrue('pcm.!default' in config.keys())
        self.assertTrue('type' in config['pcm.!default'].keys())
        self.assertTrue('cardid' in config['pcm.!default'].keys())
        #self.assertTrue('cardname' in config['pcm.!default'].keys())
        self.assertTrue('deviceid' in config['pcm.!default'].keys())
        self.assertNotEqual(None, config['pcm.!default']['type'])
        self.assertNotEqual(None, config['pcm.!default']['cardid'])
        #self.assertNotEqual(None, config['pcm.!default']['cardname'])
        self.assertNotEqual(None, config['pcm.!default']['deviceid'])

        self.assertTrue('ctl.!default' in config.keys())
        self.assertTrue('type' in config['ctl.!default'].keys())
        self.assertTrue('cardid' in config['ctl.!default'].keys())
        #self.assertTrue('cardname' in config['ctl.!default'].keys())
        self.assertTrue('deviceid' in config['ctl.!default'].keys())
        self.assertNotEqual(None, config['ctl.!default']['type'])
        self.assertNotEqual(None, config['ctl.!default']['cardid'])
        #self.assertNotEqual(None, config['ctl.!default']['cardname'])
        self.assertEqual(None, config['ctl.!default']['deviceid'])

    def test_set_default_card(self):
        self.assertTrue(self.a.set_default_card(card_id=0, device_id=1)) #set HDMI
        config = self.a.get_configuration()
        #print(config)

        self.assertTrue('pcm.!default' in config.keys())
        self.assertEqual(0, config['pcm.!default']['cardid'])
        self.assertEqual(1, config['pcm.!default']['deviceid'])

        self.assertTrue('ctl.!default' in config.keys())
        self.assertEqual(0, config['ctl.!default']['cardid'])
        self.assertEqual(None, config['ctl.!default']['deviceid'])

    #def test_set_default_card_with_invalid_infos(self):
    #    self.assertFalse(self.a.set_default_card(card_id=5, device_id=0))
    #    self.assertFalse(self.a.set_default_card(card_id=0, device_id=15))

