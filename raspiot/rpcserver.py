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
import gevent
from gevent import queue
from gevent import monkey; monkey.patch_all()
from bus import NoMessageAvailable
from bus import MessageResponse, MessageRequest
import bottle
from bottle import auth_basic
from passlib.hash import sha256_crypt

__all__ = ['app']

#constants
BASE_DIR = '/opt/raspiot/'
HTML_DIR = os.path.join(BASE_DIR, 'html')
AUTH_FILE = '/etc/raspiot/auth.conf'
POLL_TIMEOUT = 60

#logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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

#main app
app = bottle.app()
app.install(bottle_logger)

#globals
polling = 0
subscribed = False
subscriptions = {}
auth_config_loaded = False
auth_config = {}

def subscribe_bus():
    global subscribed

    if not subscribed and app.config.has_key('sys.bus'):
        logger.debug('subscribe')
        app.config['sys.bus'].add_subscription('json')
        subscribed = True

    #if subscribed:
    #    return app.config['sys.bus']
    #else:
    #    return None
    return app.config['sys.bus']

def dictToList(d):
    """
    convert dict to list
    dict key is inserted in dict item as id
    """
    l = []
    try:
        if not isinstance(d, dict):
            #not a dict!
            logger.fatal('dictToList: Unable to convert non dict variable')
            logger.debug('%s = %s' % (type(d), str(d)))
        else:
            for key in d:
                if isinstance(d[key], dict):
                    tmp = d[key]
                else:
                    tmp = {}
                    tmp['value'] = d[key]
                tmp['__key'] = key
                l.append(tmp)
    except:
        logger.exception('dictToList exception:')
        logger.debug('%s = %s' % (type(d), str(d)))
    return l

def check_auth(username, password):
    """
    Check auth
    """
    global auth_config_loaded, auth_config
    #load auth file if necessary
    if not auth_config_loaded:
        try:
            execfile(AUTH_FILE, auth_config)
            logger.debug('auth.conf: %s' % auth_config['accounts'])
        except:
            logger.exception('Unable to load auth file. Auth disabled:')
        auth_config_loaded = True

    #check auth
    if len(auth_config['accounts'])>0 and auth_config['enabled']:
        if auth_config['accounts'].has_key(username):
            if sha256_crypt.verify(password, auth_config['accounts'][username]):
                #auth is valid
                return True
            else:
                #invalid password
                logger.warning('Invalid password for user "%s"' % username)
                return False
        else:
            #username doesn't exist
            logger.warning('Invalid username "%s"' % username)
            return False
    else:
        #auth disabled
        return True

def auth_enabled():
    """
    Return auth status
    @return: True if auth enabled, False if auth disabled
    """
    global auth_config_loaded, auth_config
    return len(auth_config['accounts'])>0 and auth_config['enabled']

def execute_command(command, to, params):
    """
    Execute specified command
    """
    #get bus
    bus = app.config['sys.bus']

    #prepare and send command
    request = MessageRequest()
    request.command = command
    request.to = to
    request.params = params
    return bus.push(request)


@app.route('/upload', method='POST')
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
            resp = execute_command(command, to, params)

    except Exception, e:
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

        
@app.route('/command', method='POST')
@app.route('/command', method='GET')
#@auth_basic(check_auth)
def command():
    """
    Execute command on system
    """
    logger.debug('COMMAND method=%s data=[%d]: %s' % (str(bottle.request.method), len(bottle.request.params), str(bottle.request.json)))

    try:
        #prepare data to push
        if bottle.request.method=='GET':
            #GET request
            tmp_params = bottle.request.query
            logger.debug('params: %s' % dir(params))
            command = None
            to = None
            if 'to' in tmp_params.keys():
                to = tmp_params['to']
                del tmp_params['to']
            if 'command' in tmp_params.keys():
                command = tmp_params['command']
                del tmp_params['command']
            if len(tmp_params)>0:
                params = tmp_params['params']

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
        resp = execute_command(command, to, params)

    except Exception, e:
        logger.exception('Exception in command:')
        #something went wrong
        msg = MessageResponse()
        msg.message = str(e)
        msg.error = True
        resp = msg.to_dict()

    return resp

@app.route('/registerpoll', method='POST')
#@auth_basic(check_auth)
def registerpoll():
    bottle.response.content_type = 'application/json'
    poll_key = str(uuid.uuid4())
    subscriptions[poll_key] = time.time()
    if app.config.has_key('sys.bus'):
        logger.debug('subscribe %s' % poll_key)
        app.config['sys.bus'].add_subscription('rpc-%s' % poll_key)
    return json.dumps({'pollKey':poll_key})

@contextmanager
def pollcounter():
    global polling
    polling += 1
    yield
    polling -= 1

@app.route('/poll', method='POST')
#@auth_basic(check_auth)
def poll():
    """
    This is the endpoint for long poll clients.
    """
    with pollcounter():
        params = bottle.request.json
        # Make sure response will have the correct content type.
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
#@auth_basic(check_auth)
def default(path):
    """
    Servers static files from HTML_DIR.
    """
    return bottle.static_file(path, HTML_DIR)

@app.route('/modules', method='POST')
#@auth_basic(check_auth)
def modules():
    """
    Returns loaded modules in app to inject associated modules in webapp
    @return mod.XXX modules only
    """
    modules = []
    for module in app.config:
        if module.startswith('mod.'):
            #external module found, return it
            modules.append(module.replace('mod.',''))
    return json.dumps(modules)

@app.route('/')
#@auth_basic(check_auth)
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


