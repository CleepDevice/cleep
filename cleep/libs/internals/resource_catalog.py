#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Critical resources catalogue and shared types.

Contract
--------
Critical resources are a **cooperative, in-process arbitrator** between Cleep
applications that register with :class:`CriticalResources`.

What it guarantees:

* At most one Cleep module "holds" a named resource at a time (logical lock).
* Waiters are ordered by priority then FIFO.
* Holders are asked to release (``revoke_requested``); after a timeout the
  arbitrator may **steal** the logical hold (``revoked`` with ``forced=True``).
* A module may declare ``permanent: True`` on a resource: it holds it at
  BACKGROUND priority, yields when asked, and reclaims it when idle.
  **At most one permanent module per resource** (first registered wins).

What it does **not** guarantee:

* Exclusive access at the OS / driver level (ALSA, V4L2, serial, …). Any
  process that talks to the device without going through this API bypasses it.
* Stopping hardware I/O on steal — apps must stop capture/playback themselves
  when they receive revoke callbacks.

Resource names live in this catalogue. Add new constants here when introducing
a new exclusive peripheral (camera, radio stick, …).

ReSpeaker remigration notes
---------------------------
Typical pattern for a wake / listen window:

1. Register ``audio.capture`` with ``permanent: True`` (always-on mic listen).
2. On keyword: ``acquire([AUDIO_CAPTURE, AUDIO_PLAYBACK], priority=HIGH)`` so
   playback holders (music) get ``revoke_requested`` and can pause.
3. After the command window: ``release(session)`` so the permanent holder /
   waiters resume.

Conflict: if another app already claimed permanent on ``audio.capture``, the
second claim is refused (log + on-demand only for that app).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
import uuid
from typing import Sequence


AUDIO_PLAYBACK = "audio.playback"
AUDIO_CAPTURE = "audio.capture"

KNOWN_RESOURCES: tuple[str, ...] = (
    AUDIO_PLAYBACK,
    AUDIO_CAPTURE,
)


class ResourcePriority(IntEnum):
    """Acquire priority. Higher values preempt lower holders after handshake."""

    BACKGROUND = 0
    NORMAL = 10
    HIGH = 20


class ResourceDenyReason:
    """Reasons passed to ``on_denied``."""

    HIGHER_PRIORITY = "higher_priority"
    UNKNOWN_RESOURCE = "unknown_resource"
    NOT_REGISTERED = "not_registered"


DEFAULT_ACQUIRE_TIMEOUT_S = 2.5


@dataclass
class ResourceSession:
    """
    One acquisition attempt for one or more resource names (atomic group).

    Attributes:
        module_name (str): Cleep ``MODULE_NAME`` of the requester
        resource_names (tuple): catalogue names to hold together
        priority (ResourcePriority): preemption rank
        timeout_s (float): seconds before forced steal after revoke request
        session_id (str): unique id for this session
    """

    module_name: str
    resource_names: tuple[str, ...]
    priority: ResourcePriority = ResourcePriority.NORMAL
    timeout_s: float = DEFAULT_ACQUIRE_TIMEOUT_S
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        names = tuple(self.resource_names)
        if isinstance(self.resource_names, str):
            names = (self.resource_names,)
        elif not isinstance(self.resource_names, tuple):
            names = tuple(self.resource_names)
        object.__setattr__(self, "resource_names", names)
        if not self.resource_names:
            raise ValueError("ResourceSession requires at least one resource name")
        if not isinstance(self.priority, ResourcePriority):
            object.__setattr__(self, "priority", ResourcePriority(int(self.priority)))


def make_session(
    module_name: str,
    resource_names: str | Sequence[str],
    priority: ResourcePriority = ResourcePriority.NORMAL,
    timeout_s: float = DEFAULT_ACQUIRE_TIMEOUT_S,
) -> ResourceSession:
    """Helper to build a :class:`ResourceSession`."""
    if isinstance(resource_names, str):
        names = (resource_names,)
    else:
        names = tuple(resource_names)
    return ResourceSession(
        module_name=module_name,
        resource_names=names,
        priority=priority,
        timeout_s=timeout_s,
    )
