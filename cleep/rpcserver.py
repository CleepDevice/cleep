#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=C0103,W0603
"""
Rpcserver based on long poll example from https://github.com/larsks/pubsub_example

Rpcserver implements:

    * authentication (login, password)
    * HTTP and HTTPS support
    * file upload and download
    * poll requests
    * command requests
    * module configs requests
    * devices list requests

"""

from __future__ import annotations

from contextlib import contextmanager
import copy
import functools
import ipaddress
import json
import logging
import os
import re
import socket
import uuid
from typing import Any

import netifaces
import uptime
from passlib.hash import sha256_crypt
from gevent import pywsgi, pool, sleep
import bottle
from cleep.exception import NoMessageAvailable
from cleep.common import MessageResponse, MessageRequest, CORE_MODULES
from cleep.libs.configs.cleepconf import CleepConf

__all__ = [
    "app",
    "configure",
    "invalidate_config_cache",
    "is_apps_ready",
    "register_gateway_handler",
    "set_apps_ready",
    "start",
    "start_listening",
    "stop",
    "unregister_gateway_handler",
    "wait_forever",
]

# constants
BASE_DIR = "/opt/cleep/"
HTML_DIR = os.path.join(BASE_DIR, "html")
UPLOAD_DIR = "/tmp"
POLL_TIMEOUT = 60
SESSION_TIMEOUT = 900  # 15mins
CLEEP_CACHE: dict[str, Any] | None = None
# Plain HTTP, only reachable by a local process. A tunnel cannot open it.
LOCAL_SOCKET_PATH = "/run/cleep/rpc.sock"
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

# globals
polling = 0
subscribed = False
sessions = {}
auth_accounts = {}
auth_enabled = False
logger = None
debug_enabled = False
app = bottle.app()
server = None
local_socket_server = None
cleep_filesystem = None
inventory = None
bus = None
crash_report = None
cache_enabled = True
# False until inventory join + internal bus app_configured
apps_ready = False

# GET paths that must not be served before apps are ready (need inventory/bus)
_EARLY_BLOCKED_GET_PREFIXES = ("/doc", "/logs", "/download")

# Optional Desktop-only LAN gateway (ngrok tunnel → loopback). See CleepRemoteAccessModule.
_gateway_handler = None


def register_gateway_handler(handler):
    """
    Register the loopback gateway gate/proxy callback.

    Args:
        handler (callable): ``handler(bottle.request) -> bottle.HTTPResponse|None``.
            ``None`` continues normal routing; an ``HTTPResponse`` short-circuits.
    """
    global _gateway_handler
    _gateway_handler = handler


def unregister_gateway_handler(handler=None):
    """
    Clear the gateway handler.

    Args:
        handler (callable|None): if set, clear only when it matches the current handler
    """
    global _gateway_handler
    if handler is None or _gateway_handler is handler:
        _gateway_handler = None


def _prefix_length(mask):
    """
    Prefix length of a netmask.

    Accepts a prefix (``24``), a prefixed mask (``ffff::/64``) and the
    dotted or colon form returned by netifaces (``255.255.255.0``,
    ``ffff:ffff:ffff:ffff::``).

    Args:
        mask (str): netmask

    Returns:
        int: prefix length, or None
    """
    mask = str(mask).split("%", 1)[0]
    if mask.isdigit():
        return int(mask)
    if "/" in mask:
        prefix = mask.rsplit("/", 1)[-1]
        if prefix.isdigit():
            return int(prefix)
        mask = mask.split("/", 1)[0]
    try:
        if ":" in mask:
            bits = int.from_bytes(ipaddress.IPv6Address(mask).packed, "big")
            width = 128
        else:
            bits = int.from_bytes(ipaddress.IPv4Address(mask).packed, "big")
            width = 32
    except ValueError:
        return None
    if bits == 0:
        return 0
    return width - (bits & -bits).bit_length() + 1


def _network_from_address(entry):
    """
    Build the network of one interface address.

    Args:
        entry (dict): netifaces address entry

    Returns:
        ipaddress.IPv4Network or ipaddress.IPv6Network, or None when the entry has no usable mask
    """
    addr = entry.get("addr")
    mask = entry.get("mask") or entry.get("netmask")
    if not addr or not mask:
        return None

    addr = str(addr).split("%", 1)[0]
    prefix = _prefix_length(mask)
    if prefix is None:
        return None
    try:
        if ":" in addr:
            return ipaddress.IPv6Interface(f"{addr}/{prefix}").network
        return ipaddress.IPv4Interface(f"{addr}/{prefix}").network
    except (ValueError, TypeError):
        return None


def _interface_networks():
    """
    Networks currently configured on the device interfaces.

    Returns:
        list: ipaddress networks. Interfaces without a mask are ignored.
    """
    networks = []
    try:
        interfaces = netifaces.interfaces()
    except Exception:
        if logger:
            logger.exception("Unable to list network interfaces")
        return networks

    for interface in interfaces:
        try:
            addresses = netifaces.ifaddresses(interface)
        except Exception:
            if logger:
                logger.exception("Unable to read addresses of %s", interface)
            continue
        for family in (netifaces.AF_INET, netifaces.AF_INET6):
            for entry in addresses.get(family, []):
                network = _network_from_address(entry)
                if network is not None:
                    networks.append(network)
    return networks


def _parse_source_ip(remote_addr):
    """
    Parse the TCP peer address.

    Args:
        remote_addr (str): REMOTE_ADDR value

    Returns:
        ipaddress.IPv4Address or ipaddress.IPv6Address, or None
    """
    if not remote_addr:
        return None
    try:
        ip = ipaddress.ip_address(str(remote_addr).strip().split("%", 1)[0])
    except ValueError:
        return None
    mapped = getattr(ip, "ipv4_mapped", None)
    return mapped or ip


def source_is_on_local_network(remote_addr):
    """
    Return True when the TCP peer is loopback or belongs to a network of this device.

    Args:
        remote_addr (str): REMOTE_ADDR value
    """
    ip = _parse_source_ip(remote_addr)
    if ip is None:
        return False
    if ip.is_loopback:
        return True
    return any(ip in network for network in _interface_networks())


@app.hook("before_request")
def restrict_to_local_network():
    """
    Refuse TCP clients that are not on a network of this device.

    The Unix socket is already local. Loopback stays open for the tunnel agent.
    """
    if bottle.request.environ.get("cleep.local_socket"):
        return
    remote_addr = bottle.request.environ.get("REMOTE_ADDR")
    if source_is_on_local_network(remote_addr):
        return
    if logger:
        logger.warning("Rejected request from %s", remote_addr)
    bottle.abort(403, "Access denied")


@app.hook("before_request")
def _gateway_loopback_gate():
    """
    Desktop-only gateway: ngrok hits Cleep on loopback.

    When a gateway handler is registered, it may require a Desktop token and/or
    reverse-proxy to another LAN peer. LAN clients (non-loopback) are unchanged.
    """
    if bottle.request.environ.get("cleep.local_socket"):
        return
    if _gateway_handler is None:
        return
    remote_addr = bottle.request.environ.get("REMOTE_ADDR")
    ip = _parse_source_ip(remote_addr)
    if ip is None or not ip.is_loopback:
        return
    # Allow unauthenticated health probes on loopback
    path = bottle.request.path or "/"
    if bottle.request.method == "GET" and path == "/health":
        return
    try:
        response = _gateway_handler(bottle.request)
    except Exception:
        if logger:
            logger.exception("Gateway handler failed")
        raise bottle.HTTPResponse(status=502, body="Gateway error")
    if response is not None:
        raise response


def load_auth():
    """
    Load auth and enable auth if necessary
    """
    global auth_accounts, auth_enabled

    try:
        cleep_conf = CleepConf(cleep_filesystem)
        auth_accounts = cleep_conf.get_auth_accounts()
        auth_enabled = cleep_conf.is_auth_enabled() and len(auth_accounts) > 0

        logger.debug("Auth enabled: %s", auth_enabled)
        logger.debug("Auth accounts: %s", list(auth_accounts.keys()))
    except Exception:
        auth_accounts = {}
        auth_enabled = False
        logger.exception("Unable to load auth file. Auth disabled:")


def get_ssl_options(rpc_config):
    """
    Return ssl options if any to pass to http server

    Args:
        rpc_config (dict): rpc configuration::

            {
                host (str): server host
                port (int): server port
                ssl (bool): ssl enabled or not
                ssl_key (str): server SSL key
                ssl_cert (str): server SSL certificate
            }

    Returns:
        dict: ssl options::

            {
                keyfile (str): key filepath
                certfile (str): certificate filepath
            }

    """
    if not rpc_config.get("ssl"):
        return {}

    return {
        "keyfile": rpc_config.get("ssl_key"),
        "certfile": rpc_config.get("ssl_cert"),
        "do_handshake_on_connect": False,  # suppress SSLV3_ALERT_CERTIFICATE_UNKNOWN SSL errors
    }


def configure(rpc_config, bootstrap, inventory_, debug_enabled_):
    """
    Configure rpcserver

    Args:
        rpc_config (dict): server configuration::

            {
                host (str): server host
                port (int): server port
                ssl (bool): ssl enabled or not
                ssl_key (str): server SSL key
                ssl_cert (str): server SSL certificate
            }

        bootstrap (dict): bootstrap objects
        inventory_ (Inventory): Inventory instance
        debug_enabled_ (bool): debug status
    """
    global cleep_filesystem, inventory, bus, logger, crash_report, debug_enabled, server
    global apps_ready

    # configure logger
    logger = logging.getLogger("RpcServer")
    debug_enabled = debug_enabled_
    if debug_enabled_:
        logger.setLevel(logging.DEBUG)
    logger_requests = logging.getLogger("RpcRequests")
    logger_requests.setLevel(logging.WARNING)
    if debug_enabled_:
        logger_requests.setLevel(logging.DEBUG)

    # set members
    cleep_filesystem = bootstrap["cleep_filesystem"]
    bus = bootstrap["internal_bus"]
    inventory = inventory_
    crash_report = bootstrap["crash_report"]
    apps_ready = False

    # load auth
    load_auth()

    # create server
    ssl_options = get_ssl_options(rpc_config)
    protocol = "https" if rpc_config.get("ssl", False) else "http"
    host = rpc_config.get("host", "0.0.0.0")
    port = rpc_config.get("port", 80)
    logger.info("RPC server configured %s://%s:%s", protocol, host, port)
    logger.debug("rpc_config=%s ssl_options=%s", rpc_config, ssl_options)
    workers = pool.Pool(20)
    server = pywsgi.WSGIServer(
        (host, port),
        app,
        log=logger_requests,
        error_log=logger,
        spawn=workers,
        **ssl_options,
    )


def _local_socket_app(environ, start_response):
    """
    Mark requests that arrived on the Unix socket.

    The flag lives in the WSGI environ of this server only. A TCP client
    cannot set it, and a tunnel cannot open the socket.
    """
    environ["cleep.local_socket"] = True
    return app(environ, start_response)


def _start_local_socket():
    """
    Listen on the local Unix socket, in HTTP, with the same Bottle application.
    """
    global local_socket_server

    directory = os.path.dirname(LOCAL_SOCKET_PATH)
    os.makedirs(directory, mode=0o755, exist_ok=True)
    if os.path.exists(LOCAL_SOCKET_PATH):
        os.remove(LOCAL_SOCKET_PATH)

    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        listener.bind(LOCAL_SOCKET_PATH)
        os.chmod(LOCAL_SOCKET_PATH, 0o600)
        listener.listen(50)
        listener.setblocking(False)
    except Exception:
        listener.close()
        raise

    logger.info("Running local RPC socket %s", LOCAL_SOCKET_PATH)
    local_socket_server = pywsgi.WSGIServer(
        listener,
        _local_socket_app,
        log=logging.getLogger("RpcRequests"),
        error_log=logger,
        spawn=pool.Pool(5),
    )
    local_socket_server.start()


def _stop_local_socket():
    """
    Stop the Unix socket server and remove its socket file.
    """
    global local_socket_server

    if not local_socket_server:
        return

    try:
        local_socket_server.close()
        local_socket_server.stop()
    finally:
        local_socket_server = None
        if os.path.exists(LOCAL_SOCKET_PATH):
            try:
                os.remove(LOCAL_SOCKET_PATH)
            except OSError:
                logger.exception("Unable to remove local RPC socket")


def set_cache_control(cache_enabled_):
    """
    Set cache control

    Args:
        cache_enabled_ (bool): True to enable cache
    """
    global cache_enabled
    cache_enabled = cache_enabled_


def set_debug(debug_enabled_):
    """
    Change debug level

    Args:
        debug_enabled_ (bool): True to enable debug
    """
    global debug_enabled

    debug_enabled = debug_enabled_
    if debug_enabled:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.getLogger().getEffectiveLevel())


def is_debug_enabled():
    """
    Return debug status

    Returns:
        bool
    """
    return debug_enabled


def set_apps_ready(ready: bool = True) -> None:
    """
    Mark application modules as ready for RPC that needs the bus/inventory.

    Args:
        ready (bool): True when inventory join is done and the internal bus
            accepts messages (``app_configured``).
    """
    global apps_ready
    apps_ready = bool(ready)
    if logger:
        logger.info("RPC apps_ready=%s", apps_ready)


def is_apps_ready() -> bool:
    """Return whether app-dependent RPC may run."""
    return apps_ready


def _request_allowed_while_starting() -> bool:
    """
    Static UI assets and /health may be served before apps are ready.
    All POST APIs and some GET endpoints stay gated.
    """
    method = bottle.request.method
    path = bottle.request.path or "/"
    if method == "GET" and path == "/health":
        return True
    if method != "GET":
        return False
    for prefix in _EARLY_BLOCKED_GET_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return False
    return True


@app.hook("before_request")
def _enforce_apps_ready():
    """
    Reject app-dependent RPC with 503 while Cleep is still starting.
    """
    if apps_ready:
        return
    if _request_allowed_while_starting():
        return
    raise bottle.HTTPResponse(
        status=503,
        body=json.dumps(
            MessageResponse(
                error=True,
                message="Cleep is starting",
                data={"starting": True},
            ).to_dict()
        ),
        headers={"Content-Type": "application/json"},
    )


def start_listening():
    """
    Start accepting HTTP and local-socket connections (non-blocking).

    Call :func:`set_apps_ready` after inventory join, then :func:`wait_forever`.
    """
    if not server:
        raise RuntimeError("RPC server is not configured")
    logger.debug("Starting RPC server listening")
    _start_local_socket()
    server.start()
    logger.info("RPC server listening (static UI available, apps not ready yet)")


def wait_forever():
    """
    Block until the RPC server is stopped (after :func:`start_listening`).
    """
    try:
        server.serve_forever()

    except KeyboardInterrupt:
        pass

    except OSError:
        logger.fatal("Cleep instance is already running")

    except Exception:
        logger.exception("Fatal error starting rpcserver:")
        if crash_report:
            crash_report.report_exception({"message": "Fatal error starting rpcserver"})

    finally:
        _stop_local_socket()
        if server:
            server.close()
            server.stop()


def start():
    """
    Start RPC server and block (legacy / tests).

    Marks apps ready immediately then listens. Prefer
    :func:`start_listening` + :func:`set_apps_ready` + :func:`wait_forever`
    for boot so the UI can load while modules configure.
    """
    set_apps_ready(True)
    start_listening()
    wait_forever()


def stop():
    """
    Stop RPC server
    """
    global apps_ready
    apps_ready = False
    _stop_local_socket()
    if server:
        server.close()
        server.stop()


def _prune_expired_sessions(now: float | None = None) -> None:
    """Drop expired auth sessions to avoid unbounded growth."""
    if len(sessions) < 64:
        return
    current = now if now is not None else uptime.uptime()
    for key in [k for k, expires in sessions.items() if expires < current]:
        del sessions[key]


def check_auth(account: str, password: str) -> bool:
    """
    Check auth

    Args:
        account: account name
        password: account password
    """
    client_ip = bottle.request.environ.get("REMOTE_ADDR")
    logger.trace("Client ip: %s", client_ip)
    session_key = f"{client_ip}-{account}"
    now = uptime.uptime()
    _prune_expired_sessions(now)

    if session_key in sessions and sessions[session_key] >= now:
        sessions[session_key] = now + SESSION_TIMEOUT
        return True

    if account not in auth_accounts:
        logger.warning('Invalid auth account "%s"', account)
        return False

    try:
        if sha256_crypt.verify(password, auth_accounts[account]):
            sessions[session_key] = now + SESSION_TIMEOUT
            return True

        logger.warning('Invalid password for account "%s"', account)
        return False
    except Exception:
        logger.warning(
            'Password failed for account "%s" from ip "%s"', account, client_ip
        )
        return False


def authenticate():
    """
    Authenticate decorator.

    When authentication is enabled, every TCP request must present Cleep
    basic auth. Requests that arrived on the local Unix socket are trusted.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if bottle.request.environ.get("cleep.local_socket"):
                return func(*args, **kwargs)
            if auth_enabled:
                account, password = bottle.request.auth or (None, None)
                remote_addr = bottle.request.environ.get("REMOTE_ADDR")
                logger.debug("Auth check for account=%s from %s", account, remote_addr)
                if account is None or not check_auth(account, password):
                    err = bottle.HTTPError(401, "Access denied")
                    err.add_header("WWW-Authenticate", 'Basic realm="private"')
                    return err
            return func(*args, **kwargs)

        return wrapper

    return decorator


def invalidate_config_cache() -> None:
    """Drop cached /config snapshot (call after inventory reload / app install)."""
    global CLEEP_CACHE
    CLEEP_CACHE = None
    if logger:
        logger.debug("RPC config cache invalidated")


def _safe_upload_filename(filename: str | None) -> str:
    """Return a safe basename under UPLOAD_DIR (no path traversal)."""
    if not filename:
        raise ValueError("Missing upload filename")
    name = os.path.basename(filename.replace("\\", "/"))
    name = _SAFE_FILENAME_RE.sub("_", name).strip("._")
    if not name:
        raise ValueError("Invalid upload filename")
    return f"{uuid.uuid4().hex[:8]}_{name}"


def _parse_upload_params(forms: dict[str, Any]) -> dict[str, Any]:
    """Build command params from multipart form fields."""
    forms = dict(forms)
    forms.pop("command", None)
    forms.pop("to", None)
    forms.pop("filename", None)
    params_raw = forms.pop("params", None)
    if params_raw is not None:
        if isinstance(params_raw, str):
            try:
                parsed = json.loads(params_raw) if params_raw else {}
            except Exception:
                parsed = {}
            return parsed if isinstance(parsed, dict) else {}
        if isinstance(params_raw, dict):
            return params_raw
        return {}
    return forms


def send_command(command, to, params, timeout=None):
    """
    Send specified command

    Args:
        command (string): command to execute
        to (string): command recipient
        params (dict): command parameters
        timeout (float): set new timeout (default no timeout)

    Returns:
        MessageResponse: command response (None if broadcasted message)
    """
    # prepare and send command
    request = MessageRequest()
    request.command = command
    request.to = to
    request.sender = "rpcserver"
    request.params = params

    if timeout is not None:
        return bus.push(request, timeout)

    return bus.push(request)


def get_events_from_inventory():
    """
    Return used events

    Returns:
        list: list of used events
    """
    return inventory.get_used_events()


def get_renderers_from_inventory():
    """
    Return renderers

    Returns:
        list: list of renderers (see profileformattersbroker.py)
    """
    return inventory.get_renderers()


def get_modules_from_inventory():
    """
    Return configurations for all loaded (installed) modules.

    Market / installable catalog is owned by the update application.
    """
    return inventory.get_modules()


def get_devices_from_inventory():
    """
    Return all devices

    Returns:
        dict: all devices by module
    """
    return inventory.get_devices()


def get_drivers_from_inventory():
    """
    Return referenced drivers

    Returns:
        list: list of drivers
    """
    drivers = []
    for driver_type, data in inventory.get_drivers().items():
        for driver_name, driver in data.items():
            try:
                drivers.append(
                    {
                        "drivername": driver_name,
                        "drivertype": driver_type,
                        "processing": driver.processing(),
                        "installed": driver.is_installed(),
                    }
                )
            except Exception:
                logger.exception('Error getting data for driver "%s"', driver_name)

    return drivers


@app.route("/reloadauth", method="POST")
@authenticate()
def reload_auth():
    """
    Reload auth configuration
    Must be executed after update on auth configuration to reload changes
    """
    load_auth()
    logger.info("Rpc auth configuration reloaded")


@app.route("/upload", method="POST")
@authenticate()
def exec_upload():
    """
    Upload file (POST only)
    Parameters are embedded in POST data

    Args:
        command (string): command
        to (string): command recipient
        params (dict): command parameters

    Returns:
        dict: message response
    """
    path = ""
    try:
        forms = dict(bottle.request.forms or {})
        command = forms.get("command")
        to = forms.get("to")
        params = _parse_upload_params(forms)
        logger.debug("Form content: command=%s to=%s params=%s", command, to, params)

        if command is None or to is None:
            raise Exception("Missing parameters")

        logger.debug("Upload %s", bottle.request.files)
        files = dict(bottle.request.files or {})
        upload = files.get("file")
        if upload is None:
            raise Exception("Missing upload file")

        safe_name = _safe_upload_filename(getattr(upload, "filename", None))
        path = os.path.join(UPLOAD_DIR, safe_name)

        if os.path.exists(path):
            os.remove(path)
            sleep(0.25)

        upload.save(path)
        params["filepath"] = path

        logger.debug("Upload command:%s to:%s params:%s", command, to, params)
        resp = send_command(command, to, params, 10.0)

    except Exception as error:
        logger.exception("Exception during file upload:")
        resp = MessageResponse(error=True, message=str(error))

        if path and os.path.exists(path):
            logger.debug("Delete uploaded file")
            os.remove(path)

    return resp.to_dict()


@app.route("/download", method="GET")
@authenticate()
def exec_download():
    """
    Download file
    Parameters must be specified in uri: http://mydomain.com/download?command=mycommand&to=myrecipient&params=

    Args:
        command (string): command
        to (string): command recipient
        params (dict): command parameters

    Returns:
        dict: message response or file content
    """
    try:
        # prepare params
        query = dict(bottle.request.query or {})
        command = query.get("command")
        to = query.get("to")
        try:
            params = copy.deepcopy(query)
            # remove useless parameters
            if "command" in params:
                del params["command"]
            if "to" in params:
                del params["to"]
        except Exception:  # pragma: no cover
            params = {}
        logger.debug("Download params: command=%s to=%s params=%s", command, to, params)

        # request full filepath from module (string format)
        resp = send_command(command, to, params)
        logger.debug("Response: %s", resp)
        if not resp.error:
            data = resp.data
            filename = os.path.basename(data["filepath"])
            root = os.path.dirname(data["filepath"])
            # download param is used to force download client side
            download = True
            if data["filename"]:
                download = data["filename"]
            logger.info(
                "Download file root=%s filename=%s download=%s",
                root,
                filename,
                download,
            )
            bottle.response.set_header("Cache-Control", "max-age=5")
            return bottle.static_file(filename=filename, root=root, download=download)

        # error during command execution
        raise Exception(resp.message)

    except Exception as error:
        logger.exception("Exception in download:")
        # something went wrong
        resp = MessageResponse(error=True, message=str(error))
        return resp.to_dict()


def handle_get_command():
    """
    Handle command from GET

    Returns:
        tuple: command values::

        (
            command (string): command name
            to (string): command recipient
            params (dict): command parameters
            timeout (int): command timeout
        )

    """
    query = dict(bottle.request.query or {})
    command = query.get("command")
    to = query.get("to")
    params = query.get("params", {})
    timeout = query.get("timeout", 3.0)
    logger.debug(
        "Get command: command=%s to=%s params=%s timeout=%s",
        command,
        to,
        params,
        timeout,
    )

    if len(params) == 0:
        # no params value specified, use all query string
        params = copy.deepcopy(query)
        # remove useless parameters
        if "command" in params:
            del params["command"]
        if "to" in params:
            del params["to"]
    else:
        # params specified in query string, unjsonify it
        try:
            params = json.loads(params)
        except Exception:
            params = None

    return (command, to, params, timeout)


def handle_post_command():
    """
    Handle command from POST

    Returns:
        tuple: command values::

        (
            command (string): command name
            to (string): command recipient
            params (dict): command parameters
            timeout (int): command timeout
        )

    """
    if bottle.request.json is None or not isinstance(bottle.request.json, dict):
        raise Exception("Invalid payload, json required.")
    tmp_params = dict(bottle.request.json or {})
    logger.debug("Post params: %s", tmp_params)

    to = tmp_params.get("to")
    if "to" in tmp_params:
        del tmp_params["to"]

    command = tmp_params.get("command")
    if "command" in tmp_params:
        del tmp_params["command"]

    timeout = tmp_params.get("timeout")
    if timeout:
        timeout = float(timeout)
    if "timeout" in tmp_params:
        del tmp_params["timeout"]

    if "params" in tmp_params:
        params = tmp_params["params"]
    else:
        params = tmp_params

    return (command, to, params, timeout)


@app.route("/command", method=["POST", "GET"])
@authenticate()
def exec_command():
    """
    Execute command on Cleep

    Args:
        command (string): command
        to (string): command recipient
        timeout (float): timeout
        params (dict): command parameters

    Returns:
        dict: message response
    """
    logger.trace(
        "Received command: method=%s data=[%d] json=%s",
        str(bottle.request.method),
        len(bottle.request.params),
        str(bottle.request.json),
    )

    try:
        command, to, params, timeout = (
            handle_get_command()
            if bottle.request.method == "GET"
            else handle_post_command()
        )
        resp = send_command(command, to, params, timeout)

    except Exception as error:
        logger.exception(
            "Exception in command: %s",
            {
                "method": bottle.request.method,
                "json": bottle.request.json,
                "type_json": type(bottle.request.json),
            },
        )
        resp = MessageResponse(error=True, message=str(error))

    return resp.to_dict()


@app.route("/modules", method="POST")
@authenticate()
def get_modules():
    """
    Return installed modules with their configuration.

    Installable/market modules are served by the update application RPC.
    """
    modules = get_modules_from_inventory()
    logger.debug("Modules: %s", modules)
    resp = MessageResponse(data=modules)
    return resp.to_dict()


@app.route("/devices", method="POST")
@authenticate()
def get_devices():
    """
    Return all devices

    Returns:
        MessageResponse: all devices by module
    """
    devices = get_devices_from_inventory()
    logger.debug("Devices: %s", devices)

    resp = MessageResponse(data=devices)
    return resp.to_dict()


@app.route("/renderers", method="POST")
@authenticate()
def get_renderers():
    """
    Returns all renderers

    Returns:
        MessageResponse: all renderers by type
    """
    renderers = get_renderers_from_inventory()
    logger.debug("Renderers: %s", renderers)

    resp = MessageResponse(data=renderers)
    return resp.to_dict()


@app.route("/drivers", method="POST")
@authenticate()
def get_drivers():
    """
    Returns all drivers

    Returns:
        MessageResponse: all drivers by type
    """
    drivers = get_drivers_from_inventory()
    logger.debug("Drivers: %s", drivers)

    resp = MessageResponse(data=drivers)
    return resp.to_dict()


@app.route("/events", method="POST")
@authenticate()
def get_events():
    """
    Return all used events

    Returns:
        MessageResponse: list of used events
    """
    events = get_events_from_inventory()
    logger.debug("Used events: %s", events)

    resp = MessageResponse(data=events)
    return resp.to_dict()


@app.route("/commands", method="POST")
@authenticate()
def get_commands():
    """
    Return all commands

    Returns:
        MessageResponse: list of commands
    """
    commands = inventory.get_module_commands(None)
    logger.debug("Commands: %s", commands)

    resp = MessageResponse(data=commands)
    return resp.to_dict()


@app.route("/doc/check/<app>", method="GET")
@authenticate()
def check_app_documentation(app):
    """
    Check application documentation

    Returns:
        MessageResponse: check result
    """
    query = dict(bottle.request.query or {})
    with_details = True if query.get("details") else False

    resp = MessageResponse()
    try:
        resp.data = inventory.check_module_documentation(app, with_details)
        has_error = any(
            [command_doc["valid"] is False for command_doc in resp.data.values()]
        )
        if has_error:
            resp.error = True
            resp.message = "Invalid application documentation"
    except Exception as error:
        logging.exception("Error checking application '%s' documentation", app)
        resp.error = True
        resp.message = str(error)

    return resp.to_dict()


@app.route("/doc/<app>", method="GET")
@authenticate()
def get_app_documentation(app):
    """
    Return documentation for specified application

    Returns:
        MessageResponse: application doc::

            {
                command (dict): command documentation
                ...
            }

    """
    resp = MessageResponse()
    try:
        doc = inventory.get_module_documentation(app)
        logger.debug("%s documentation: %s", app, doc)
        resp.data = doc
    except Exception as error:
        logger.exception("Unable to get application '%s' documentation: %s", app, error)
        resp.error = True
        resp.message = str(error)

    return resp.to_dict()


@app.route("/config", method="POST")
@authenticate()
def get_config():
    """
    Return device config

    Returns:
        MessageResponse: all device config::

            {
                modules (dict): all devices by module
                renderers (dict): all renderers
                devices (dict): all devices
                events (list): all used events
            }

    """
    global CLEEP_CACHE

    if not CLEEP_CACHE:
        logger.debug("Init cache")
        CLEEP_CACHE = {
            "modules": get_modules_from_inventory(),
            "events": get_events_from_inventory(),
            "renderers": get_renderers_from_inventory(),
            "drivers": get_drivers_from_inventory(),
        }

    resp = MessageResponse()
    try:
        modules_configs = inventory.get_modules_configs()
        for module_name, module in CLEEP_CACHE["modules"].items():
            module["config"] = modules_configs.get(module_name)

        resp.data = {
            "modules": CLEEP_CACHE["modules"],
            "devices": get_devices_from_inventory(),
            "events": CLEEP_CACHE["events"],
            "renderers": CLEEP_CACHE["renderers"],
            "drivers": CLEEP_CACHE["drivers"],
        }

    except Exception:
        logger.exception("Error getting config")
        resp.error = True
        resp.message = "Error getting configuration"

    return resp.to_dict()


@app.route("/remote-access", method="POST")
@authenticate()
def get_remote_access_urls():
    """
    Return device remote access urls

    Returns:
        MessageResponse: all remote access urls::

            {
                app name (str): url
            }

    """
    return MessageResponse(data=inventory.get_remote_access_urls()).to_dict()


@app.route("/registerpoll", method="POST")
@authenticate()
def registerpoll():
    """
    Register poll

    Returns:
        dict: {'pollKey':''}
    """
    poll_key = str(uuid.uuid4())
    if bus:
        logger.trace("Subscribe to bus %s", poll_key)
        bus.add_subscription(f"rpc-{poll_key}")

    bottle.response.content_type = "application/json"
    return json.dumps({"pollKey": poll_key})


@contextmanager
def pollcounter():
    """
    Poll counter context
    """
    global polling
    polling += 1
    try:
        yield
    finally:
        polling -= 1


@app.route("/poll", method="POST")
@authenticate()
def poll():
    """
    This is the endpoint for long poll clients.

    Returns:
        MessageResponse: dict of received event
    """
    with pollcounter():
        params = dict(bottle.request.json or {})
        logger.trace("Poll params: %s", params)
        bottle.response.content_type = "application/json"

        resp = MessageResponse(error=True, data=None, message="")
        if not bus:
            logger.debug("polling: bus not available")
            resp.message = "Bus not available"

        elif "pollKey" not in params:
            logger.debug("polling: registration key must be sent to poll request")
            resp.message = "Polling key is missing"

        elif not bus.is_subscribed(f'rpc-{params["pollKey"]}'):
            logger.debug("polling: rpc client must be registered before polling")
            resp.message = "Client not registered"

        else:
            try:
                poll_key = f'rpc-{params["pollKey"]}'
                msg = bus.pull(poll_key, POLL_TIMEOUT)

                resp.error = False
                resp.data = msg["message"]
                logger.debug("polling received %s", resp)

            except NoMessageAvailable:
                resp.message = "No message available"

            except Exception:
                logger.exception("Poll exception")
                crash_report.report_exception({"message": "Poll exception"})
                resp.message = "Internal error"

    return resp.to_dict()


@app.route("/<route:re:.*>", method="POST")
def rpc_wrapper(route):
    """
    Custom rpc route used to implement wrappers (ie REST=>RPC).

    Intentionally unauthenticated: external services (Alexa, webhooks) call this
    catch-all. Wrapper modules must validate their own tokens/signatures.
    Prefer named authenticated routes for new integrations.
    """
    return inventory.rpc_wrapper(route, bottle.request)


@app.route("/<path:path>", method="GET")
@authenticate()
def default(path):
    """
    Servers static files from HTML_DIR.
    """
    bottle.response.set_header(
        "Cache-Control",
        "no-cache, no-store, must-revalidate" if not cache_enabled else "max-age=3600",
    )
    return bottle.static_file(path, HTML_DIR)


@app.route("/", method="GET")
@authenticate()
def index():
    """
    Return a default document if no path was specified.
    """
    bottle.response.set_header(
        "Cache-Control",
        "no-cache, no-store, must-revalidate" if not cache_enabled else "max-age=3600",
    )
    return bottle.static_file("index.html", HTML_DIR)


@app.route("/logs", method="GET")
@authenticate()
def logs():  # pragma: no cover
    """
    Serve log file
    """
    script = """<script src="https://cdn.jsdelivr.net/gh/google/code-prettify@master/loader/run_prettify.js"></script>
    <script type="text/javascript">
    function scrollBottom() {
        setTimeout(function(){
            window.scrollTo(0, document.body.scrollHeight);
        }, 500);
    }
    </script>"""
    content = '<pre class="prettyprint" style="white-space: pre-wrap; white-space: -moz-pre-wrap; white-space: -pre-wrap; white-space: -o-pre-wrap; word-wrap: break-word;">%s</pre>'

    lines = cleep_filesystem.read_data("/var/log/cleep.log")
    lines = "" if not lines else lines

    return (
        "<html>\n<head>\n"
        + script
        + '\n</head>\n<body onload="scrollBottom()">\n'
        + content % "".join(lines)
        + "\n</body>\n</html>"
    )


@app.route("/health", method="GET")
def health():  # pragma: no cover
    """
    Return health status

    Returns:
        dict: cleep health::

        {
            starting (bool): True while modules are still configuring
            ready (bool): True when apps_ready (bus + inventory join done)
            started (dict): health status per app (True if started)
            core_ok (bool): True if all core apps are healthy
            apps_ok (bool): True if all user apps are healthy
        }

    """
    bottle.response.content_type = "application/json"

    if not apps_ready or not inventory:
        bottle.response.status = 503
        return json.dumps(
            {
                "starting": True,
                "ready": False,
                "started": {},
                "core_ok": False,
                "apps_ok": False,
            }
        )

    status_code = 200
    core_ok = True
    apps_ok = True
    apps_health = inventory.get_apps_health()
    for module_name, started in apps_health.items():
        if not started:
            status_code = 503
            if module_name in CORE_MODULES:
                core_ok = False
            else:
                apps_ok = False

    data = {
        "starting": False,
        "ready": True,
        "started": apps_health,
        "core_ok": core_ok,
        "apps_ok": apps_ok,
    }
    bottle.response.status = status_code
    return json.dumps(data)
