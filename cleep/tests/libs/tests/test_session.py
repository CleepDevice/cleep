# -*- coding: utf-8 -*-
"""Unit tests for TestSession (hybrid unittest / pytest tooling)."""
import unittest

import pytest

from cleep.libs.tests.session import TestSession


def _register_command(session, name, calls=0, params=None, lastto=None):
    """Populate bus command handler without running full module setup."""
    session._TestSession__setup_executed = True
    session._TestSession__bus_command_handlers[name] = {
        "data": None,
        "side_effect": None,
        "calls": calls,
        "fail": False,
        "noresponse": False,
        "params": params if params is not None else [],
        "lastto": lastto,
    }


def _register_event(session, name, sends=0, lastparams=None, lastdeviceid=None):
    session._TestSession__event_handlers[name] = {
        "sends": sends,
        "lastparams": lastparams,
        "lastdeviceid": lastdeviceid,
    }


class TestSessionUnittestCompat(unittest.TestCase):
    """Legacy path: TestSession(self) still works with TestCase asserts consumers."""

    def setUp(self):
        self.session = TestSession(self)

    def test_assert_command_not_called(self):
        _register_command(self.session, "ping", calls=0)
        self.session.assert_command_not_called("ping")

    def test_assert_command_called_fails_when_not_called(self):
        _register_command(self.session, "ping", calls=0)
        with self.assertRaises(AssertionError):
            self.session.assert_command_called("ping")


def test_session_without_testcase():
    session = TestSession()
    _register_command(session, "ping", calls=1, params=[{"a": 1}], lastto="system")
    session.assert_command_called("ping", to="system")
    session.assert_command_called_with("ping", {"a": 1}, to="system")


def test_session_assert_event_helpers():
    session = TestSession()
    _register_event(session, "system.device.delete", sends=1, lastparams={"id": "x"}, lastdeviceid="d1")
    session.assert_event_called("system.device.delete")
    session.assert_event_called_with("system.device.delete", {"id": "x"}, device_id="d1")
    session.assert_event_not_called("never.fired")


def test_cleep_session_fixture(cleep_session):
    assert isinstance(cleep_session, TestSession)
    assert cleep_session.testcase is None
    _register_command(cleep_session, "ping", calls=0)
    cleep_session.assert_command_not_called("ping")
    with pytest.raises(AssertionError):
        cleep_session.assert_command_called("ping")
