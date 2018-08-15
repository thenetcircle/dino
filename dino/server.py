#!/usr/bin/env python

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import logging
from flask import Flask
from flask_socketio import SocketIO
from werkzeug.contrib.fixers import ProxyFix

from dino import environ
from dino.config import ConfigKeys

__author__ = 'Oscar Eriksson <oscar@gmail.com>'

logger = logging.getLogger(__name__)
logging.getLogger('amqp').setLevel(logging.INFO)
logging.getLogger('kafka.conn').setLevel(logging.INFO)


def create_app():
    _app = Flask(__name__)

    # used for encrypting cookies for handling sessions
    _app.config['SECRET_KEY'] = 'abc492ee-9739-11e6-a174-07f6b92d4a4b'

    message_queue_type = environ.env.config.get(ConfigKeys.TYPE, domain=ConfigKeys.QUEUE, default=None)
    if message_queue_type is None and not (len(environ.env.config) == 0 or environ.env.config.get(ConfigKeys.TESTING)):
        raise RuntimeError('no message queue type specified')

    if message_queue_type == 'redis':
        message_queue = environ.env.config.get(ConfigKeys.HOST, domain=ConfigKeys.QUEUE, default='')
    elif message_queue_type == 'amqp':
        queue_host = environ.env.config.get(ConfigKeys.HOST, domain=ConfigKeys.QUEUE, default='')
        message_queue = ';'.join(['amqp://%s:%s@%s:%s%s' % (
            environ.env.config.get(ConfigKeys.USER, domain=ConfigKeys.QUEUE, default=''),
            environ.env.config.get(ConfigKeys.PASSWORD, domain=ConfigKeys.QUEUE, default=''),
            host,
            environ.env.config.get(ConfigKeys.PORT, domain=ConfigKeys.QUEUE, default=''),
            environ.env.config.get(ConfigKeys.VHOST, domain=ConfigKeys.QUEUE, default=''),
        ) for host in queue_host.split(';')])

    else:
        raise RuntimeError('unknown message queue type specified')

    message_channel = 'dino_%s' % environ.env.config.get(ConfigKeys.ENVIRONMENT, default='test')
    logger.info('message_queue: %s' % message_queue)

    _socketio = SocketIO(
            _app,
            logger=logger,
            engineio_logger=os.environ.get('DINO_DEBUG', '0') == '1',
            async_mode='eventlet',
            message_queue=message_queue,
            channel=message_channel)

    # preferably "emit" should be set during env creation, but the socketio object is not created until after env is
    environ.env.out_of_scope_emit = _socketio.emit

    _app.wsgi_app = ProxyFix(_app.wsgi_app)
    return _app, _socketio


app, socketio = create_app()

import dino.endpoint.sockets
