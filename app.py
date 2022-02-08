import eventlet

# need to monkey patch some standard functions in python since they don't natively support async mode
eventlet.monkey_patch()

# let the rest node start first and send the restart event, and not all nodes
# query for the same thing at the same time, some can get from the cache after
# the first one has queried
import time
import random
time.sleep(int(5+random.random()*10))

import logging
logging.getLogger('kafka').setLevel(logging.INFO)
logging.getLogger('yapsy').setLevel(logging.INFO)

# keep this import; even though unused, gunicorn needs it, otherwise it will not start
from dino.server import socketio, app

from dino import environ
environ.env.node = 'app'
