#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Based on long poll example from https://github.com/larsks/pubsub_example
Encryption based on example from XXX
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
from .utils import NoMessageAvailable, MessageResponse, MessageRequest
import bottle
from bottle import auth_basic
from passlib.hash import sha256_crypt
import functools

__all__ = ['app']

#constants
BASE_DIR = '/opt/raspiot/'
HTML_DIR = os.path.join(BASE_DIR, 'html')
AUTH_FILE = '/etc/raspiot/auth.conf'
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
        logger.debug('%s %s %s %s' % (
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
        logger.debug('auth.conf: %s' % auth_config['accounts'])

        if len(auth_config['accounts'])>0 and auth_config['enabled']:
            auth_enabled = True
        else:
            auth_enabled = False
        logger.debug('Auth enabled: %s' % auth_enabled)
    except:
        logger.exception('Unable to load auth file. Auth disabled:')

def get_app(debug_enabled):
    """
    Return web server
    @return bottle instance
    """
    global logger, app

    #logging (in raspiot.conf file, module name is 'rpcserver')
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s : %(message)s")
    logger = logging.getLogger('RpcServer')
    if debug_enabled:
        logger.setLevel(logging.DEBUG)

    #load auth
    load_auth()

    return app

def start(host='0.0.0.0', port=80, key=None, cert=None):
    """
    Start RPC server
    Start by default unsecure web server
    You can configure SSL server specifying key and cert parameters
    @param host: host (default computer is accessible on localt network)
    @param port: port to listen to (by default is standart HTTP port 80)
    @param key: SSL key file
    @param cert: SSL certificate file
    """
    global server, app

    try:
        if key is not None and len(key)>0 and cert is not None and len(cert)>0:
            #start HTTPS server
            logger.info('Starting HTTPS server on %s:%d' % (host, port))
            server_logger = LoggingLogAdapter(logger, logging.DEBUG)
            server = pywsgi.WSGIServer((host, port), app, keyfile=key, certfile=cert, log=server_logger)
            server.serve_forever()

        else:
            #start HTTP server
            logger.info('Starting HTTP server on %s:%d' % (host, port))
            app.run(server='gevent', host=host, port=port, quiet=True, debug=False, reloader=False)

    except KeyboardInterrupt:
        #user stops raspiot, close server properly
        if not server.closed:
            server.close()

def check_auth(username, password):
    """
    Check auth
    """
    global auth_config_loaded, auth_config, sessions, SESSION_TIMEOUT

    #check session
    ip = bottle.request.environ.get('REMOTE_ADDR')
    session_key = '%s-%s' % (ip, username)
    if sessions.has_key(session_key) and sessions[session_key]>=time.time():
        #user still logged, update session timeout
        sessions[session_key] = time.time() + SESSION_TIMEOUT
        return True

    #check auth
    if auth_config['accounts'].has_key(username):
        if sha256_crypt.verify(password, auth_config['accounts'][username]):
            #auth is valid, save session
            sessions[session_key] = time.time() + SESSION_TIMEOUT
            return True
        else:
            #invalid password
            logger.warning('Invalid password for user "%s"' % username)
            return False
    else:
        #username doesn't exist
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
                logger.debug('username=%s password=%s' % (username, password))
                if username is None or not check_auth(username, password):
                    err = bottle.HTTPError(401, 'Access denied')
                    err.add_header('WWW-Authenticate', 'Basic realm="private"')
                    return err 
            return func(*args, **kwargs)

        return wrapper

    return decorator

def send_command(command, to, params):
    """
    Send specified command
    @param command: command to execute
    @param to: command recipient
    @param parmas: command parameters
    @return command response (None if broadcasted message)
    """
    #get bus
    bus = app.config['sys.bus']

    #prepare and send command
    request = MessageRequest()
    request.command = command
    request.to = to
    request.from_ = 'rpcserver'
    request.params = params
    return bus.push(request)


@app.route('/upload', method='POST')
@authenticate()
def upload():
    """
    Upload file
    """
    path = None
    try:
        #get form fields
        command = bottle.request.forms.get('command')
        logger.debug('command=%s' % str(command))
        to = bottle.request.forms.get('to')
        logger.debug('to=%s' % str(to))
        params = bottle.request.forms.get('params')
        logger.debug('params=%s' % str(params))
        if params is None:
            params = {}

        #check params
        if command is None or to is None:
            #not allowed, missing parameters
            msg = MessageResponse()
            msg.message = 'Missing parameters'
            msg.error = True
            resp = msg.to_dict()

        else:
            #get file
            upload = bottle.request.files.get('file')
            path = os.path.join('/tmp', upload.filename)

            #remove file if already exists
            if os.path.exists(path):
                os.remove(path)
                time.sleep(0.25)

            #save file locally
            upload.save(path)

            #add filepath in params
            params['filepath'] = path

            #execute specified command
            logger.debug('Upload command:%s to:%s params:%s' % (str(command), str(to), str(params)))
            resp = send_command(command, to, params)

    except Exception as e:
        logger.exception('Exception in upload:')
        #something went wrong
        msg = MessageResponse()
        msg.message = str(e)
        msg.error = True
        resp = msg.to_dict()

        #delete uploaded file if possible
        if path:
            logger.debug('Delete uploaded file')
            os.remove(path)

    return resp

@app.route('/download', method='GET')
@authenticate()
def download():
    """
    Download file
    @info: need to have command, to and params values on uri:
    """
    try:
        #prepare params
        command = bottle.request.query.command
        to = bottle.request.query.to
        params = {}
        logger.debug('Download params: command=%s to=%s params=%s' % (command, to, params))

        try:
            params = dict(bottle.request.query)
            #remove useless parameters
            if params.has_key('command'):
                del params['command']
            if params.has_key('to'):
                del params['to']
        except:
            params = {}

        #request full filepath from module (string format)
        resp = send_command(command, to, params)
        logger.debug('response: %s' % resp)
        if not resp['error']:
            filename = os.path.basename(resp['data'])
            root = os.path.dirname(resp['data'])
            logger.debug('Download file root=%s filename=%s' % (root, filename))
            return bottle.static_file(filename=filename, root=root, download=True)
        else:
            #error during filepath retrieving
            raise Exception(resp['message'])

    except Exception as e:
        logger.exception('Exception in download:')
        #something went wrong
        msg = MessageResponse()
        msg.message = str(e)
        msg.error = True
        resp = msg.to_dict()

    return resp

@app.route('/command', method=['POST','GET'])
@authenticate()
def command():
    """
    Execute command on raspiot
    """
    logger.debug('COMMAND method=%s data=[%d]: %s' % (str(bottle.request.method), len(bottle.request.params), str(bottle.request.json)))

    try:
        #prepare data to push
        if bottle.request.method=='GET':
            #GET request
            command = bottle.request.query.command
            to = bottle.request.query.to
            params = bottle.request.query.params
            #handle params: 
            # - could be specified as params field with json 
            # - or not specified in which case parameters are directly specified in query string
            if len(params)==0:
                #no params value specified, use all query string
                params = dict(bottle.request.query)
                #remove useless parameters
                if params.has_key('command'):
                    del params['command']
                if params.has_key('to'):
                    del params['to']
            else:
                #params specified in query string, unjsonify it
                try:
                    params = json.loads(params)
                except:
                    params = None

        else:
            #POST request (need json)
            tmp_params = bottle.request.json
            if tmp_params.has_key('to'):
                to = tmp_params['to']
                del tmp_params['to']
            if tmp_params.has_key('command'):
                command = tmp_params['command']
                del tmp_params['command']
            if len(tmp_params)>0:
                params = tmp_params['params']

        #execute command
        resp = send_command(command, to, params)

    except Exception as e:
        logger.exception('Exception in command:')
        #something went wrong
        msg = MessageResponse()
        msg.message = str(e)
        msg.error = True
        resp = msg.to_dict()

    return resp

@app.route('/modules', method='POST')
@authenticate()
def modules():
    """
    Return configurations for all loaded modules
    """
    #request each loaded module for its config
    configs = {}
    for module in app.config:
        if module.startswith('mod.'):
            _module = module.replace('mod.', '')

            logger.debug('Request "%s" config' % _module)
            #response = send_command('get_module_config', _module, {})
            #if not response['error']:
            #    configs[_module] = response['data']
            #else:
            #    configs[_module] = None
            configs[_module] = {}
            configs[_module]['config'] = app.config[module].get_module_config()
            configs[_module]['description'] = app.config[module].MODULE_DESCRIPTION
            configs[_module]['locked'] = app.config[module].MODULE_LOCKED

    logger.debug('Configs: %s' % configs)

    return json.dumps(configs)

@app.route('/devices', method='POST')
@authenticate()
def devices():
    """
    Return all devices
    """
    #request each loaded module for its devices
    devices = {}
    for module in app.config:
        if module.startswith('mod.'):
            _module = module.replace('mod.', '')
            logger.debug('Request "%s" config' % _module)
            response = send_command('get_module_devices', _module, {})
            if not response['error']:
                devices[_module] = response['data']
            else:
                devices[_module] = None
    logger.debug('Devices: %s' % devices)

    return json.dumps(devices)

@app.route('/registerpoll', method='POST')
@authenticate()
def registerpoll():
    """
    Register poll
    """
    #subscribe to bus
    poll_key = str(uuid.uuid4())
    if app.config.has_key('sys.bus'):
        logger.debug('subscribe %s' % poll_key)
        app.config['sys.bus'].add_subscription('rpc-%s' % poll_key)

    #return response
    bottle.response.content_type = 'application/json'
    return json.dumps({'pollKey':poll_key})

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
    """
    with pollcounter():
        params = bottle.request.json
        #response content type.
        bottle.response.content_type = 'application/json'

        #get message bus
        bus = app.config['sys.bus']

        #init message
        message = {'error':True, 'data':None, 'message':''}

        #process poll
        if not bus:
            #bus not available yet
            logger.debug('polling: bus not available')
            message['message'] = 'Bus not available'
            time.sleep(1.0)

        elif not params.has_key('pollKey'):
            #rpc client no registered yet
            logger.debug('polling: registration key must be sent to poll request')
            message['message'] = 'Polling key is missing'
            time.sleep(1.0)

        elif not bus.is_subscribed('rpc-%s' % params['pollKey']):
            #rpc client no registered yet
            logger.debug('polling: rpc client must be registered before polling')
            message['message'] = 'Client not registered'
            time.sleep(1.0)

        else:
            #wait for event (blocking by default) until end of timeout
            try:
                #wait for message
                poll_key = 'rpc-%s' % params['pollKey']
                msg = bus.pull(poll_key, POLL_TIMEOUT)

                #prepare output
                message['error'] = False
                message['data'] = msg['message']
                logger.debug('polling received %s' % message)

            except NoMessageAvailable:
                message['message'] = 'No message available'
                time.sleep(1.0)

            except:
                logger.exception('poll exception')
                message['message'] = 'Internal error'
                time.sleep(5.0)

    #and return it
    return json.dumps(message)

@app.route('/<path:path>')
@authenticate()
def default(path):
    """
    Servers static files from HTML_DIR.
    """
    return bottle.static_file(path, HTML_DIR)

@app.route('/')
@authenticate()
def index():
    """
    Return a default document if no path was specified.
    """
    return bottle.static_file('index.html', HTML_DIR)

@app.route('/debug')
def debug():
    """
    This lets us see how many /sub requests are active.
    """
    bottle.response.content_type = 'text/plain'

    # Using yield because this makes it easier to add
    # additional output.
    yield('polling = %d\n' % polling)


