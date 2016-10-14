from flask import Flask
from flask_socketio import SocketIO

from dino import environ
from dino.config import ConfigKeys

__author__ = 'Oscar Eriksson <oscar@thenetcircle.com>'


def create_app():
    _app = Flask(__name__)
    _app.config['SECRET_KEY'] = 'secret!fdsa'

    # TODO: let the queue config contain the complete value for message_queue, so no queue can be used
    _socketio = SocketIO(
            _app,
            logger=environ.env.logger,
            engineio_logger=False,
            message_queue='redis://%s' % environ.env.config.get(
                    ConfigKeys.HOST,
                    domain=ConfigKeys.QUEUE, default=''))

    return _app, _socketio


app, socketio = create_app()

import dino.endpoint.sockets
