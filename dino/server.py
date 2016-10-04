from flask import session, Flask
from flask_socketio import SocketIO

from dino.env import env
from dino.env import ConfigKeys

__author__ = 'Oscar Eriksson <oscar@thenetcircle.com>'


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secret!fdsa'
    socketio = SocketIO(app, logger=env.config.get(ConfigKeys.LOGGER),
                        message_queue='redis://%s' % env.config.get(ConfigKeys.REDIS_HOST))

    env.config[ConfigKeys.SESSION] = session
    return app, socketio


app, socketio = create_app()

import dino.endpoint.sockets
