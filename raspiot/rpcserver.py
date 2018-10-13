#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Rpcserver based on long poll example from https://github.com/larsks/pubsub_example
Rpcserver implements:
 - authentication (login, password)
 - HTTP and HTTPS support
 - file upload and download
 - poll requests
 - command requests
 - module configs requests
 - devices list requests
"""

import os
import logging
import sys
import argparse
import json
from contextlib import contextmanager
import time
import uptime
import uuid
from gevent import monkey; monkey.patch_all()
from gevent import queue
from gevent import pywsgi 
from gevent.pywsgi import LoggingLogAdapter
from .utils import NoMessageAvailable, MessageResponse, MessageRequest, CommandError, NoResponse
import bottle
from bottle import auth_basic
from passlib.hash import sha256_crypt
import functools
from .libs.configs.raspiotconf import RaspiotConf

__all__ = [u'app']

#constants
BASE_DIR = u'/opt/raspiot/'
HTML_DIR = os.path.join(BASE_DIR, u'html')
AUTH_FILE = u'/etc/raspiot/auth.conf'
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

def bottle_logger(func):
    """
    Define bottle logging
    """
    def wrapper(*args, **kwargs):
        req = func(*args, **kwargs)
        logger.debug(u'%s %s %s %s' % (
                     bottle.request.remote_addr, 
                     bottle.request.method,
                     bottle.request.url,
                     bottle.response.status))
        return req
    return wrapper

def load_auth():
    """
    Load auth and enable auth if necessary
    """
    global AUTH_FILE, auth_enabled, auth_config
    try:
        execfile(AUTH_FILE, auth_config)
        logger.debug(u'auth.conf: %s' % auth_config[u'accounts'])

        if len(auth_config[u'accounts'])>0 and auth_config[u'enabled']:
            auth_enabled = True
        else:
            auth_enabled = False
        logger.debug(u'Auth enabled: %s' % auth_enabled)
    except:
        logger.exception(u'Unable to load auth file. Auth disabled:')
        crash_report.report_exception({
            u'message': u'Unable to load auth file. Auth disabled:',
            u'auth_enabled': auth_enabled,
            u'auth_config': auth_config
        })

def configure(bootstrap, inventory_, debug_enabled_):
    """
    Configure rpcserver

    Args:
        bootstrap (dict): bootstrap objects
        inventory_ (Inventory): Inventory instance
        debug_enabled_ (bool): debug status
    """
    global cleep_filesystem, inventory, bus, logger, crash_report, debug_enabled

    #configure logger
    #logging.basicConfig(level=logging.DEBUG, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')
    logger = logging.getLogger(u'RpcServer')
    debug_enabled = debug_enabled_
    if debug_enabled_:
        logger.setLevel(logging.DEBUG)

    #set members
    cleep_filesystem = bootstrap[u'cleep_filesystem']
    bus = bootstrap[u'message_bus']
    inventory = inventory_

    #configure crash report
    crash_report = bootstrap[u'crash_report']

    #load auth
    load_auth()

def set_debug(debug_enabled_):
    """
    Change debug level

    Args:
        debug_enabled_ (bool): True to enable debug
    """
    global logger, debug_enabled
    logger.error('set debug %s' % debug_enabled_)

    debug_enabled = debug_enabled_
    if debug_enabled:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

def get_debug():
    """
    Return debug status

    Returns:
        bool
    """
    global debug_enabled
    return debug_enabled

def start(host=u'0.0.0.0', port=80, key=None, cert=None):
    """
    Start RPC server. This function is blocking.
    Start by default unsecure web server
    You can configure SSL server specifying key and cert parameters

    Args:
        host (string): host (default computer is accessible on localt network)
        port (int): port to listen to (by default is standart HTTP port 80)
        key (string): SSL key file
        cert (string): SSL certificate file
    """
    global server, app, crash_report

    try:
        run_https = False
        if key is not None and len(key)>0 and cert is not None and len(cert)>0:
            #check files
            if os.path.exists(key) and os.path.exists(cert):
                run_https = True
            else:
                logger.error('Invalid key (%s) or cert (%s) file specified. Fallback to HTTP.' % (key, cert))

        if run_https:
            #start HTTPS server
            logger.debug(u'Starting HTTPS server on %s:%d' % (host, port))
            server_logger = LoggingLogAdapter(logger, logging.DEBUG)
            server = pywsgi.WSGIServer((host, port), app, keyfile=key, certfile=cert, log=server_logger)
            server.serve_forever()

        else:
            #start HTTP server
            logger.debug(u'Starting HTTP server on %s:%d' % (host, port))
            app.run(server=u'gevent', host=host, port=port, quiet=True, debug=False, reloader=False)

    except KeyboardInterrupt:
        #user stops raspiot, close server properly
        if not server.closed:
            server.close()

    except:
        logger.exception(u'Fatal error starting rpcserver:')
        crash_report.report_exception({
            u'message': u'Fatal error starting rpcserver'
        })
        if not server.closed:
            server.close()

def check_auth(username, password):
    """
    Check auth

    Args:
        username (string): username
        password (string): user password
    """
    global auth_config_loaded, auth_config, sessions, SESSION_TIMEOUT

    #check session
    ip = bottle.request.environ.get(u'REMOTE_ADDR')
    session_key = u'%s-%s' % (ip, username)
    if sessions.has_key(session_key) and sessions[session_key]>=uptime.uptime():
        #user still logged, update session timeout
        sessions[session_key] = uptime.uptime() + SESSION_TIMEOUT
        return True

    #check auth
    if auth_config[u'accounts'].has_key(username):
        if sha256_crypt.verify(password, auth_config[u'accounts'][username]):
            #auth is valid, save session
            sessions[session_key] = uptime.uptime() + SESSION_TIMEOUT
            return True
        else:
            #invalid password
            logger.warning(u'Invalid password for user "%s"' % username)
            return False
    else:
        #username doesn't exist
        logger.warning(u'Invalid username "%s"' % username)
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
                logger.debug(u'username=%s password=%s' % (username, password))
                if username is None or not check_auth(username, password):
                    err = bottle.HTTPError(401, u'Access denied')
                    err.add_header(u'WWW-Authenticate', u'Basic realm="private"')
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

    Return:
        MessageResonse: command response (None if broadcasted message)
    """
    #prepare and send command
    request = MessageRequest()
    request.command = command
    request.to = to
    request.from_ = u'rpcserver'
    request.params = params

    if timeout is not None:
        return bus.push(request, timeout)
    else:
        return bus.push(request)

def get_events():
    """
    Return used events

    Return:
        list: list of used events
    """
    return inventory.get_used_events()

def get_renderers():
    """
    Return renderers

    Return:
        list: list of renderers by type::
            {
                'type1': {
                    'subtype1':  {
                        <profile name>: <profile instance>,
                        ...
                    }
                    'subtype2': ...
                },
                'type2': {
                    <profile name>: <renderer instance>
                },
                ...
            }
    """
    return inventory.get_renderers()

def get_modules():
    """
    Return configurations for all loaded modules

    Return:
        dict: map of modules with their configuration, devices, commands...
    """
    return inventory.get_modules()

def get_devices():
    """
    Return all devices

    Return:
        dict: all devices by module
    """
    return inventory.get_devices()

@app.route(u'/upload', method=u'POST')
@authenticate()
def upload():
    """
    Upload file (POST only)
    Parameters are embedded in POST data

    Args:
        command (string): command
        to (string): command recipient
        params (dict): command parameters

    Return:
        MessageResponse: command response
    """
    path = None
    try:
        #get form fields
        command = bottle.request.forms.get(u'command')
        logger.debug(u'command=%s' % unicode(command))
        to = bottle.request.forms.get('to')
        logger.debug(u'to=%s' % unicode(to))
        params = bottle.request.forms.get(u'params')
        logger.debug(u'params=%s' % unicode(params))
        if params is None:
            params = {}

        #check params
        if command is None or to is None:
            #not allowed, missing parameters
            msg = MessageResponse()
            msg.message = u'Missing parameters'
            msg.error = True
            resp = msg.to_dict()

        else:
            #get file
            upload = bottle.request.files.get(u'file')
            path = os.path.join(u'/tmp', upload.filename)

            #remove file if already exists
            if os.path.exists(path):
                os.remove(path)
                time.sleep(0.25)

            #save file locally
            upload.save(path)

            #add filepath in params
            params[u'filepath'] = path

            #execute specified command
            logger.debug(u'Upload command:%s to:%s params:%s' % (unicode(command), unicode(to), unicode(params)))
            resp = send_command(command, to, params, 10.0)

    except Exception as e:
        logger.exception(u'Exception in upload:')
        #something went wrong
        msg = MessageResponse()
        msg.message = unicode(e)
        msg.error = True
        resp = msg.to_dict()

        #delete uploaded file if possible
        if path:
            logger.debug(u'Delete uploaded file')
            os.remove(path)

    return resp

@app.route(u'/download', method=u'GET')
@authenticate()
def download():
    """
    Download file
    Parameters must be specified in uri: http://mydomain.com/download?command=mycommand&to=myrecipient&params=

    Args:
        command (string): command
        to (string): command recipient
        params (dict): command parameters

    Return:
        MessageResponse: command response
    """
    try:
        #prepare params
        command = bottle.request.query.command
        to = bottle.request.query.to
        params = {}
        logger.debug(u'Download params: command=%s to=%s params=%s' % (command, to, params))

        try:
            params = dict(bottle.request.query)
            #remove useless parameters
            if params.has_key(u'command'):
                del params[u'command']
            if params.has_key(u'to'):
                del params[u'to']
        except:
            params = {}

        #request full filepath from module (string format)
        resp = send_command(command, to, params)
        logger.debug(u'Response: %s' % resp)
        if not resp[u'error']:
            data = resp[u'data']
            filename = os.path.basename(data[u'filepath'])
            root = os.path.dirname(data[u'filepath'])
            download = True
            if data[u'filename']:
                download = data[u'filename']
            logger.debug(u'Download file root=%s filename=%s download=%s' % (root, filename, download))
            return bottle.static_file(filename=filename, root=root, download=download)
        else:
            #error during filepath retrieving
            raise Exception(resp[u'message'])

    except Exception as e:
        logger.exception(u'Exception in download:')
        #something went wrong
        msg = MessageResponse()
        msg.message = unicode(e)
        msg.error = True
        resp = msg.to_dict()

    return resp

@app.route(u'/command', method=[u'POST',u'GET'])
@authenticate()
def command():
    """
    Execute command on raspiot

    Args:
        command (string): command
        to (string): command recipient
        timeout (float): timeout
        params (dict): command parameters

    Return:
        MessageResponse: command response
    """
    logger.debug(u'COMMAND method=%s data=[%d]: %s' % (unicode(bottle.request.method), len(bottle.request.params), unicode(bottle.request.json)))

    try:
        command = None
        to = None
        params = {}
        timeout = None

        #prepare data to push
        if bottle.request.method==u'GET':
            #GET request
            command = bottle.request.query.command
            to = bottle.request.query.to
            params = bottle.request.query.params
            timeout = bottle.request.query.timeout
            #handle params: 
            # - could be specified as params field with json 
            # - or not specified in which case parameters are directly specified in query string
            if len(params)==0:
                #no params value specified, use all query string
                params = dict(bottle.request.query)
                #remove useless parameters
                if params.has_key(u'command'):
                    del params[u'command']
                if params.has_key(u'to'):
                    del params[u'to']
            else:
                #params specified in query string, unjsonify it
                try:
                    params = json.loads(params)
                except:
                    params = None

        else:
            #POST request (need json)
            tmp_params = bottle.request.json
            if tmp_params.has_key(u'to'):
                to = tmp_params[u'to']
                del tmp_params[u'to']
            if tmp_params.has_key(u'command'):
                command = tmp_params[u'command']
                del tmp_params[u'command']
            if tmp_params.has_key(u'timeout') and tmp_params[u'timeout'] is not None and type(tmp_params[u'timeout']).__name__ in (u'float', u'int'):
                timeout = float(tmp_params[u'timeout'])
                del tmp_params[u'timeout']
            if len(tmp_params)>0:
                params = tmp_params[u'params']

        #execute command
        resp = send_command(command, to, params, timeout)

    except Exception as e:
        logger.exception(u'Exception in command:')
        #something went wrong
        msg = MessageResponse()
        msg.message = unicode(e)
        msg.error = True
        resp = msg.to_dict()

    return resp

@app.route(u'/modules', method=u'POST')
@authenticate()
def modules():
    """
    Return configurations for all loaded modules

    Return:
        dict: map of modules with their configuration, devices, commands...
    """
    modules = get_modules()
    logger.debug(u'Modules: %s' % modules)

    return json.dumps(modules)

@app.route(u'/devices', method=u'POST')
@authenticate()
def devices():
    """
    Return all devices

    Return:
        dict: all devices by module
    """
    devices = get_devices()
    logger.debug(u'Devices: %s' % devices)

    return json.dumps(devices)

@app.route(u'/renderers', method=u'POST')
@authenticate()
def renderers():
    """
    Returns all renderers

    Return:
        dict: all renderers by type
    """
    renderers = get_renderers()
    logger.debug(u'Renderers: %s' % renderers)

    return json.dumps(renderers)

@app.route(u'/events', method=u'POST')
@authenticate()
def events():
    """
    Return all used events

    Return:
        list: list of used events
    """
    events = get_events()
    logger.debug(u'Used events: %s' % events)

    return json.dumps(events)

@app.route(u'/config', method=u'POST')
@authenticate()
def config():
    """
    Return device config

    Return:
        dict: all device config::
            {
                modules (dict): all devices by module
                renderers (dict): all renderers
                devices (dict): all devices
                events (list): all used events
            }
    """
    config = {
        'modules': get_modules(),
        'events': get_events(),
        'renderers': get_renderers(),
        'devices': get_devices()
    }

    return json.dumps(config)

@app.route(u'/registerpoll', method=u'POST')
@authenticate()
def registerpoll():
    """
    Register poll

    Return:
        dict: {'pollkey':''}
    """
    #subscribe to bus
    poll_key = unicode(uuid.uuid4())
    if bus:
        logger.debug(u'subscribe %s' % poll_key)
        bus.add_subscription(u'rpc-%s' % poll_key)

    #return response
    bottle.response.content_type = u'application/json'
    return json.dumps({u'pollKey':poll_key})

@contextmanager
def pollcounter():
    global polling
    polling += 1
    yield
    polling -= 1

@app.route(u'/poll', method=u'POST')
@authenticate()
def poll():
    """
    This is the endpoint for long poll clients.

    Return:
        dict: map of received event
    """
    with pollcounter():
        params = bottle.request.json
        #response content type.
        bottle.response.content_type = u'application/json'

        #init message
        message = {u'error':True, u'data':None, u'message':''}

        #process poll
        if not bus:
            #bus not available yet
            logger.debug(u'polling: bus not available')
            message[u'message'] = u'Bus not available'
            time.sleep(1.0)

        elif not params.has_key(u'pollKey'):
            #rpc client no registered yet
            logger.debug(u'polling: registration key must be sent to poll request')
            message[u'message'] = u'Polling key is missing'
            time.sleep(1.0)

        elif not bus.is_subscribed(u'rpc-%s' % params[u'pollKey']):
            #rpc client no registered yet
            logger.debug(u'polling: rpc client must be registered before polling')
            message[u'message'] = u'Client not registered'
            time.sleep(1.0)

        else:
            #wait for event (blocking by default) until end of timeout
            try:
                #wait for message
                poll_key = u'rpc-%s' % params[u'pollKey']
                msg = bus.pull(poll_key, POLL_TIMEOUT)

                #prepare output
                message[u'error'] = False
                message[u'data'] = msg[u'message']
                logger.debug(u'polling received %s' % message)

            except NoMessageAvailable:
                message[u'message'] = u'No message available'
                time.sleep(1.0)

            except:
                logger.exception(u'Poll exception')
                crash_report.report_exception({
                    u'message': u'Poll exception'
                })
                message[u'message'] = u'Internal error'
                time.sleep(5.0)

    #and return it
    return json.dumps(message)

@app.route(u'/<path:path>')
@authenticate()
def default(path):
    """
    Servers static files from HTML_DIR.
    """
    return bottle.static_file(path, HTML_DIR)

@app.route(u'/')
@authenticate()
def index():
    """
    Return a default document if no path was specified.
    """
    return bottle.static_file(u'index.html', HTML_DIR)

@app.route(u'/debug')
def debug():
    """
    This lets us see how many /sub requests are active.
    """
    bottle.response.content_type = u'text/plain'

    # Using yield because this makes it easier to add
    # additional output.
    yield(u'polling = %d\n' % polling)


