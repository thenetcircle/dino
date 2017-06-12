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

__author__ = 'Oscar Eriksson <oscar@thenetcircle.com>'

logger = logging.getLogger(__name__)


def create_app():
    _app = Flask(__name__)

    # used for encrypting cookies for handling sessions
    _app.config['SECRET_KEY'] = 'secret!fdsa'
    message_queue_type = environ.env.config.get(ConfigKeys.TYPE, domain=ConfigKeys.QUEUE, default=None)
    if message_queue_type is None:
        raise RuntimeError('no message queue type specified')

    message_queue = None
    message_channel = None

    if message_queue_type == 'redis':
        message_queue = environ.env.config.get(ConfigKeys.HOST, domain=ConfigKeys.QUEUE, default='')
    elif message_queue_type == 'amqp':
        queue_host = environ.env.config.get(ConfigKeys.HOST, domain=ConfigKeys.QUEUE, default='')
        message_queue = 'amqp://%s:%s@%s:%s%s' % (
            environ.env.config.get(ConfigKeys.USER, domain=ConfigKeys.QUEUE, default=''),
            environ.env.config.get(ConfigKeys.PASSWORD, domain=ConfigKeys.QUEUE, default=''),
            queue_host.split(';')[0],
            environ.env.config.get(ConfigKeys.PORT, domain=ConfigKeys.QUEUE, default=''),
            environ.env.config.get(ConfigKeys.VHOST, domain=ConfigKeys.QUEUE, default=''),
        )

        message_channel = 'dino_%s' % environ.env.config.get(ConfigKeys.ENVIRONMENT)

    logger.info('message_queue: %s' % message_queue)

    _socketio = SocketIO(
            _app,
            logger=logger,
            engineio_logger=os.environ.get('DINO_DEBUG', '0') == '1',
            async_mode='eventlet',
            message_queue=message_queue,
            channel=message_channel)

    _app.wsgi_app = ProxyFix(_app.wsgi_app)
    return _app, _socketio


app, socketio = create_app()

import dino.endpoint.sockets
