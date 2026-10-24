#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Alsa ↔ /usr/bin/aplay, arecord, amixer (real binaries)."""

import unittest
import logging
import pytest
from unittest.mock import Mock

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.alsa import Alsa
from cleep.libs.tests.functional_helpers import setup_functional

PLAYBACK_DEVICE_KEYS = ("name", "desc", "devices")
PLAYBACK_SUBDEVICE_KEYS = ("name", "desc", "cardid", "deviceid")
ALSA_CONTROL_KEYS = ("numid", "iface", "name")


@pytest.mark.functional
class AlsaFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/usr/bin/aplay")
        TestLib.require_binary("/usr/bin/arecord")
        TestLib.require_binary("/usr/bin/amixer")
        self.a = Alsa(Mock())

    def test_get_playback_and_capture_devices(self):
        playback = self.a.get_playback_devices()
        capture = self.a.get_capture_devices()
        logging.info("playback=%s capture=%s", playback, capture)
        self.assertIsInstance(playback, dict)
        self.assertIsInstance(capture, dict)
        for card in playback.values():
            for key in PLAYBACK_DEVICE_KEYS:
                self.assertIn(key, card)
            for sub in card["devices"].values():
                for key in PLAYBACK_SUBDEVICE_KEYS:
                    self.assertIn(key, sub)

    def test_get_controls(self):
        simple = self.a.get_simple_controls()
        controls = self.a.get_controls()
        logging.info("simple=%s controls=%s", simple, controls)
        self.assertIsInstance(simple, list)
        self.assertIsInstance(controls, list)
        for control in controls:
            for key in ALSA_CONTROL_KEYS:
                self.assertIn(key, control)
