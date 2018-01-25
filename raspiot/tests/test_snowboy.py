#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.snowboy import Snowboy
import unittest
import logging

logging.basicConfig(level=logging.WARN, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')

class SnowboyTests(unittest.TestCase):

    def setUp(self):
        self.s = Snowboy('00d4e117330634cdf22d29ea011f1f257433e0e1')

    def tearDown(self):
        pass

    def test_train(self):
        model = self.s.train('snowboy1.wav', 'snowboy2.wav', 'snowboy3.wav', 'coucou')
        self.assertIsNotNone(model)

