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

from contextlib import contextmanager
import copy
import functools
import io
import json
import logging
import os
import time
import uuid
import uptime
from passlib.hash import sha256_crypt
from gevent import pywsgi
from gevent import monkey

monkey.patch_all()
import bottle
import socket
from cleep.exception import NoMessageAvailable
from cleep.common import MessageResponse, MessageRequest, CORE_MODULES
from cleep.libs.configs.cleepconf import CleepConf

__all__ = ["app"]

# constants
BASE_DIR = "/opt/cleep/"
HTML_DIR = os.path.join(BASE_DIR, "html")
POLL_TIMEOUT = 60
SESSION_TIMEOUT = 900  # 15mins
CLEEP_CACHE = None
LOCAL_ADDRS = ["127.0.0.1", "localhost", socket.gethostbyname(socket.gethostname())]

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
cleep_filesystem = None
inventory = None
bus = None
crash_report = None
cache_enabled = True


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

    # load auth
    load_auth()

    # create server
    ssl_options = get_ssl_options(rpc_config)
    protocol = "https" if rpc_config.get("ssl", False) else "http"
    host = rpc_config.get("host", "0.0.0.0")
    port = rpc_config.get("port", 80)
    logger.info("Running RPC server %s://%s:%s", protocol, host, port)
    logger.debug("rpc_config=%s ssl_options=%s", rpc_config, ssl_options)
    server = pywsgi.WSGIServer(
        (host, port), app, log=logger_requests, error_log=logger, **ssl_options
    )


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


def start():
    """
    Start RPC server. This function is blocking.
    """
    try:
        logger.debug("Starting RPC server")
        server.serve_forever()

    except KeyboardInterrupt:
        # user stops Cleep, close server properly
        pass

    except OSError:
        logger.fatal("Cleep instance is already running")

    except Exception:
        logger.exception("Fatal error starting rpcserver:")
        crash_report.report_exception({"message": "Fatal error starting rpcserver"})

    finally:
        if server:
            server.close()
            server.stop()


def check_auth(account, password):
    """
    Check auth

    Args:
        account (str): account name
        password (str): account password
    """
    # check session
    client_ip = bottle.request.environ.get("REMOTE_ADDR")
    logger.trace("Client ip: %s", client_ip)
    session_key = f"{client_ip}-{account}"
    if session_key in sessions and sessions[session_key] >= uptime.uptime():
        # user still logged, update session timeout
        sessions[session_key] = uptime.uptime() + SESSION_TIMEOUT
        return True

    # check account exists
    if account not in auth_accounts:
        logger.warning('Invalid auth account "%s"', account)
        return False

    try:
        if sha256_crypt.verify(password, auth_accounts[account]):
            # auth is valid, save session
            sessions[session_key] = uptime.uptime() + SESSION_TIMEOUT
            return True

        # invalid password
        logger.warning('Invalid password for account "%s"', account)
        return False
    except Exception:
        logger.warning(
            'Password failed for account "%s" from ip "%s"', account, client_ip
        )
        return False


def authenticate():
    """
    Authenticate decorator
    If authentication is enabled, check credentials
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            remote_addr = bottle.request.environ.get('HTTP_X_FORWARDED_FOR') or bottle.request.environ.get('REMOTE_ADDR')
            if auth_enabled and remote_addr not in LOCAL_ADDRS:
                account, password = bottle.request.auth or (None, None)
                logger.debug("account=%s password=%s", account, password)
                if account is None or not check_auth(account, password):
                    err = bottle.HTTPError(401, "Access denied")
                    err.add_header("WWW-Authenticate", 'Basic realm="private"')
                    return err
            return func(*args, **kwargs)

        return wrapper

    return decorator


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


def get_modules_from_inventory(installable=False):
    """
    Return configurations for all loaded modules

    Args:
        installable (bool): If true returns all installable modules. If false (default) returns installed modules

    Returns:
        dict: map of modules with their configuration, devices, commands...
    """
    return (
        inventory.get_modules()
        if not installable
        else inventory.get_installable_modules()
    )


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
        # get form fields
        forms = dict(bottle.request.forms or {})
        command = forms.get("command")
        to = forms.get("to")
        params = forms.get("params") or {}
        logger.debug("Form content: command=%s to=%s params=%s", command, to, params)

        # check params
        if command is None or to is None:
            # not allowed, missing parameters
            raise Exception("Missing parameters")

        else:
            # get file
            logger.debug("Upload %s", bottle.request.files)
            files = dict(bottle.request.files or {})
            upload = files.get("file")
            path = os.path.join("/tmp", upload.filename)

            # remove file if already exists
            if os.path.exists(path):
                os.remove(path)
                time.sleep(0.25)

            # save file locally
            upload.save(path)

            # add filepath in params
            params["filepath"] = path

            # execute specified command
            logger.debug("Upload command:%s to:%s params:%s", command, to, params)
            resp = send_command(command, to, params, 10.0)

    except Exception as error:
        logger.exception("Exception during file upload:")
        resp = MessageResponse(error=True, message=str(error))

        # delete uploaded file if possible
        if os.path.exists(path):
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
def get_modules():
    """
    Return modules with their configuration

    Args:
        installable (bool): if True will return installable modules only. Otherwise returns installed modules

    Returns:
        dict: map of modules with their configuration, devices, commands...
    """
    installable = False
    params = dict(bottle.request.json or {})
    if params and "installable" in params:
        installable = params["installable"]

    if not installable:
        modules = get_modules_from_inventory()
        logger.debug("Modules: %s", modules)
    else:
        modules = get_modules_from_inventory(installable=installable)
        logger.debug("Installable modules: %s", modules)

    return json.dumps(modules)


@app.route("/devices", method="POST")
def get_devices():
    """
    Return all devices

    Returns:
        dict: all devices by module
    """
    devices = get_devices_from_inventory()
    logger.debug("Devices: %s", devices)

    return json.dumps(devices)


@app.route("/renderers", method="POST")
def get_renderers():
    """
    Returns all renderers

    Returns:
        dict: all renderers by type
    """
    renderers = get_renderers_from_inventory()
    logger.debug("Renderers: %s", renderers)

    return json.dumps(renderers)


@app.route("/drivers", method="POST")
def get_drivers():
    """
    Returns all drivers

    Returns:
        dict: all drivers by type
    """
    drivers = get_drivers_from_inventory()
    logger.debug("Drivers: %s", drivers)

    return json.dumps(drivers)


@app.route("/events", method="POST")
def get_events():
    """
    Return all used events

    Returns:
        list: list of used events
    """
    events = get_events_from_inventory()
    logger.debug("Used events: %s", events)

    return json.dumps(events)

@app.route("/commands", method="POST")
def get_commands():
    """
    Return all commands

    Returns:
        list: list of commands
    """
    commands = inventory.get_module_commands(None)
    logger.debug("Commands: %s", commands)

    return json.dumps(commands)


@app.route("/config", method="POST")
@authenticate()
def get_config():
    """
    Return device config

    Returns:
        dict: all device config::

            {
                modules (dict): all devices by module
                renderers (dict): all renderers
                devices (dict): all devices
                events (list): all used events
            }

    """
    global CLEEP_CACHE

    # handle cleep cache
    if not CLEEP_CACHE:
        logger.debug("Init cache")
        CLEEP_CACHE = {
            "modules": get_modules_from_inventory(),
            "events": get_events_from_inventory(),
            "renderers": get_renderers_from_inventory(),
            "drivers": get_drivers_from_inventory(),
        }

    try:
        # update volatile data
        modules_configs = inventory.get_modules_configs()
        for module_name, module in CLEEP_CACHE["modules"].items():
            module["config"] = modules_configs[module_name]

        return json.dumps(
            {
                "modules": CLEEP_CACHE["modules"],
                "devices": get_devices_from_inventory(),
                "events": CLEEP_CACHE["events"],
                "renderers": CLEEP_CACHE["renderers"],
                "drivers": CLEEP_CACHE["drivers"],
            }
        )
    except Exception:
        logger.exception("Error getting config")

    return json.dumps({})


@app.route("/registerpoll", method="POST")
def registerpoll():
    """
    Register poll

    Returns:
        dict: {'pollkey':''}
    """
    # subscribe to bus
    poll_key = str(uuid.uuid4())
    if bus:
        logger.trace("Subscribe to bus %s", poll_key)
        bus.add_subscription(f"rpc-{poll_key}")

    # return response
    bottle.response.content_type = "application/json"
    return json.dumps({"pollKey": poll_key})


@contextmanager
def pollcounter():
    """
    Poll counter context
    """
    global polling
    polling += 1
    yield
    polling -= 1


@app.route("/poll", method="POST")
@authenticate()
def poll():
    """
    This is the endpoint for long poll clients.

    Returns:
        dict: map of received event
    """
    with pollcounter():
        params = dict(bottle.request.json or {})
        logger.trace("Poll params: %s", params)
        # response content type.
        bottle.response.content_type = "application/json"

        # init message
        message = {"error": True, "data": None, "message": ""}

        # process poll
        if not bus:
            # bus not available yet
            logger.debug("polling: bus not available")
            message["message"] = "Bus not available"
            time.sleep(1.0)

        elif "pollKey" not in params:
            # rpc client no registered yet
            logger.debug("polling: registration key must be sent to poll request")
            message["message"] = "Polling key is missing"
            time.sleep(1.0)

        elif not bus.is_subscribed(f'rpc-{params["pollKey"]}'):
            # rpc client no registered yet
            logger.debug("polling: rpc client must be registered before polling")
            message["message"] = "Client not registered"
            time.sleep(1.0)

        else:
            # wait for event (blocking by default) until end of timeout
            try:
                # wait for message
                poll_key = f'rpc-{params["pollKey"]}'
                msg = bus.pull(poll_key, POLL_TIMEOUT)

                # prepare output
                message["error"] = False
                message["data"] = msg["message"]
                logger.debug("polling received %s", message)

            except NoMessageAvailable:
                message["message"] = "No message available"
                time.sleep(1.0)

            except Exception:
                logger.exception("Poll exception")
                crash_report.report_exception({"message": "Poll exception"})
                message["message"] = "Internal error"
                time.sleep(5.0)

    # and return it
    return json.dumps(message)


@app.route("/<route:re:.*>", method="POST")
# TODO add auth to external request ?
def rpc_wrapper(route):
    """
    Custom rpc route used to implement wrappers (ie REST=>RPC)
    This route is intended to be used with external services like alexa
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
            details (dict): health status per app (True if started)
            core_ok (bool): True if all core apps are healthy
            apps_ok (bool): True if all user apps are healthy
        }

    """
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
        "started": apps_health,
        "core_ok": core_ok,
        "apps_ok": apps_ok,
    }
    bottle.response.content_type = "application/json"
    bottle.response.status = status_code
    return json.dumps(data)
