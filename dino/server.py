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
from flask import Flask
from flask_socketio import SocketIO
from werkzeug.contrib.fixers import ProxyFix

from dino import environ
from dino.config import ConfigKeys

__author__ = 'Oscar Eriksson <oscar@thenetcircle.com>'


def create_app():
    _app = Flask(__name__)

    # used for encrypting cookies for handling sessions
    _app.config['SECRET_KEY'] = 'secret!fdsa'

    _socketio = SocketIO(
            _app,
            logger=environ.env.logger,
            engineio_logger=os.environ.get('DINO_DEBUG', '0') == '1',
            async_mode='eventlet',
            message_queue=environ.env.config.get(ConfigKeys.HOST, domain=ConfigKeys.QUEUE, default=''))

    _app.wsgi_app = ProxyFix(_app.wsgi_app)
    return _app, _socketio


app, socketio = create_app()

import dino.endpoint.sockets
