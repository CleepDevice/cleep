#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests: Systemctl ↔ /usr/bin/systemctl + journalctl (real binaries)."""

import unittest
import logging
import pytest

from cleep.libs.tests.lib import TestLib
from cleep.libs.commands.systemctl import Systemctl
from cleep.libs.tests.functional_helpers import setup_functional

SYSTEMCTL_STATUS_KEYS = (
    "state",
    "substate",
    "pid",
    "path",
    "start",
    "stop",
    "restarts",
    "runtime",
    "command",
)

SYSTEMCTL_STATES = (
    "active",
    "inactive",
    "failed",
    "activating",
    "deactivating",
    "maintenance",
    "reloading",
    "refreshing",
)


@pytest.mark.functional
class SystemctlFunctionalTests(unittest.TestCase):

    def setUp(self):
        setup_functional(self)
        TestLib.require_binary("/usr/bin/systemctl")
        TestLib.require_binary("/usr/bin/journalctl")
        self.s = Systemctl()

    def test_get_service_status_journald(self):
        status = self.s.get_service_status("systemd-journald")
        logging.info(status)
        self.assertIsNotNone(status, "systemctl show systemd-journald failed")
        for key in SYSTEMCTL_STATUS_KEYS:
            self.assertIn(key, status)
        self.assertIn(status["state"], SYSTEMCTL_STATES)

    def test_get_service_logs_journald(self):
        logs = self.s.get_service_logs("systemd-journald", minutes=5, lines=5)
        logging.info(logs)
        self.assertIsNotNone(logs, "journalctl for systemd-journald failed")
        self.assertIsInstance(logs, list)
        for entry in logs:
            self.assertEqual(len(entry), 3)
            dt, priority, message = entry
            self.assertIsNotNone(dt)
            self.assertIn(priority, Systemctl.PRIORITIES)
            self.assertIsInstance(message, str)
