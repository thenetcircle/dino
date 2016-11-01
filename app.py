import gevent.monkey

# need to monkey patch some standard functions in python since they don't natively support async mode
gevent.monkey.patch_all()

# keep this import; even though unused, gunicorn needs it, otherwise it will not start
from dino.server import socketio, app
