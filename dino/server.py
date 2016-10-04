from flask import session, Flask
from flask_socketio import SocketIO
from functools import wraps

from dino.env import env
from dino.env import ConfigKeys

__author__ = 'Oscar Eriksson <oscar@thenetcircle.com>'


class _SocketIO(object):
    _socketio = None

    def __init__(self, _socketio):
        self._socketio = _socketio

    def on(self, message, namespace=None):
        def factory(view_func):
            @wraps(view_func)
            def decorator(*args, **kwargs):
                if env.config.get(ConfigKeys.TESTING):
                    view_func(*args, **kwargs)
                else:
                    self._socketio.on(message, namespace)
            return decorator
        return factory


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secret!fdsa'
    socketio = SocketIO(app, logger=env.config.get(ConfigKeys.LOGGER),
                        message_queue='redis://%s' % env.config.get(ConfigKeys.REDIS_HOST))

    env.config[ConfigKeys.SESSION] = session
    return app, _SocketIO(socketio)


app, socketio = create_app()

import dino.endpoint.sockets
