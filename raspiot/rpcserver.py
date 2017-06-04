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
import uuid
from gevent import queue
from gevent import monkey; monkey.patch_all()
from gevent import pywsgi 
from gevent.pywsgi import LoggingLogAdapter
from .utils import NoMessageAvailable, MessageResponse, MessageRequest, CommandError
import bottle
from bottle import auth_basic
from passlib.hash import sha256_crypt
import functools
from .libs.raspiotconf import RaspiotConf

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
app = bottle.app()
server = None

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

def get_app(debug_enabled):
    """
    Return web server

    Returns:
        object: bottle instance
    """
    global logger, app

    #logging (in raspiot.conf file, module name is 'rpcserver')
    logging.basicConfig(level=logging.DEBUG, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')
    logger = logging.getLogger(u'RpcServer')
    if debug_enabled:
        logger.setLevel(logging.DEBUG)

    #load auth
    load_auth()

    return app

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
    global server, app

    try:
        if key is not None and len(key)>0 and cert is not None and len(cert)>0:
            #start HTTPS server
            logger.info(u'Starting HTTPS server on %s:%d' % (host, port))
            server_logger = LoggingLogAdapter(logger, logging.DEBUG)
            server = pywsgi.WSGIServer((host, port), app, keyfile=key, certfile=cert, log=server_logger)
            server.serve_forever()

        else:
            #start HTTP server
            logger.info(u'Starting HTTP server on %s:%d' % (host, port))
            app.run(server=u'gevent', host=host, port=port, quiet=True, debug=False, reloader=False)

    except KeyboardInterrupt:
        #user stops raspiot, close server properly
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
    if sessions.has_key(session_key) and sessions[session_key]>=time.time():
        #user still logged, update session timeout
        sessions[session_key] = time.time() + SESSION_TIMEOUT
        return True

    #check auth
    if auth_config[u'accounts'].has_key(username):
        if sha256_crypt.verify(password, auth_config[u'accounts'][username]):
            #auth is valid, save session
            sessions[session_key] = time.time() + SESSION_TIMEOUT
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

    Returns:
        MessageResonse: command response (None if broadcasted message)
    """
    #get bus
    bus = app.config[u'sys.bus']

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

    Returns:
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

    Returns:
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
        logger.debug(u'response: %s' % resp)
        if not resp[u'error']:
            filename = os.path.basename(resp[u'data'])
            root = os.path.dirname(resp[u'data'])
            logger.debug(u'Download file root=%s filename=%s' % (root, filename))
            return bottle.static_file(filename=filename, root=root, download=True)
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

    Returns:
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

    Returns:
        Dict: map of modules with their configuration, devices, commands...
    """
    logger.debug(u'Request inventory for available modules')
    modules = app.config[u'sys.inventory'].get_modules()
    
    #inject config of installed modules
    for module in modules:
        if modules[module][u'installed']:
            modules[module][u'config'] = app.config[u'mod.%s' % module].get_module_config()

    #inject module pending status (installed but not loaded yet or uninstalled but still loaded => need restart)
    conf = RaspiotConf()
    config = conf.as_dict()
    for module in modules:
        modules[module][u'pending'] = False
        if module in config[u'general'][u'modules'] and not modules[module][u'installed']:
            #install pending
            modules[module][u'pending'] = True
        if module not in config[u'general'][u'modules'] and modules[module][u'installed']:
            #uninstall pending
            modules[module][u'pending'] = True

    logger.debug(u'Modules: %s' % modules)
    return json.dumps(modules)

@app.route(u'/devices', method=u'POST')
@authenticate()
def devices():
    """
    Return all devices

    Returns:
        dict: all devices by modules
    """
    #request each loaded module for its devices
    devices = {}
    for module in app.config:
        if module.startswith(u'mod.'):
            _module = module.replace(u'mod.', '')
            logger.debug(u'Request "%s" config' % _module)
            response = send_command(u'get_module_devices', _module, {})
            if not response[u'error']:
                devices[_module] = response[u'data']
            else:
                devices[_module] = None
    logger.debug(u'Devices: %s' % devices)

    return json.dumps(devices)

@app.route(u'/providers', method=u'POST')
@authenticate()
def providers():
    """
    Returns all providers

    Returns:
        dict: all providers by type
    """
    providers = app.config[u'sys.inventory'].get_providers()

    logger.debug(u'Providers: %s' % providers)
    return json.dumps(providers)

@app.route(u'/registerpoll', method=u'POST')
@authenticate()
def registerpoll():
    """
    Register poll

    Returns:
        dict: {'pollkey':''}
    """
    #subscribe to bus
    poll_key = unicode(uuid.uuid4())
    if app.config.has_key(u'sys.bus'):
        logger.debug(u'subscribe %s' % poll_key)
        app.config[u'sys.bus'].add_subscription(u'rpc-%s' % poll_key)

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

    Returns:
        dict: map of received event
    """
    with pollcounter():
        params = bottle.request.json
        #response content type.
        bottle.response.content_type = u'application/json'

        #get message bus
        bus = app.config[u'sys.bus']

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
                logger.exception(u'poll exception')
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


