#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.configs.asoundrc import Asoundrc
from raspiot.libs.internals.cleepfilesystem import CleepFilesystem
import unittest
import logging
import os

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class AsoundrcTests(unittest.TestCase):

    def setUp(self):
        self.fs = CleepFilesystem()
        self.fs.enable_write()
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
        self.a = self.a(self.fs)

    def tearDown(self):
        if os.path.exists(self.fake):
            os.remove(self.fake)

    def test_get_configuration(self):
        config = self.a.get_configuration()
        logging.debug('config=%s' % config)

        self.assertNotEqual(None, config)

        self.assertTrue('section' in config.keys())
        self.assertTrue('type' in config.keys())
        self.assertTrue('cardid' in config.keys())
        self.assertTrue('deviceid' in config.keys())
        self.assertEqual(config['section'], 'pcm.!default')
        self.assertNotEqual(None, config['cardid'])
        self.assertNotEqual(None, config['deviceid'])

    def test_set_default_device(self):
        self.assertTrue(self.a.set_default_device(card_id=0, device_id=1)) #set HDMI
        config = self.a.get_configuration()
        logging.debug('config=%s' % config)

        self.assertTrue('section' in config.keys())
        self.assertTrue('type' in config.keys())
        self.assertTrue('cardid' in config.keys())
        self.assertTrue('deviceid' in config.keys())
        self.assertEqual(config['section'], 'pcm.!default')
        self.assertEqual(0, config['cardid'])
        self.assertEqual(1, config['deviceid'])


