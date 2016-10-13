from flask import Flask
from flask_socketio import SocketIO

import dino.environ

__author__ = 'Oscar Eriksson <oscar@thenetcircle.com>'


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secret!fdsa'

    # TODO: let the queue config contain the complete value for message_queue, so no queue can be used
    socketio = SocketIO(
            app,
            logger=dino.environ.env.logger,
            engineio_logger=False,
            message_queue='redis://%s' % dino.environ.env.config.get(
                    dino.environ.ConfigKeys.HOST,
                    domain=dino.environ.ConfigKeys.QUEUE, default=''))

    return app, socketio


app, socketio = create_app()

import dino.endpoint.sockets
