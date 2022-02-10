import eventlet

# need to monkey patch some standard functions in python since they don't natively support async mode
eventlet.monkey_patch()

import logging
logging.getLogger('kafka').setLevel(logging.INFO)
logging.getLogger('kafka.protocol.parser').setLevel(logging.INFO)
logging.getLogger('kafka.producer.sender').setLevel(logging.INFO)
logging.getLogger('kafka.producer.record_accumulator').setLevel(logging.INFO)

# keep this import; even though unused, gunicorn needs it, otherwise it will not start
from dino.hooks.startup import *
from dino.web import app

from dino import environ
environ.env.node = 'web'

environ.env.observer.emit('on_startup_done', (None, None))
