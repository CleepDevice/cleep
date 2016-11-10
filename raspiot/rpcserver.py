#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Based on long poll example from https://github.com/larsks/pubsub_example
"""

import os
import logging
import sys
import argparse
import json
from contextlib import contextmanager
import time
import uuid

#import gevent
import gevent
from gevent import queue
from gevent import monkey; monkey.patch_all()
from bus import NoMessageAvailable
from bus import MessageResponse, MessageRequest
import bottle

__all__ = ['app']

# This lets us track how many clients are currently connected.
polling = 0

BASE_DIR = '/opt/raspiot/'
HTML_DIR = os.path.join(BASE_DIR, 'html')
POLL_TIMEOUT = 60

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

app = bottle.app()

subscribed = False

subscriptions = {}

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


@app.route('/command', method='POST')
def command():
    """
    Execute command on system
    """
    logger.debug('COMMAND data [%d]: %s' % (len(bottle.request.params), str(bottle.request.json)))

    #get app bus
    bus = app.config['sys.bus']

    #get command params
    params = bottle.request.json

    #push message to bus
    try:
        #prepare data to push
        request = MessageRequest()
        if params.has_key('to'):
            request.to = params['to']
            del params['to']
        if params.has_key('command'):
            request.command = params['command']
            del params['command']
        if len(params)>0:
            request.params = params['params']

        #send request
        resp = bus.push(request)

    except Exception, e:
        logger.exception('webserver.command exception')
        #something went wrong
        msg = MessageResponse()
        msg.message = str(e)
        msg.error = True
        resp = msg.to_dict()

    #convert dict to list to have easy to use array in js
    #if resp['data']!=None and isinstance(resp['data'], dict):
    #    resp['data'] = dictToList(resp['data'])

    return resp

#@contextmanager
#def wait_for_message():
#    """
#    Wait for message to send to client
#    """
#    with subscribe_bus() as bus:
#        message = {'error':True, 'data':None, 'message':''}
#        if bus:
#            #wait for event (blocking by default) until end of timeout
#            try:
#                msg = bus.pull('json', POLL_TIMEOUT)
#                #prepare output
#                message['error'] = False
#                message['data'] = msg['message']
#                logger.debug('polling received %s' % message)
#            except NoMessageAvailable:
#                message['message'] = 'No message available'
#                time.sleep(1.0)
#            except:
#                logger.exception('poll exception')
#                message['message'] = 'Internal error'
#                time.sleep(5.0)
#        else:
#            #bus not available yet
#            logger.info('polling: bus not available')
#            message['message'] = 'Bus not available'
#            time.sleep(1.0)
#
#    #and return it
#    return json.dumps(message)

@app.route('/registerpoll', method='POST')
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
def default(path):
    """
    Servers static files from HTML_DIR.
    """
    return bottle.static_file(path, HTML_DIR)

@app.route('/modules', method='POST')
def modules():
    """
    Returns loaded modules in app to inject associated modules in webapp
    @return ext.XXX modules only
    """
    modules = []
    for module in app.config:
        if module.startswith('ext.'):
            #external module found, return it
            modules.append(module.replace('ext.',''))
    return json.dumps(modules)

@app.route('/')
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


