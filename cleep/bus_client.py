#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bus client: one worker thread per module, dispatching commands and events from MessageBus.
"""

from __future__ import annotations

import inspect
import logging
import threading
from collections.abc import Callable
from threading import Event
from typing import TYPE_CHECKING, Any, Protocol, TypedDict

from cleep.common import MessageRequest, MessageResponse
from cleep.exception import (
    CommandError,
    CommandInfo,
    InvalidParameter,
    NoMessageAvailable,
)

if TYPE_CHECKING:
    from cleep.message_bus import BusEnvelope, MessageBus

__all__ = ["BusClient"]

# How long the module loop waits for the next bus message before re-running _on_process
_PULL_LOOP_TIMEOUT = 1.0

ManualResponseCallback = Callable[[MessageResponse], None]
CommandHandler = Callable[..., Any]
EventPayload = dict[str, Any]


class CrashReportLike(Protocol):
    def report_exception(self, data: dict[str, Any]) -> Any: ...


class TaskLike(Protocol):
    def start(self) -> Any: ...


class TaskFactoryLike(Protocol):
    def create_task(
        self,
        interval: float | None,
        task: Any,
        task_args: Any = None,
        task_kwargs: Any = None,
        end_callback: Any = None,
    ) -> TaskLike: ...


class BusClientBootstrap(TypedDict):
    internal_bus: MessageBus
    crash_report: CrashReportLike
    module_join_event: Event
    core_join_event: Event
    task_factory: TaskFactoryLike


class BusClient(threading.Thread):
    """
    Base class for modules that consume the internal MessageBus.

    Reads messages from the module queue, executes named commands, and returns
    responses to the originator. Events are forwarded to :meth:`_on_event`.
    """

    CORE_SYNC_TIMEOUT = 60.0

    PARAM_COMMAND_SENDER = "command_sender"
    # If present on the handler signature, the bus will not auto-ack; the handler
    # must call the injected callback or the caller will time out.
    PARAM_MANUAL_RESPONSE = "manual_response"

    def __init__(self, module_name: str, bootstrap: BusClientBootstrap) -> None:
        """
        Args:
            module_name: module name
            bootstrap: bootstrap objects
        """
        threading.Thread.__init__(
            self,
            daemon=True,
            name=f"module-{module_name.lower()}",
        )

        self.logger = logging.getLogger(self.__class__.__name__)
        self.__continue = True
        self.__bus: MessageBus = bootstrap["internal_bus"]
        self.__bootstrap_crash_report: CrashReportLike = bootstrap["crash_report"]
        self.__module_name = module_name.lower()
        self.__module_join_event: Event = bootstrap["module_join_event"]
        self.__module_join_event.clear()
        self.__core_join_event: Event = bootstrap["core_join_event"]
        self.__on_start_event = Event()
        self.__task_factory: TaskFactoryLike = bootstrap["task_factory"]

        self.__bus.add_subscription(self.__module_name)

    def stop(self) -> None:
        """Stop the module thread."""
        self.__continue = False

    def __get_crash_report(self) -> CrashReportLike:
        crash_report = getattr(self, "crash_report", None)
        return crash_report if crash_report else self.__bootstrap_crash_report

    def __check_command_parameters(
        self,
        function: CommandHandler,
        message: dict[str, Any] | None,
        sender: str,
        bus_message: BusEnvelope | None = None,
    ) -> tuple[bool, dict[str, Any] | None]:
        """
        Bind command parameters to the handler signature.

        Returns:
            (ok, args) — args is None when parameters are invalid
        """
        args: dict[str, Any] = {}
        params_with_default: list[str] = []

        func_signature = inspect.signature(function)

        for param in func_signature.parameters:
            if func_signature.parameters[param].default != func_signature.empty:
                params_with_default.append(param)

        for param in func_signature.parameters:
            if param == "self":  # pragma: no cover
                continue
            if param == BusClient.PARAM_COMMAND_SENDER:
                args[BusClient.PARAM_COMMAND_SENDER] = sender
            elif param == BusClient.PARAM_MANUAL_RESPONSE:

                def manual_response(
                    response: MessageResponse,
                    bus_message: BusEnvelope | None = bus_message,
                ) -> None:
                    if bus_message is None or bus_message.get("cancelled"):
                        return
                    bus_message["response"] = response
                    if bus_message["event"]:
                        bus_message["event"].set()

                args[BusClient.PARAM_MANUAL_RESPONSE] = (
                    manual_response if bus_message else None
                )
                if bus_message is not None:
                    bus_message["auto_response"] = (
                        args[BusClient.PARAM_MANUAL_RESPONSE] is None
                    )
            elif (
                isinstance(message, dict)
                and param not in message
                and param not in params_with_default
            ):
                return False, None
            else:
                if isinstance(message, dict) and param in message:
                    args[param] = message[param]

        return True, args

    def _get_module_name(self) -> str:
        return self.__module_name

    def push(
        self, request: MessageRequest, timeout: float | None = 3.0
    ) -> MessageResponse:
        """
        Push a message to the bus and wait for a response when applicable.

        Raises:
            InvalidParameter: if request is not a MessageRequest, or self-push
        """
        if not isinstance(request, MessageRequest):
            raise InvalidParameter("Request parameter must be MessageRequest instance")

        request.sender = self.__module_name

        if request.to is not None and request.to == self.__module_name:
            raise Exception("Unable to send message to same module")

        response = MessageResponse()
        try:
            if request.is_broadcast() or not timeout:
                self.__bus.push(request, timeout)
                if request.is_broadcast():
                    response.broadcast = True
            else:
                response.fill_from_response(self.__bus.push(request, timeout))

        except Exception as error:
            self.logger.exception("Error occured while pushing message to bus")
            response.error = True
            response.message = str(error)

        return response

    def send_event(
        self,
        event: str,
        params: dict[str, Any] | None = None,
        device_id: str | None = None,
        to: str | None = None,
    ) -> MessageResponse:
        """Helper to push an event (no response awaited)."""
        request = MessageRequest()
        request.to = to
        request.event = event
        request.device_id = device_id
        request.params = params
        return self.push(request, None)

    def send_event_from_request(self, request: MessageRequest) -> MessageResponse:
        if not isinstance(request, MessageRequest):
            raise Exception('Parameter "request" must be MessageRequest instance')
        return self.push(request, None)

    def __execute_command(
        self, command: str, params: dict[str, Any] | None = None
    ) -> MessageResponse:
        """Execute a command on this module without going through the bus."""
        resp = MessageResponse()
        try:
            module_function: CommandHandler = getattr(self, command)
            if module_function is not None:
                (params_ok, args) = self.__check_command_parameters(
                    module_function, params, self.__module_name
                )
                if params_ok and args is not None:
                    try:
                        resp.data = module_function(**args)
                    except Exception as error:
                        self.logger.exception(
                            "Exception during send_command in the same module:"
                        )
                        resp.error = True
                        resp.message = str(error)
                else:
                    self.logger.error(
                        'Some command "%s" parameters are missing: %s', command, params
                    )
                    resp.error = True
                    resp.message = "Some command parameters are missing"

        except AttributeError:
            self.logger.exception(
                'Command "%s" doesn\'t exist in "%s" module',
                command,
                self.__module_name,
            )
            resp.error = True
            resp.message = (
                f'Command "{command}" doesn\'t exist in "{self.__module_name}" module'
            )

        except Exception:
            self.logger.exception("Internal error:")
            resp.error = True
            resp.message = "Internal error"

        return resp

    def send_command(
        self,
        command: str,
        to: str | None,
        params: dict[str, Any] | None = None,
        timeout: float | None = 3.0,
    ) -> MessageResponse:
        """
        Push a command to another module (or execute locally if `to` is self).
        """
        if to == self.__module_name:
            return self.__execute_command(command, params)

        request = MessageRequest()
        request.to = to
        request.command = command
        request.params = params
        return self.push(request, timeout)

    def send_command_from_request(
        self, request: MessageRequest, timeout: float | None = 3.0
    ) -> MessageResponse:
        if not isinstance(request, MessageRequest):
            raise Exception('Parameter "request" must be MessageRequest instance')

        if request.to == self.__module_name:
            return self.__execute_command(request.command, request.params)
        return self.push(request, timeout)

    def _on_process(self) -> None:
        """
        Called on each loop before pulling a message.

        Must stay non-blocking / short or the module becomes unresponsive.
        """
        pass

    def _configure(self) -> None:
        """Called once at thread start before modules sync. Prefer short work."""
        pass

    def _on_start(self) -> None:
        """Called once after all modules are configured (async)."""
        pass

    def _on_stop(self) -> None:
        """Called once when the module stops."""
        pass

    def _on_event(self, event: EventPayload) -> None:  # pragma: no cover
        """
        Handle an event message.

        Args:
            event: MessageRequest as dict
        """
        pass

    def __started_callback(self) -> None:
        self.__on_start_event.set()

    def _wait_is_started(self) -> None:
        """Block until `_on_start` has finished."""
        self.__on_start_event.wait()

    def _reply(self, msg: BusEnvelope, resp: MessageResponse) -> None:
        """Deliver auto-response if the caller is still waiting."""
        if msg.get("cancelled"):
            return
        if msg["event"] and (
            msg["auto_response"] or (not msg["auto_response"] and resp.error)
        ):
            msg["response"] = resp
            msg["event"].set()

    def run(self) -> None:
        """
        Module lifecycle: configure → sync → async start → message loop → stop.
        """
        self.logger.trace("BusClient %s started", self.__module_name)

        try:
            self._configure()
        except Exception:
            self.__continue = False
            self.logger.exception(
                'Exception during module "%s" configuration:', self.__module_name
            )
            self.__get_crash_report().report_exception(
                {
                    "message": f'Exception during module "{self.__module_name}" configuration',
                    "module": self.__module_name,
                }
            )
        except KeyboardInterrupt:  # pragma: no cover
            self.stop()
        finally:
            self.__module_join_event.set()

        self.__core_join_event.wait(self.CORE_SYNC_TIMEOUT)

        start_task = self.__task_factory.create_task(
            None, self._on_start, end_callback=self.__started_callback
        )
        start_task.start()

        while self.__continue:
            try:
                try:
                    self._on_process()
                except Exception as error:
                    self.logger.exception(
                        "Critical error occured in on_process: %s", str(error)
                    )
                    self.__get_crash_report().report_exception(
                        {
                            "message": f"Critical error occured in on_process: {str(error)}",
                            "module": self.__module_name,
                        }
                    )

                try:
                    msg = self.__bus.pull(self.__module_name, timeout=_PULL_LOOP_TIMEOUT)
                except NoMessageAvailable:
                    continue

                # Timed-out callers leave cancelled envelopes; do not execute them
                if msg.get("cancelled"):
                    self.logger.trace(
                        'Dropping cancelled message for "%s": %s',
                        self.__module_name,
                        msg.get("message"),
                    )
                    continue

                resp = MessageResponse()

                if msg and "message" in msg:
                    if "command" in msg["message"]:
                        self._handle_command(msg, resp)
                    elif "event" in msg["message"]:
                        self._handle_event(msg)
                else:  # pragma: no cover
                    self.logger.warning(
                        "Received message is malformed, message dropped: %s", msg
                    )

            except KeyboardInterrupt:  # pragma: no cover
                break

            except Exception:  # pragma: no cover
                self.logger.exception(
                    'Fatal exception occured running module "%s":', self.__module_name
                )
                self.__get_crash_report().report_exception(
                    {
                        "message": "Fatal exception occured running module",
                        "module": self.__module_name,
                    }
                )
                self.stop()

        try:
            self._on_stop()
        except Exception:
            self.logger.exception(
                'Fatal exception occured stopping module "%s":', self.__module_name
            )
            self.__get_crash_report().report_exception(
                {
                    "message": "Fatal exception occured stopping module",
                    "module": self.__module_name,
                }
            )

        self.__bus.remove_subscription(self.__module_name)
        self.logger.trace("BusClient %s stopped", self.__module_name)

    def _handle_command(self, msg: BusEnvelope, resp: MessageResponse) -> None:
        command_name = msg["message"].get("command")
        if not command_name:
            self.logger.error("No command specified in message %s", msg["message"])
            resp.error = True
            resp.message = "No command specified in message"
            self._reply(msg, resp)
            return

        try:
            command: CommandHandler = getattr(self, command_name)
            self.logger.debug(
                'Module "%s" received command "%s" from "%s" with params: %s',
                self.__module_name,
                command_name,
                msg["message"]["sender"],
                msg["message"]["params"],
            )

            if command is not None:
                (params_ok, args) = self.__check_command_parameters(
                    command,
                    msg["message"]["params"],
                    msg["message"]["sender"],
                    msg,
                )

                if params_ok and args is not None:
                    try:
                        resp.data = command(**args)
                    except CommandError as error:
                        self.logger.error("Command error: %s", str(error))
                        resp.error = True
                        resp.message = str(error)
                    except CommandInfo as error:
                        resp.error = False
                        resp.message = str(error)
                    except Exception as error:
                        self.logger.exception(
                            'Exception running command "%s" on module "%s"',
                            command_name,
                            self.__module_name,
                        )
                        resp.error = True
                        resp.message = str(error)
                else:
                    self.logger.error(
                        'Some "%s" command parameters are missing: %s',
                        command_name,
                        msg["message"]["params"],
                    )
                    resp.error = True
                    resp.message = "Some command parameters are missing"

        except AttributeError:
            if not msg["message"].get("broadcast"):
                self.logger.exception(
                    'Command "%s" doesn\'t exist in "%s" module',
                    command_name,
                    self.__module_name,
                )
                resp.error = True
                resp.message = (
                    f'Command "{command_name}" doesn\'t exist in '
                    f'"{self.__module_name}" module'
                )

        except Exception:  # pragma: no cover
            self.logger.exception("Command is malformed:")
            resp.error = True
            resp.message = "Received command was malformed"

        self._reply(msg, resp)

    def _handle_event(self, msg: BusEnvelope) -> None:
        self.logger.debug(
            '%s received event "%s" from "%s" with params: %s',
            self.__module_name,
            msg["message"]["event"],
            msg["message"]["sender"],
            msg["message"]["params"],
        )
        if msg["message"].get("sender") == self.__module_name:  # pragma: no cover
            self.logger.trace("Do not process event from same module")
            return

        try:
            self._on_event(msg["message"])
        except Exception:
            self.logger.exception(
                'Exception during on_event call, handled by "%s" module:',
                self.__module_name,
            )
