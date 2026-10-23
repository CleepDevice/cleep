#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.tests.lib import TestLib
import os
import unittest
import logging
import time
from threading import Event
from unittest.mock import Mock

from cleep.libs.internals.criticalresources import CriticalResources
from cleep.libs.internals.resource_catalog import (
    AUDIO_CAPTURE,
    AUDIO_PLAYBACK,
    ResourceDenyReason,
    ResourcePriority,
    make_session,
)
from cleep.libs.internals.taskfactory import TaskFactory
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class SyncTaskFactory:
    """Run create_task callbacks immediately; timers fire on demand."""

    def __init__(self):
        self.timers = []

    def create_task(
        self, interval, task, task_args=None, task_kwargs=None, end_callback=None
    ):
        task_args = task_args or []
        task_kwargs = task_kwargs or {}
        mock = Mock()

        def start():
            task(*task_args, **task_kwargs)
            if end_callback:
                end_callback()

        mock.start = start
        mock.wait = Mock()
        return mock

    def create_timer(self, interval, task, task_args=None, task_kwargs=None):
        task_args = task_args or []
        task_kwargs = task_kwargs or {}
        mock = Mock()
        mock.interval = interval
        mock.task = task
        mock.task_args = task_args
        mock.cancelled = False

        def start():
            pass

        def cancel():
            mock.cancelled = True

        def fire():
            if not mock.cancelled:
                task(*task_args, **task_kwargs)

        mock.start = start
        mock.cancel = cancel
        mock.fire = fire
        self.timers.append(mock)
        return mock


class CriticalResourcesTests(unittest.TestCase):
    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL,
            format="%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
        )
        self.tf = SyncTaskFactory()
        self.c = CriticalResources({"task_factory": self.tf}, False)
        self.events = []

    def _handlers(self, module):
        return {
            "on_granted": lambda session: self.events.append(
                ("granted", module, session)
            ),
            "on_revoke_requested": lambda session: self.events.append(
                ("revoke_requested", module, session)
            ),
            "on_revoked": lambda session, forced=False: self.events.append(
                ("revoked", module, session, forced)
            ),
            "on_denied": lambda session, reason="": self.events.append(
                ("denied", module, session, reason)
            ),
        }

    def test_catalogue_loaded(self):
        resources = list(self.c.get_resources())
        self.assertIn(AUDIO_PLAYBACK, resources)
        self.assertIn(AUDIO_CAPTURE, resources)

    def test_register_and_acquire(self):
        self.c.register("player", self._handlers("player"))
        session = make_session("player", AUDIO_PLAYBACK)
        self.c.acquire(session)
        self.assertEqual(self.c.resources[AUDIO_PLAYBACK]["holder"], "player")
        self.assertEqual(self.events[-1][0], "granted")

    def test_register_unknown_resource(self):
        with self.assertRaises(Exception) as cm:
            self.c.register(
                "player", self._handlers("player"), permanent_resources=("nope",)
            )
        self.assertIn("does not exists", str(cm.exception))

    def test_register_invalid_handlers(self):
        with self.assertRaises(Exception):
            self.c.register("player", {"on_granted": None})

    def test_permanent_exclusive_first_wins(self):
        self.c.register(
            "mic", self._handlers("mic"), permanent_resources=(AUDIO_CAPTURE,)
        )
        self.assertTrue(self.c.is_resource_permanently_acquired(AUDIO_CAPTURE))
        with self.assertRaises(Exception) as cm:
            self.c.register(
                "other",
                self._handlers("other"),
                permanent_resources=(AUDIO_CAPTURE,),
            )
        self.assertIn("already has permanent module", str(cm.exception))
        self.assertIn("first registered wins", str(cm.exception))
        # First claimant still permanent; second never registered handlers
        self.assertEqual(
            self.c.resources[AUDIO_CAPTURE]["reclaim_module"], "mic"
        )
        self.assertNotIn("other", self.c.handlers)

    def test_waiter_then_release(self):
        self.c.register("a", self._handlers("a"))
        self.c.register("b", self._handlers("b"))
        s1 = make_session("a", AUDIO_PLAYBACK)
        s2 = make_session("b", AUDIO_PLAYBACK)
        self.c.acquire(s1)
        self.c.acquire(s2)
        self.assertEqual(self.c.resources[AUDIO_PLAYBACK]["holder"], "a")
        self.assertTrue(
            any(e[0] == "revoke_requested" and e[1] == "a" for e in self.events)
        )
        self.c.release(s1)
        self.assertEqual(self.c.resources[AUDIO_PLAYBACK]["holder"], "b")
        grants = [e for e in self.events if e[0] == "granted"]
        self.assertEqual(grants[-1][1], "b")

    def test_deny_higher_priority(self):
        self.c.register("high", self._handlers("high"))
        self.c.register("low", self._handlers("low"))
        s_high = make_session(
            "high", AUDIO_PLAYBACK, priority=ResourcePriority.HIGH
        )
        s_low = make_session(
            "low", AUDIO_PLAYBACK, priority=ResourcePriority.NORMAL
        )
        self.c.acquire(s_high)
        self.c.acquire(s_low)
        denied = [e for e in self.events if e[0] == "denied"]
        self.assertTrue(denied)
        self.assertEqual(denied[-1][3], ResourceDenyReason.HIGHER_PRIORITY)
        self.assertEqual(self.c.resources[AUDIO_PLAYBACK]["holder"], "high")

    def test_steal_after_timeout(self):
        self.c.register("a", self._handlers("a"))
        self.c.register("b", self._handlers("b"))
        s1 = make_session("a", AUDIO_PLAYBACK, timeout_s=1.0)
        s2 = make_session("b", AUDIO_PLAYBACK, timeout_s=1.0)
        self.c.acquire(s1)
        self.c.acquire(s2)
        self.assertEqual(self.c.resources[AUDIO_PLAYBACK]["holder"], "a")
        self.assertTrue(self.tf.timers)
        self.tf.timers[-1].fire()
        self.assertEqual(self.c.resources[AUDIO_PLAYBACK]["holder"], "b")
        revoked = [e for e in self.events if e[0] == "revoked"]
        self.assertTrue(revoked)
        self.assertTrue(revoked[-1][3])

    def test_multi_resource_atomic(self):
        self.c.register("voice", self._handlers("voice"))
        self.c.register("music", self._handlers("music"))
        music = make_session("music", AUDIO_PLAYBACK)
        self.c.acquire(music)
        voice = make_session(
            "voice",
            (AUDIO_PLAYBACK, AUDIO_CAPTURE),
            priority=ResourcePriority.HIGH,
        )
        self.c.acquire(voice)
        self.assertEqual(self.c.resources[AUDIO_PLAYBACK]["holder"], "music")
        self.c.release(music)
        self.assertEqual(self.c.resources[AUDIO_PLAYBACK]["holder"], "voice")
        self.assertEqual(self.c.resources[AUDIO_CAPTURE]["holder"], "voice")

    def test_reclaim_after_idle(self):
        self.c.register(
            "player",
            self._handlers("player"),
            permanent_resources=(AUDIO_PLAYBACK,),
        )
        self.assertEqual(self.c.resources[AUDIO_PLAYBACK]["holder"], "player")
        self.c.register("voice", self._handlers("voice"))
        voice = make_session(
            "voice", AUDIO_PLAYBACK, priority=ResourcePriority.HIGH
        )
        self.c.acquire(voice)
        # steal so voice gets it
        self.tf.timers[-1].fire()
        self.assertEqual(self.c.resources[AUDIO_PLAYBACK]["holder"], "voice")
        voice_hold = None
        for e in self.events:
            if e[0] == "granted" and e[1] == "voice":
                voice_hold = e[2]
        self.c.release(voice_hold)
        self.assertEqual(self.c.resources[AUDIO_PLAYBACK]["holder"], "player")

    def test_double_acquire_same_module(self):
        self.c.register("a", self._handlers("a"))
        s1 = make_session("a", AUDIO_PLAYBACK)
        self.c.acquire(s1)
        before = len(self.events)
        s2 = make_session("a", AUDIO_PLAYBACK)
        self.c.acquire(s2)
        self.assertEqual(len([e for e in self.events[before:] if e[0] == "granted"]), 0)

    def test_get_status(self):
        self.c.register("a", self._handlers("a"))
        self.c.acquire(make_session("a", AUDIO_PLAYBACK))
        status = self.c.get_status()
        self.assertEqual(status[AUDIO_PLAYBACK]["holder"], "a")

    def test_legacy_register_acquire_release(self):
        acquired = []
        need = []
        self.c.register_resource(
            "test", AUDIO_PLAYBACK, acquired.append, need.append, False
        )
        self.c.acquire_resource("test", AUDIO_PLAYBACK)
        self.assertEqual(self.c.resources[AUDIO_PLAYBACK]["holder"], "test")
        self.assertEqual(acquired, [AUDIO_PLAYBACK])
        self.assertTrue(self.c.release_resource("test", AUDIO_PLAYBACK))
        self.assertIsNone(self.c.resources[AUDIO_PLAYBACK]["holder"])

    def test_legacy_permanent_conflict(self):
        self.c.register_resource(
            "test1", AUDIO_CAPTURE, Mock(), Mock(), True
        )
        with self.assertRaises(Exception):
            self.c.register_resource(
                "test2", AUDIO_CAPTURE, Mock(), Mock(), True
            )

    def test_legacy_acquire_unknown(self):
        self.c.register_resource("test", AUDIO_PLAYBACK, Mock(), Mock())
        with self.assertRaises(Exception):
            self.c.acquire_resource("test", "a.resource")

    def test_legacy_acquire_unregistered(self):
        with self.assertRaises(Exception):
            self.c.acquire_resource("test", AUDIO_CAPTURE)

    def test_release_not_holder(self):
        self.c.register("a", self._handlers("a"))
        self.c.register("b", self._handlers("b"))
        self.c.acquire(make_session("a", AUDIO_PLAYBACK))
        self.assertFalse(self.c.release_by_module("b", AUDIO_PLAYBACK))

    def test_crash_report_on_dispatch_error(self):
        crash = Mock()
        self.c.set_crash_report(crash)

        def boom(session):
            raise RuntimeError("boom")

        self.c.register(
            "a",
            {
                "on_granted": boom,
                "on_revoke_requested": Mock(),
                "on_revoked": Mock(),
                "on_denied": Mock(),
            },
        )
        # SyncTaskFactory runs inline — exception is caught in _dispatch
        # Override create_task to raise on start
        def bad_create_task(interval, task, task_args=None, task_kwargs=None, end_callback=None):
            mock = Mock()
            mock.start.side_effect = Exception("fail start")
            return mock

        self.tf.create_task = bad_create_task
        self.c.acquire(make_session("a", AUDIO_PLAYBACK))
        self.assertTrue(crash.report_exception.called)


class CriticalResourcesRealTaskFactoryTests(unittest.TestCase):
    """Smoke test with real TaskFactory (async callbacks)."""

    def setUp(self):
        TestLib()
        self.app_stop = Event()
        self.tf = TaskFactory({"app_stop_event": self.app_stop})
        self.c = CriticalResources({"task_factory": self.tf}, False)

    def tearDown(self):
        self.app_stop.set()

    def test_acquire_async(self):
        granted = []

        def on_granted(session):
            granted.append(session)

        self.c.register(
            "a",
            {
                "on_granted": on_granted,
                "on_revoke_requested": Mock(),
                "on_revoked": Mock(),
                "on_denied": Mock(),
            },
        )
        self.c.acquire(make_session("a", AUDIO_PLAYBACK))
        deadline = time.time() + 2
        while not granted and time.time() < deadline:
            time.sleep(0.05)
        self.assertTrue(granted)
        self.assertEqual(self.c.resources[AUDIO_PLAYBACK]["holder"], "a")


if __name__ == "__main__":
    unittest.main()
