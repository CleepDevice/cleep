#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Shared helpers for functional tests (real OS binaries)."""

import logging

from cleep.libs.tests.lib import TestLib
from cleep.libs.tests.common import get_log_level
from cleep.libs.commands.iw import Iw
from cleep.libs.commands.iwconfig import Iwconfig

LOG_LEVEL = get_log_level()


def setup_functional(test_case):
    """Gate on CLEEP_FUNCTIONAL_TESTS and configure logging."""
    TestLib(test_case).set_functional_tests()
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
    )


def first_wifi_interface():
    """Best-effort wifi iface from iw/iwconfig; None if none."""
    adapters = Iw().get_adapters()
    if adapters:
        return next(iter(adapters.keys()))
    interfaces = Iwconfig().get_interfaces()
    if interfaces:
        return next(iter(interfaces.keys()))
    return None
