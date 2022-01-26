#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import os
import logging
import json
from contextlib import contextmanager
import time
import uptime
import uuid
import io
from gevent import pywsgi
from gevent.pywsgi import LoggingLogAdapter
from gevent import monkey
monkey.patch_all()
from cleep.exception import NoMessageAvailable
from cleep.common import MessageResponse, MessageRequest, CORE_MODULES
import bottle
from passlib.hash import sha256_crypt
import functools

__all__ = ['app']

#constants
BASE_DIR = '/opt/cleep/'
HTML_DIR = os.path.join(BASE_DIR, 'html')
AUTH_FILE = '/etc/cleep/auth.conf'
POLL_TIMEOUT = 60
SESSION_TIMEOUT = 900 #15mins

#globals
polling = 0
subscribed = False
sessions = {}
auth_config = {}
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
    global AUTH_FILE, auth_enabled, auth_config

    try:
        with io.open(AUTH_FILE, 'r') as fp:
            auth_config = json.load(fp)
        logger.debug('auth.conf: %s' % auth_config['accounts'])

        if bool(len(auth_config['accounts'])) and auth_config['enabled']:
            auth_enabled = True
        else:
            auth_enabled = False
        logger.debug('Auth enabled: %s' % auth_enabled)

    except:
        logger.exception('Unable to load auth file. Auth disabled:')
        crash_report.report_exception({
            'message': 'Unable to load auth file. Auth disabled:',
            'auth_enabled': auth_enabled,
            'auth_config': auth_config
        })

def configure(server_config, bootstrap, inventory_, debug_enabled_):
    """
    Configure rpcserver

    Args:
        server_config (dict): server configuration::

            {
                host (str): server host
                port (int): server port
                ssl_key (str): server SSL key
                ssl_cert (str): server SSL certificate
            }

        bootstrap (dict): bootstrap objects
        inventory_ (Inventory): Inventory instance
        debug_enabled_ (bool): debug status
    """
    global cleep_filesystem, inventory, bus, logger, crash_report, debug_enabled, server, app

    # configure logger
    logger = logging.getLogger('RpcServer')
    debug_enabled = debug_enabled_
    if debug_enabled_:
        logger.setLevel(logging.DEBUG)
    logger_requests = logging.getLogger('RpcRequests')
    logger_requests.setLevel(logging.WARNING)
    if debug_enabled_:
        logger_requests.setLevel(logging.DEBUG)

    # set members
    cleep_filesystem = bootstrap['cleep_filesystem']
    bus = bootstrap['internal_bus']
    inventory = inventory_
    crash_report = bootstrap['crash_report']

    # load auth
    load_auth()

    # create server
    ssl_key = server_config.get('ssl_key')
    ssl_cert = server_config.get('ssl_cert')
    if ssl_key and ssl_cert:
        if not os.path.exists(ssl_key) or not os.path.exists(ssl_cert):
            logger.error('Invalid key (%s) or cert (%s) file specified. Fallback to HTTP.', ssl_key, ssl_cert)
            ssl_key = None
            ssl_cert = None
    server = pywsgi.WSGIServer(
        (server_config.get('host', '0.0.0.0'), server_config.get('port', 80)),
        app,
        log=logger_requests,
        error_log=logger,
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
    global logger, debug_enabled

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
    global debug_enabled
    return debug_enabled

def start():
    """
    Start RPC server. This function is blocking.
    """
    global server, crash_report, app

    try:
        logger.debug('Starting RPC server')
        server.serve_forever()

    except KeyboardInterrupt:
        # user stops Cleep, close server properly
        pass

    except OSError:
        logger.fatal('Cleep instance is already running')

    except:
        logger.exception('Fatal error starting rpcserver:')
        crash_report.report_exception({
            'message': 'Fatal error starting rpcserver'
        })

    finally:
        if server:
            server.close()
            server.stop()

def check_auth(username, password):
    """
    Check auth

    Args:
        username (string): username
        password (string): user password
    """
    global auth_config_loaded, auth_config, sessions, SESSION_TIMEOUT

    # check session
    ip = bottle.request.environ.get('REMOTE_ADDR')
    logger.trace('Ip: %s' % ip)
    session_key = '%s-%s' % (ip, username)
    if session_key in sessions and sessions[session_key] >= uptime.uptime():
        # user still logged, update session timeout
        sessions[session_key] = uptime.uptime() + SESSION_TIMEOUT
        return True

    # check auth
    if username in auth_config['accounts']:
        logger.trace('Check password "%s"' % password)
        try:
            if sha256_crypt.verify(password, auth_config['accounts'][username]):
                # auth is valid, save session
                sessions[session_key] = uptime.uptime() + SESSION_TIMEOUT
                return True
            else:
                # invalid password
                logger.warning('Invalid password for user "%s"' % username)
                return False
        except:
            logger.warning('Password failed for user from ip "%s"' % ip)
            return False
    else:
        # username doesn't exist
        logger.warning('Invalid username "%s"' % username)
        return False

def authenticate():
    """
    Authentication process
    If authentication is enabled, check credentials
    """
    def decorator(func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if auth_enabled:
                username, password = bottle.request.auth or (None, None)
                logger.trace('username=%s password=%s' % (username, password))
                if username is None or not check_auth(username, password):
                    err = bottle.HTTPError(401, 'Access denied')
                    err.add_header('WWW-Authenticate', 'Basic realm="private"')
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
    request.sender = 'rpcserver'
    request.params = params

    if timeout is not None:
        # use specified timeout
        return bus.push(request, timeout)
    else:
        # use default timeout
        return bus.push(request)

def get_events():
    """
    Return used events

    Returns:
        list: list of used events
    """
    return inventory.get_used_events()

def get_renderers():
    """
    Return renderers

    Returns:
        list: list of renderers (see profileformattersbroker.py)
    """
    return inventory.get_renderers()

def get_modules(installable=False):
    """
    Return configurations for all loaded modules

    Args:
        installable (bool): If true returns all installable modules. If false (default) returns installed modules

    Returns:
        dict: map of modules with their configuration, devices, commands...
    """
    return inventory.get_modules() if not installable else inventory.get_installable_modules()

def get_devices():
    """
    Return all devices

    Returns:
        dict: all devices by module
    """
    return inventory.get_devices()

def get_drivers():
    """
    Return referenced drivers

    Returns:
        list: list of drivers
    """
    drivers = []
    for driver_type, data in inventory.get_drivers().items():
        for driver_name, driver in data.items():
            try:
                drivers.append({
                    'drivername': driver_name,
                    'drivertype': driver_type,
                    'processing': driver.processing(),
                    'installed': driver.is_installed(),
                })
            except:
                logger.exception('Error getting data for driver "%s"' % driver_name)

    return drivers

@app.route('/upload', method='POST')
@authenticate()
def upload():
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
    path = ''
    try:
        # get form fields
        command = bottle.request.forms.get('command')
        logger.debug('command=%s' % str(command))
        to = bottle.request.forms.get('to')
        logger.debug('to=%s' % str(to))
        params = bottle.request.forms.get('params')
        params = {} if params is None else params
        logger.debug('params=%s' % str(params))

        # check params
        if command is None or to is None:
            # not allowed, missing parameters
            resp = MessageResponse(message='Missing parameters', error=True)

        else:
            # get file
            logger.debug('Upload %s' % bottle.request.files.get('filename'))
            upload = bottle.request.files.get('file')
            path = os.path.join('/tmp', upload.filename)

            # remove file if already exists
            if os.path.exists(path):
                os.remove(path)
                time.sleep(0.25)

            # save file locally
            upload.save(path)

            # add filepath in params
            params['filepath'] = path

            # execute specified command
            logger.debug('Upload command:%s to:%s params:%s' % (str(command), str(to), str(params)))
            resp = send_command(command, to, params, 10.0)

    except Exception as e:
        logger.exception('Exception during file upload:')
        # something went wrong
        resp = MessageResponse(error=True, message=str(e))

        # delete uploaded file if possible
        if os.path.exists(path):
            logger.debug('Delete uploaded file')
            os.remove(path)

    return resp.to_dict()

@app.route('/download', method='GET')
@authenticate()
def download():
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
        command = bottle.request.query.command
        to = bottle.request.query.to
        params = {}
        logger.debug('Download params: command=%s to=%s params=%s' % (command, to, params))

        try:
            params = dict(bottle.request.query)
            # remove useless parameters
            if 'command' in params:
                del params['command']
            if 'to' in params:
                del params['to']
        except: # pragma: no cover
            params = {}

        # request full filepath from module (string format)
        resp = send_command(command, to, params)
        logger.debug('Response: %s' % resp)
        if not resp.error:
            data = resp.data
            filename = os.path.basename(data['filepath'])
            root = os.path.dirname(data['filepath'])
            # download param is used to force download client side
            download = True
            if data['filename']:
                download = data['filename']
            logger.info('Download file root=%s filename=%s download=%s' % (root, filename, download))
            bottle.response.set_header('Cache-Control', 'max-age=5')
            return bottle.static_file(filename=filename, root=root, download=download)

        else:
            # error during command execution
            raise Exception(resp.message)

    except Exception as e:
        logger.exception('Exception in download:')
        # something went wrong
        resp = MessageResponse(error=True, message=str(e))
        return resp.to_dict()

@app.route('/command', method=['POST', 'GET'])
@authenticate()
def command():
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
    logger.trace('Received command: method=%s data=[%d] json=%s' % (
        str(bottle.request.method),
        len(bottle.request.params),
        str(bottle.request.json)
    ))

    try:
        command = None
        to = None
        params = {}
        timeout = None

        # prepare data to push
        if bottle.request.method == 'GET':
            # GET request
            command = bottle.request.query.command
            to = bottle.request.query.to
            params = bottle.request.query.params
            timeout = bottle.request.query.timeout
            logger.debug('PARAMS=%s' % params)
            # handle params:
            #  - could be specified as params field with json
            #  - or not specified in which case parameters are directly specified in query string
            if len(params) == 0:
                # no params value specified, use all query string
                params = dict(bottle.request.query)
                # remove useless parameters
                if 'command' in params:
                    del params['command']
                if 'to' in params:
                    del params['to']
            else:
                # params specified in query string, unjsonify it
                try:
                    params = json.loads(params)
                except:
                    params = None

        else:
            # POST request (need json)
            tmp_params = bottle.request.json
            if tmp_params is None:
                raise Exception('Invalid payload, json required.')
            if 'to' in tmp_params:
                to = tmp_params['to']
                del tmp_params['to']
            if 'command' in tmp_params:
                command = tmp_params['command']
                del tmp_params['command']
            if ('timeout' in tmp_params and tmp_params['timeout'] is not None and
                    type(tmp_params['timeout']).__name__ in ('float', 'int')):
                timeout = float(tmp_params['timeout'])
                del tmp_params['timeout']
            if 'params' in tmp_params:
                params = tmp_params['params']
            else:
                params = None

        # execute command
        resp = send_command(command, to, params, timeout)

    except Exception as e:
        logger.exception('Exception in command:')
        # something went wrong
        resp = MessageResponse(error=True, message=str(e))

    return resp.to_dict()

@app.route('/modules', method='POST')
@authenticate()
def modules():
    """
    Return modules with their configuration

    Args:
        installable (bool): if True will return installable modules only. Otherwise returns installed modules

    Returns:
        dict: map of modules with their configuration, devices, commands...
    """
    installable = False
    params = bottle.request.json
    if params and 'installable' in params:
        installable = params['installable']

    if not installable:
        modules = get_modules()
        logger.debug('Modules: %s' % modules)
    else:
        modules = get_modules(installable=installable)
        logger.debug('Installable modules: %s' % modules)

    return json.dumps(modules)

@app.route('/devices', method='POST')
@authenticate()
def devices():
    """
    Return all devices

    Returns:
        dict: all devices by module
    """
    devices = get_devices()
    logger.debug('Devices: %s' % devices)

    return json.dumps(devices)

@app.route('/renderers', method='POST')
@authenticate()
def renderers():
    """
    Returns all renderers

    Returns:
        dict: all renderers by type
    """
    renderers = get_renderers()
    logger.debug('Renderers: %s' % renderers)

    return json.dumps(renderers)

@app.route('/drivers', method='POST')
@authenticate()
def drivers():
    """
    Returns all drivers

    Returns:
        dict: all drivers by type
    """
    drivers = get_drivers()
    logger.debug('Drivers: %s' % drivers)

    return json.dumps(drivers)

@app.route('/events', method='POST')
@authenticate()
def events():
    """
    Return all used events

    Returns:
        list: list of used events
    """
    events = get_events()
    logger.debug('Used events: %s' % events)

    return json.dumps(events)

@app.route('/config', method='POST')
@authenticate()
def config():
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
    try:
        return json.dumps({
            'modules': get_modules(),
            'events': get_events(),
            'renderers': get_renderers(),
            'devices': get_devices(),
            'drivers': get_drivers(),
        })
    except:
        logger.exception('Error getting config')

    return json.dumps({})

@app.route('/registerpoll', method='POST')
@authenticate()
def registerpoll():
    """
    Register poll

    Returns:
        dict: {'pollkey':''}
    """
    # subscribe to bus
    poll_key = str(uuid.uuid4())
    if bus:
        logger.trace('Subscribe to bus %s' % poll_key)
        bus.add_subscription('rpc-%s' % poll_key)

    # return response
    bottle.response.content_type = 'application/json'
    return json.dumps({'pollKey': poll_key})

@contextmanager
def pollcounter():
    global polling
    polling += 1
    yield
    polling -= 1

@app.route('/poll', method='POST')
@authenticate()
def poll():
    """
    This is the endpoint for long poll clients.

    Returns:
        dict: map of received event
    """
    with pollcounter():
        params = bottle.request.json
        logger.trace('Poll params: %s' % params)
        # response content type.
        bottle.response.content_type = 'application/json'

        # init message
        message = {'error':True, 'data':None, 'message':''}

        # process poll
        if params is None:
            # rpc client no registered yet
            logger.debug('polling: request must be in json')
            message['message'] = 'Invalid request'
            time.sleep(1.0)

        elif not bus:
            # bus not available yet
            logger.debug('polling: bus not available')
            message['message'] = 'Bus not available'
            time.sleep(1.0)

        elif not 'pollKey' in params:
            # rpc client no registered yet
            logger.debug('polling: registration key must be sent to poll request')
            message['message'] = 'Polling key is missing'
            time.sleep(1.0)

        elif not bus.is_subscribed('rpc-%s' % params['pollKey']):
            # rpc client no registered yet
            logger.debug('polling: rpc client must be registered before polling')
            message['message'] = 'Client not registered'
            time.sleep(1.0)

        else:
            # wait for event (blocking by default) until end of timeout
            try:
                # wait for message
                poll_key = 'rpc-%s' % params['pollKey']
                msg = bus.pull(poll_key, POLL_TIMEOUT)

                # prepare output
                message['error'] = False
                message['data'] = msg['message']
                logger.debug('polling received %s' % message)

            except NoMessageAvailable:
                message['message'] = 'No message available'
                time.sleep(1.0)

            except:
                logger.exception('Poll exception')
                crash_report.report_exception({
                    'message': 'Poll exception'
                })
                message['message'] = 'Internal error'
                time.sleep(5.0)

    # and return it
    return json.dumps(message)

@app.route('/<route:re:.*>', method='POST')
# TODO add auth to external request
# @authenticate()
def rpc_wrapper(route):
    """
    Custom rpc route used to implement wrappers (ie REST=>RPC)
    This route is intended to be used with external services like alexa
    """
    return inventory.rpc_wrapper(route, bottle.request)

@app.route('/<path:path>', method='GET')
@authenticate()
def default(path):
    """
    Servers static files from HTML_DIR.
    """
    bottle.response.set_header('Cache-Control', 'no-cache, no-store, must-revalidate' if not cache_enabled else 'max-age=3600')
    return bottle.static_file(path, HTML_DIR)

@app.route('/', method='GET')
@authenticate()
def index():
    """
    Return a default document if no path was specified.
    """
    bottle.response.set_header('Cache-Control', 'no-cache, no-store, must-revalidate' if not cache_enabled else 'max-age=3600')
    return bottle.static_file('index.html', HTML_DIR)

@app.route('/logs', method='GET')
def logs(): # pragma: no cover
    """
    Serve log file
    """
    script = u"""<script src="https://cdn.jsdelivr.net/gh/google/code-prettify@master/loader/run_prettify.js"></script>
    <script type="text/javascript">
    function scrollBottom() {
        setTimeout(function(){
            window.scrollTo(0, document.body.scrollHeight);
        }, 500);
    }
    </script>"""
    content = '<pre class="prettyprint" style="white-space: pre-wrap; white-space: -moz-pre-wrap; white-space: -pre-wrap; white-space: -o-pre-wrap; word-wrap: break-word;">%s</pre>'

    lines = cleep_filesystem.read_data('/var/log/cleep.log')
    lines = '' if not lines else lines

    return '<html>\n<head>\n' + script + '\n</head>\n<body onload="scrollBottom()">\n' + content % ''.join(lines) + '\n</body>\n</html>'

@app.route('/health', method='GET')
def health(): # pragma: no cover
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
    health = inventory.get_apps_health()
    for module_name, started in health.items():
        if not started:
            status_code = 503
            if module_name in CORE_MODULES:
                core_ok = False
            else:
                apps_ok = False

    data = {
        'started': health,
        'core_ok': core_ok,
        'apps_ok': apps_ok,
    }
    bottle.response.content_type = 'application/json'
    bottle.response.status = status_code
    return json.dumps(data)
    

