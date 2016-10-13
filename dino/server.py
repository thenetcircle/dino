from flask import Flask
from flask_socketio import SocketIO

from dino import environ

__author__ = 'Oscar Eriksson <oscar@thenetcircle.com>'


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secret!fdsa'

    # TODO: let the queue config contain the complete value for message_queue, so no queue can be used
    socketio = SocketIO(
            app,
            logger=environ.env.logger,
            engineio_logger=False,
            message_queue='redis://%s' % environ.env.config.get(
                    environ.ConfigKeys.HOST,
                    domain=environ.ConfigKeys.QUEUE, default=''))

    return app, socketio


app, socketio = create_app()

import dino.endpoint.sockets
