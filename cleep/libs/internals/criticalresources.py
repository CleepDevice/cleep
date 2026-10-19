#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Critical resources arbitrator (cooperative logical locks between Cleep apps).

See :mod:`cleep.libs.internals.resource_catalog` for the contract and catalogue.
"""

from __future__ import annotations

import logging
from threading import Lock
from typing import Any, Callable

from cleep.libs.internals.resource_catalog import (
    DEFAULT_ACQUIRE_TIMEOUT_S,
    KNOWN_RESOURCES,
    ResourceDenyReason,
    ResourcePriority,
    ResourceSession,
    make_session,
)

HandlerMap = dict[str, Callable[..., Any]]


class CriticalResources:
    """
    Arbitrate named exclusive resources between registered Cleep modules.

    Does not lock OS devices; only coordinates modules that play by the rules.
    """

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap context (needs ``task_factory``)
            debug_enabled (bool): debug enabled flag
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:  # pragma: no cover
            self.logger.setLevel(logging.DEBUG)

        self.task_factory = bootstrap["task_factory"]
        self.__mutex = Lock()
        self.crash_report = None

        # name -> state
        self.resources: dict[str, dict[str, Any]] = {}
        for name in KNOWN_RESOURCES:
            self.resources[name] = self._empty_resource_state()

        # module_name -> handlers
        self.handlers: dict[str, HandlerMap] = {}
        # session_id -> ResourceSession (active hold or waiting)
        self._sessions: dict[str, ResourceSession] = {}
        # requester session_id -> CancelableTimer (steal)
        self._steal_timers: dict[str, Any] = {}
        # FIFO counter for equal-priority waiters
        self._wait_seq = 0

    @staticmethod
    def _empty_resource_state() -> dict[str, Any]:
        return {
            "holder": None,
            "holder_session_id": None,
            "holder_priority": None,
            "wait_queue": [],  # list of (priority, seq, session_id)
            "reclaim_module": None,
        }

    def set_crash_report(self, crash_report):
        """
        Set crash report

        Args:
            crash_report (CrashReport): CrashReport instance
        """
        self.crash_report = crash_report

    def __report_exception(self, *args, **kwargs):
        if self.crash_report:
            self.crash_report.report_exception(args=args, kwargs=kwargs)

    def get_resources(self):
        """
        Returns list of existing resource names

        Returns:
            list: resource names from the catalogue
        """
        return list(self.resources.keys())

    def get_status(self) -> dict[str, Any]:
        """
        Debug snapshot of holders and wait queues.

        Returns:
            dict: per-resource status
        """
        with self.__mutex:
            out = {}
            for name, state in self.resources.items():
                out[name] = {
                    "holder": state["holder"],
                    "holder_session_id": state["holder_session_id"],
                    "holder_priority": (
                        int(state["holder_priority"])
                        if state["holder_priority"] is not None
                        else None
                    ),
                    "waiting": [sid for _, _, sid in state["wait_queue"]],
                    "reclaim_module": state["reclaim_module"],
                }
            return out

    def is_resource_referenced(self, resource_name: str) -> bool:
        """Return True if ``resource_name`` is in the catalogue."""
        return resource_name in self.resources

    def is_resource_permanently_acquired(self, resource_name: str) -> bool:
        """
        Return True if a reclaim module is configured for the resource.

        Args:
            resource_name (str): catalogue name

        Returns:
            bool
        """
        if not self.is_resource_referenced(resource_name):
            raise Exception('Resource "%s" does not exists' % resource_name)
        return self.resources[resource_name]["reclaim_module"] is not None

    def register(
        self,
        module_name: str,
        handlers: HandlerMap,
        permanent_resources: tuple[str, ...] | list[str] = (),
        reclaim_resources: tuple[str, ...] | list[str] | None = None,
    ):
        """
        Register a module and optional permanent resources.

        Only one module may be permanent per resource (first registrant wins).
        A second permanent claim raises; callers may catch and re-register
        without permanent so the app still works on demand.

        Args:
            module_name (str): Cleep MODULE_NAME
            handlers (dict): callbacks ``on_granted``, ``on_revoke_requested``,
                ``on_revoked``, ``on_denied`` (all required callables)
            permanent_resources: catalogue names to hold at BACKGROUND and
                reclaim when idle (former permanent flag)
            reclaim_resources: deprecated alias of ``permanent_resources``

        Raises:
            Exception: unknown resource or permanent already taken by another module
        """
        required = (
            "on_granted",
            "on_revoke_requested",
            "on_revoked",
            "on_denied",
        )
        for key in required:
            if key not in handlers or not callable(handlers[key]):
                raise Exception("Handlers must include callable %s" % key)

        if reclaim_resources is not None:
            permanent_resources = reclaim_resources
        permanent_resources = tuple(permanent_resources)
        for resource_name in permanent_resources:
            if not self.is_resource_referenced(resource_name):
                raise Exception('Resource "%s" does not exists' % resource_name)
            existing = self.resources[resource_name]["reclaim_module"]
            if existing is not None and existing != module_name:
                raise Exception(
                    'Resource "%s" already has permanent module "%s" configured. '
                    "Only one allowed (first registered wins)" % (resource_name, existing)
                )

        self.logger.debug(
            'Registering critical-resources handlers for module "%s" (permanent=%s)',
            module_name,
            permanent_resources,
        )
        self.handlers[module_name] = dict(handlers)

        for resource_name in permanent_resources:
            self.resources[resource_name]["reclaim_module"] = module_name

        if permanent_resources:
            session = make_session(
                module_name,
                permanent_resources,
                priority=ResourcePriority.BACKGROUND,
                timeout_s=DEFAULT_ACQUIRE_TIMEOUT_S,
            )
            self.acquire(session)

    def acquire(self, session: ResourceSession):
        """
        Request acquisition of ``session.resource_names`` (all-or-nothing).

        Args:
            session (ResourceSession): acquisition request
        """
        with self.__mutex:
            self._acquire_locked(session)

    def release(self, session: ResourceSession) -> bool:
        """
        Release resources held by ``session``.

        Args:
            session (ResourceSession): session to release

        Returns:
            bool: True if this session was holding resources
        """
        with self.__mutex:
            return self._release_locked(session)

    def release_by_module(self, module_name: str, resource_name: str | None = None) -> bool:
        """
        Release the active hold for ``module_name`` (optionally one resource).

        Args:
            module_name (str): MODULE_NAME
            resource_name (str|None): if set, only release if that name is in the hold

        Returns:
            bool: True if something was released
        """
        with self.__mutex:
            session = self._find_holder_session(module_name, resource_name)
            if not session:
                self.logger.warning(
                    'Unable to release: module "%s" holds no matching resource',
                    module_name,
                )
                return False
            return self._release_locked(session)

    # --- internal ---------------------------------------------------------

    def _find_holder_session(
        self, module_name: str, resource_name: str | None
    ) -> ResourceSession | None:
        for state in self.resources.values():
            if state["holder"] != module_name:
                continue
            sid = state["holder_session_id"]
            session = self._sessions.get(sid)
            if not session:
                continue
            if resource_name is None or resource_name in session.resource_names:
                return session
        return None

    def _acquire_locked(self, session: ResourceSession):
        for name in session.resource_names:
            if not self.is_resource_referenced(name):
                self._dispatch(session.module_name, "on_denied", session, ResourceDenyReason.UNKNOWN_RESOURCE)
                return

        if session.module_name not in self.handlers:
            self._dispatch(
                session.module_name,
                "on_denied",
                session,
                ResourceDenyReason.NOT_REGISTERED,
            )
            return

        # Already holding exactly these resources
        if self._session_already_holds(session):
            self.logger.debug(
                'Module "%s" already holds %s; drop acquire',
                session.module_name,
                session.resource_names,
            )
            return

        # Higher-priority holder on any name -> deny
        for name in session.resource_names:
            state = self.resources[name]
            if state["holder"] is None:
                continue
            if state["holder"] == session.module_name:
                continue
            if state["holder_priority"] is not None and state[
                "holder_priority"
            ] > session.priority:
                self.logger.debug(
                    'Deny "%s" for %s: held by higher priority "%s"',
                    session.module_name,
                    name,
                    state["holder"],
                )
                self._dispatch(
                    session.module_name,
                    "on_denied",
                    session,
                    ResourceDenyReason.HIGHER_PRIORITY,
                )
                return

        if self._all_free_or_self(session):
            self._grant_locked(session)
            return

        # Queue and ask holders to release
        self._sessions[session.session_id] = session
        holders = set()
        for name in session.resource_names:
            state = self.resources[name]
            if state["holder"] and state["holder"] != session.module_name:
                holders.add(state["holder"])
            self._enqueue_waiter(name, session)

        self.logger.debug(
            'Module "%s" waiting for %s (holders=%s)',
            session.module_name,
            session.resource_names,
            holders,
        )
        for holder in holders:
            self._dispatch(holder, "on_revoke_requested", session)

        self._arm_steal_timer(session)

    def _session_already_holds(self, session: ResourceSession) -> bool:
        for name in session.resource_names:
            state = self.resources[name]
            if state["holder"] != session.module_name:
                return False
        return True

    def _all_free_or_self(self, session: ResourceSession) -> bool:
        for name in session.resource_names:
            state = self.resources[name]
            if state["holder"] is None:
                continue
            if state["holder"] == session.module_name:
                continue
            return False
        return True

    def _enqueue_waiter(self, resource_name: str, session: ResourceSession):
        state = self.resources[resource_name]
        for _, _, sid in state["wait_queue"]:
            if sid == session.session_id:
                return
        self._wait_seq += 1
        state["wait_queue"].append(
            (int(session.priority), self._wait_seq, session.session_id)
        )
        # highest priority first, then lower seq (earlier) among equals
        state["wait_queue"].sort(key=lambda item: (-item[0], item[1]))

    def _grant_locked(self, session: ResourceSession):
        self._cancel_steal_timer(session.session_id)
        self._sessions[session.session_id] = session
        for name in session.resource_names:
            state = self.resources[name]
            # drop from wait queues
            state["wait_queue"] = [
                item for item in state["wait_queue"] if item[2] != session.session_id
            ]
            state["holder"] = session.module_name
            state["holder_session_id"] = session.session_id
            state["holder_priority"] = session.priority
        self.logger.debug(
            'Granted %s to "%s" (session=%s priority=%s)',
            session.resource_names,
            session.module_name,
            session.session_id,
            session.priority,
        )
        self._dispatch(session.module_name, "on_granted", session)

    def _release_locked(self, session: ResourceSession) -> bool:
        held = False
        for name in session.resource_names:
            state = self.resources[name]
            if state["holder_session_id"] == session.session_id:
                held = True
                state["holder"] = None
                state["holder_session_id"] = None
                state["holder_priority"] = None
            # also drop from wait queues
            state["wait_queue"] = [
                item for item in state["wait_queue"] if item[2] != session.session_id
            ]

        self._cancel_steal_timer(session.session_id)
        self._sessions.pop(session.session_id, None)

        if not held:
            self.logger.warning(
                'Session %s did not hold resources %s',
                session.session_id,
                session.resource_names,
            )
            return False

        self.logger.debug(
            'Module "%s" released %s',
            session.module_name,
            session.resource_names,
        )
        self._schedule_next_locked()
        return True

    def _schedule_next_locked(self):
        # Collect candidate waiting sessions (unique), highest priority first
        candidates: dict[str, ResourceSession] = {}
        for state in self.resources.values():
            for _prio, _seq, sid in state["wait_queue"]:
                session = self._sessions.get(sid)
                if session:
                    candidates[sid] = session

        ordered = sorted(
            candidates.values(),
            key=lambda s: (-int(s.priority), s.session_id),
        )
        for session in ordered:
            if self._all_free_or_self(session):
                # remove from all wait queues then grant
                for name in session.resource_names:
                    state = self.resources[name]
                    state["wait_queue"] = [
                        item
                        for item in state["wait_queue"]
                        if item[2] != session.session_id
                    ]
                self._grant_locked(session)
                return

        # Reclaim idle resources
        for name, state in self.resources.items():
            if state["holder"] is not None:
                continue
            reclaim = state["reclaim_module"]
            if not reclaim or reclaim not in self.handlers:
                continue
            if state["wait_queue"]:
                continue
            session = make_session(
                reclaim,
                (name,),
                priority=ResourcePriority.BACKGROUND,
            )
            self._grant_locked(session)

    def _arm_steal_timer(self, session: ResourceSession):
        self._cancel_steal_timer(session.session_id)
        timeout = session.timeout_s if session.timeout_s is not None else DEFAULT_ACQUIRE_TIMEOUT_S
        if timeout <= 0:
            self._steal_locked(session.session_id)
            return
        timer = self.task_factory.create_timer(
            timeout, self._on_steal_timeout, task_args=[session.session_id]
        )
        self._steal_timers[session.session_id] = timer
        timer.start()

    def _cancel_steal_timer(self, session_id: str):
        timer = self._steal_timers.pop(session_id, None)
        if timer is not None:
            try:
                timer.cancel()
            except Exception:  # pragma: no cover
                pass

    def _on_steal_timeout(self, session_id: str):
        with self.__mutex:
            self._steal_locked(session_id)

    def _steal_locked(self, session_id: str):
        session = self._sessions.get(session_id)
        if not session:
            return
        if self._all_free_or_self(session):
            for name in session.resource_names:
                state = self.resources[name]
                state["wait_queue"] = [
                    item for item in state["wait_queue"] if item[2] != session_id
                ]
            self._grant_locked(session)
            return

        # Force revoke current holders of needed resources
        revoked_sessions: dict[str, ResourceSession] = {}
        for name in session.resource_names:
            state = self.resources[name]
            if state["holder"] is None or state["holder"] == session.module_name:
                continue
            holder_sid = state["holder_session_id"]
            holder_session = self._sessions.get(holder_sid)
            if holder_session:
                revoked_sessions[holder_sid] = holder_session
            state["holder"] = None
            state["holder_session_id"] = None
            state["holder_priority"] = None

        for holder_session in revoked_sessions.values():
            self.logger.info(
                'Forced revoke of %s from "%s" for waiter "%s"',
                holder_session.resource_names,
                holder_session.module_name,
                session.module_name,
            )
            self._sessions.pop(holder_session.session_id, None)
            self._dispatch(
                holder_session.module_name, "on_revoked", holder_session, True
            )

        for name in session.resource_names:
            state = self.resources[name]
            state["wait_queue"] = [
                item for item in state["wait_queue"] if item[2] != session_id
            ]
        self._grant_locked(session)

    def _dispatch(self, module_name: str, handler_name: str, *args):
        handlers = self.handlers.get(module_name)
        if not handlers:
            return
        callback = handlers.get(handler_name)
        if not callback:
            return
        try:
            task = self.task_factory.create_task(None, callback, list(args))
            task.start()
        except Exception:
            self.logger.exception(
                'Error dispatching %s to module "%s"', handler_name, module_name
            )
            self.__report_exception(
                {
                    "error": "Error dispatching critical resource callback",
                    "handler": handler_name,
                    "module_name": module_name,
                }
            )

    # --- legacy-compatible thin wrappers (tests / gradual callers) --------

    def register_resource(
        self,
        module_name,
        resource_name,
        acquired_callback,
        need_release_callback,
        permanent=False,
    ):
        """
        Legacy register API (single resource + acquired/need_release callbacks).

        Maps onto :meth:`register` and session handlers.
        """
        if not self.is_resource_referenced(resource_name):
            raise Exception('Resource "%s" does not exists' % resource_name)
        if not callable(acquired_callback) or not callable(need_release_callback):
            raise Exception("Callbacks must be functions")

        def on_granted(session: ResourceSession):
            for name in session.resource_names:
                acquired_callback(name)

        def on_revoke_requested(session: ResourceSession):
            for name in session.resource_names:
                need_release_callback(name)

        def on_revoked(session: ResourceSession, forced: bool = False):
            for name in session.resource_names:
                need_release_callback(name)

        def on_denied(session: ResourceSession, reason: str = ""):
            self.logger.debug(
                'Acquire denied for "%s" (%s): %s',
                module_name,
                session.resource_names,
                reason,
            )

        handlers = {
            "on_granted": on_granted,
            "on_revoke_requested": on_revoke_requested,
            "on_revoked": on_revoked,
            "on_denied": on_denied,
        }

        if permanent:
            other = self.resources[resource_name]["reclaim_module"]
            if other is not None and other != module_name:
                raise Exception(
                    'Resource "%s" already has permanent module "%s" configured. '
                    "Only one allowed" % (resource_name, other)
                )

        # Keep handlers for the module (last register wins for callbacks)
        self.handlers[module_name] = handlers

        if permanent:
            self.resources[resource_name]["reclaim_module"] = module_name
            session = make_session(
                module_name,
                (resource_name,),
                priority=ResourcePriority.BACKGROUND,
            )
            self.acquire(session)

    def acquire_resource(self, module_name, resource_name):
        """Legacy single-resource acquire."""
        if not self.is_resource_referenced(resource_name):
            raise Exception('Resource "%s" does not exists' % resource_name)
        if module_name not in self.handlers:
            raise Exception(
                'Module "%s" try to acquire resource "%s" which it is not registered on'
                % (module_name, resource_name)
            )
        session = make_session(module_name, (resource_name,))
        self.acquire(session)
        return None

    def release_resource(self, module_name, resource_name):
        """Legacy single-resource release."""
        if not self.is_resource_referenced(resource_name):
            raise Exception('Resource "%s" does not exists' % resource_name)
        return self.release_by_module(module_name, resource_name)
