#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
In-process message bus: waitable per-subscriber queues, directed RPC and broadcast.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from queue import Empty, Full, Queue
from threading import Event
from typing import Any, Dict, Protocol, Union

import uptime

from cleep.common import MessageRequest, MessageResponse
from cleep.exception import (
    BusError,
    InvalidModule,
    InvalidParameter,
    NoMessageAvailable,
    NoResponse,
    NotReady,
)

__all__ = ["BusEnvelope", "MessageBus"]

# Response stored on an envelope / returned by push after a wait.
# Production BusClient sets MessageResponse; some tests still store a dict.
BusResponse = Union[MessageResponse, Dict[str, Any]]
RequestDict = Dict[str, Any]


class CrashReportLike(Protocol):
    def report_exception(self, data: dict[str, Any]) -> Any: ...


class TaskLike(Protocol):
    def start(self) -> Any: ...
    def stop(self) -> Any: ...


class TaskFactoryLike(Protocol):
    def create_task(
        self,
        interval: float | None,
        task: Any,
        task_args: Any = None,
        task_kwargs: Any = None,
        end_callback: Any = None,
    ) -> TaskLike: ...


@dataclass
class BusEnvelope:
    """
    Internal queue envelope (not a public DTO).

    Supports dict-like access so existing consumers (BusClient, tests) keep working.
    """

    message: RequestDict
    event: Event | None = None
    response: BusResponse | None = None
    auto_response: bool = True
    cancelled: bool = False

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class MessageBus:
    """
    Process-local message bus.

    Directed messages (`request.to` = module name) wait for a response until timeout.
    `to='rpc'` fans out to frontend long-poll subscriptions.
    `to=None` broadcasts to all module queues and RPC clients (no response).

    Messages can only be pushed after :meth:`app_configured` (raises :class:`NotReady` before).
    """

    QUEUE_MAX_LEN = 100
    SUBSCRIPTION_LIFETIME = 600  # seconds (RPC clients only)
    PURGE_SUBSCRIPTIONS_DELAY = 120  # seconds

    def __init__(self, crash_report: CrashReportLike, debug_enabled: bool) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)

        self.crash_report = crash_report
        self.__stopped = False
        self.__app_configured = False
        self.__purge: TaskLike | None = None
        self.overflow_count = 0

        self._queues: dict[str, Queue[BusEnvelope]] = {}
        self._rpc_queues: dict[str, Queue[BusEnvelope]] = {}
        self.__activities: dict[str, int] = {}

    def stop(self) -> None:
        """Stop the bus and drain all queues, releasing waiters."""
        self.__stopped = True
        self._drain_all_queues()
        if self.__purge:
            self.__purge.stop()

    def _is_app_stopped(self) -> bool:
        return self.__stopped

    def app_configured(self, task_factory: TaskFactoryLike) -> None:
        """
        Mark application ready so messages can be pushed, and start RPC purge task.

        Args:
            task_factory: task factory instance
        """
        self.__app_configured = True
        self.__purge = task_factory.create_task(
            self.PURGE_SUBSCRIPTIONS_DELAY, self.purge_subscriptions
        )
        self.__purge.start()

    def push(
        self, request: MessageRequest, timeout: float | None = 3.0
    ) -> BusResponse:
        """
        Push a message and optionally wait for a response.

        Args:
            request: message to push
            timeout: seconds to wait for response; falsy means fire-and-forget

        Returns:
            MessageResponse (or dict in some test helpers) when a response is awaited;
            empty MessageResponse otherwise

        Raises:
            BusError: bus stopped or recipient queue full (directed)
            InvalidParameter: bad request or self-push
            NoResponse: directed command timed out
            InvalidModule: unknown recipient
            NotReady: push before app_configured
        """
        if self.__stopped:
            raise BusError("Bus stopped")
        if not self.__app_configured:
            raise NotReady(
                "Pushing messages to internal bus is possible only when application is running. "
                "If this message appears during Cleep startup it means you try to send a message from module "
                "constructor or _configure method, if that is the case prefer using _on_start method."
            )
        if not isinstance(request, MessageRequest):
            raise InvalidParameter('Parameter "request" must be MessageRequest instance')

        if (
            request.to is not None
            and request.sender is not None
            and request.to.lower() == request.sender.lower()
        ):
            raise InvalidParameter("Unable to send message to same module")

        request_dict = request.to_dict()
        self.logger.trace(
            'Received message %s to push to "%s" module with timeout %s',
            request_dict,
            request.to,
            timeout,
        )

        if request.to is not None and request.to.lower() in self._queues:
            return self._push_to_recipient(request, request_dict, timeout)
        if request.to == "rpc":
            return self._fanout_rpc(request_dict)
        if request.to is None:
            return self._push_broadcast(request, request_dict)

        raise InvalidModule(request.to)

    def _make_envelope(
        self, request_dict: RequestDict, wait_response: bool
    ) -> BusEnvelope:
        return BusEnvelope(
            message=request_dict,
            event=Event() if wait_response else None,
            response=None,
            auto_response=True,
            cancelled=False,
        )

    def _enqueue(
        self, queue: Queue[BusEnvelope], envelope: BusEnvelope, name: str
    ) -> bool:
        try:
            queue.put_nowait(envelope)
            return True
        except Full:
            self.overflow_count += 1
            self.logger.warning(
                'Queue full for "%s" (overflow_count=%s), dropping message',
                name,
                self.overflow_count,
            )
            return False

    def _touch_activity(self, name: str) -> None:
        self.__activities[name] = int(uptime.uptime())

    def _push_to_recipient(
        self,
        request: MessageRequest,
        request_dict: RequestDict,
        timeout: float | None,
    ) -> BusResponse:
        recipient = request.to.lower()
        wait_response = bool(timeout)
        envelope = self._make_envelope(request_dict, wait_response)

        self._touch_activity(recipient)

        if not self._enqueue(self._queues[recipient], envelope, recipient):
            raise BusError(f'Queue full for module "{request.to}"')

        if not wait_response:
            return MessageResponse()

        assert envelope.event is not None
        self.logger.trace("Push wait for response (%s seconds)...", timeout)
        if envelope.event.wait(timeout):
            self.logger.debug("Response received %s", envelope.response)
            return envelope.response if envelope.response is not None else MessageResponse()

        envelope.cancelled = True
        self.logger.debug("Command has timed out")
        raise NoResponse(request.to, timeout, request_dict)

    def _fanout_rpc(self, request_dict: RequestDict) -> MessageResponse:
        envelope = self._make_envelope(request_dict, wait_response=False)
        self.logger.debug("Broadcast to RPC clients message %s", envelope)

        for name, queue in list(self._rpc_queues.items()):
            self._enqueue(queue, envelope, name)

        return MessageResponse()

    def _push_broadcast(
        self, request: MessageRequest, request_dict: RequestDict
    ) -> MessageResponse:
        envelope = self._make_envelope(request_dict, wait_response=False)
        self.logger.debug("Broadcast message %s", envelope)

        sender = (request.sender or "").lower()
        for name, queue in list(self._queues.items()):
            if name == sender:
                continue
            self._enqueue(queue, envelope, name)

        # Preserve historical behavior: broadcasts also reach long-poll UI clients
        for name, queue in list(self._rpc_queues.items()):
            self._enqueue(queue, envelope, name)

        return MessageResponse()

    def pull(self, module: str, timeout: float | None = 0.5) -> BusEnvelope:
        """
        Pull the next message for a subscriber.

        Args:
            module: module or rpc-* subscription name
            timeout: seconds to wait; falsy = non-blocking

        Returns:
            BusEnvelope

        Raises:
            InvalidModule, BusError, NoMessageAvailable
        """
        module_lc = module.lower()
        queue = self._get_queue(module_lc)
        if queue is None:
            self.logger.error("Module %s not found", module_lc)
            raise InvalidModule(module_lc)

        self._touch_activity(module_lc)

        try:
            if not timeout:
                envelope = queue.get_nowait()
            else:
                envelope = queue.get(timeout=timeout)
            self.logger.trace('"%s" pulled: %s', module_lc, envelope)
            return envelope
        except Empty:
            raise NoMessageAvailable()
        except Exception:
            self.logger.exception("Error when pulling message:")
            self.crash_report.report_exception(
                {"message": "Error when pulling message", "module": module}
            )
            raise BusError("Error when pulling message")

    def _get_queue(self, name: str) -> Queue[BusEnvelope] | None:
        if name in self._queues:
            return self._queues[name]
        if name in self._rpc_queues:
            return self._rpc_queues[name]
        return None

    def add_subscription(self, module_name: str) -> None:
        """Add a module or rpc-* subscription queue."""
        name = module_name.lower()
        self.logger.trace('Add subscription for module "%s"', name)
        queue: Queue[BusEnvelope] = Queue(maxsize=self.QUEUE_MAX_LEN)
        if name.startswith("rpc-"):
            self._rpc_queues[name] = queue
        else:
            self._queues[name] = queue
        self._touch_activity(name)

    def remove_subscription(self, module_name: str) -> None:
        """
        Remove an existing subscription.

        Raises:
            InvalidModule: if name is unknown
        """
        name = module_name.lower()
        self.logger.debug('Remove subscription for module "%s"', name)
        if name in self._queues:
            del self._queues[name]
            self.__activities.pop(name, None)
            return
        if name in self._rpc_queues:
            del self._rpc_queues[name]
            self.__activities.pop(name, None)
            return
        self.logger.error('Subscriber "%s" not found', name)
        raise InvalidModule(name)

    def is_subscribed(self, module_name: str) -> bool:
        name = module_name.lower()
        return name in self._queues or name in self._rpc_queues

    def purge_subscriptions(self) -> None:
        """Purge idle RPC long-poll subscriptions only (modules are never auto-purged)."""
        now = int(uptime.uptime())
        for name, last_activity in list(self.__activities.items()):
            if not name.startswith("rpc-"):
                continue
            if now > (last_activity + self.SUBSCRIPTION_LIFETIME):
                self.logger.debug('Remove obsolete RPC subscription "%s"', name)
                try:
                    self.remove_subscription(name)
                except InvalidModule:
                    pass

    def _drain_all_queues(self) -> None:
        for name, queue in list(self._queues.items()) + list(self._rpc_queues.items()):
            while True:
                try:
                    envelope = queue.get_nowait()
                except Empty:
                    break
                except Exception:
                    # Broken/mocked queues must not block shutdown
                    break
                self.logger.debug("Purging %s queue message: %s", name, envelope)
                if envelope.event:
                    envelope.cancelled = True
                    envelope.event.set()
