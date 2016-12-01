# import gevent.monkey
# import sqlalchemy_gevent
import eventlet

# need to monkey patch some standard functions in python since they don't natively support async mode
# gevent.monkey.patch_all()
# sqlalchemy_gevent.patch_all()
eventlet.monkey_patch()

# keep this import; even though unused, gunicorn needs it, otherwise it will not start
from dino.server import socketio, app
