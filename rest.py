import eventlet

# need to monkey patch some standard functions in python since they don't natively support async mode
eventlet.monkey_patch()

# keep this import; even though unused, gunicorn needs it, otherwise it will not start
from dino.hooks import *
from dino.restful import app

from dino import environ
environ.env.node = 'rest'
environ.env.observer.emit('on_startup_done', (None, None))
