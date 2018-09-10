from dino.environ import GNEnvironment

from dino.config import ConfigKeys
from kombu import pools

pools.set_limit(4096)  # default is 200

from kombu import Exchange
from kombu import Queue
from kombu import Connection
from kombu.pools import producers
from eventlet.semaphore import Semaphore

import eventlet
import traceback
import logging
import time
import sys
import socket


logger = logging.getLogger(__name__)


class RedisPubSub(object):
    def __init__(self, env: GNEnvironment):
        self.env = env
        conf = env.config
        args = sys.argv

        for a in ['--bind', '-b']:
            bind_arg_pos = [i for i, x in enumerate(args) if x == a]
            if len(bind_arg_pos) > 0:
                bind_arg_pos = bind_arg_pos[0]
                break

        try:
            port = args[bind_arg_pos + 1].split(':')[1]
        except TypeError:
            logger.info('skipping pubsub setup, no port specified')
            return

        queue_host = conf.get(ConfigKeys.HOST, domain=ConfigKeys.QUEUE, default=None)
        exchange = conf.get(ConfigKeys.EXCHANGE, domain=ConfigKeys.QUEUE, default='node_exchange')
        queue_db = conf.get(ConfigKeys.DB, domain=ConfigKeys.QUEUE, default=0)
        queue_name = conf.get(ConfigKeys.QUEUE, domain=ConfigKeys.QUEUE, default=None)
        hostname = socket.gethostname()

        if queue_name is None or len(queue_name.strip()) == 0:
            queue_name = 'node_queue_%s_%s_%s' % (
                conf.get(ConfigKeys.ENVIRONMENT),
                hostname,
                port
            )

        self.env.queue_connection = Connection(queue_host, transport_options={'db': queue_db})
        logger.info('queue connection: {}'.format(str(self.env.queue_connection)))
        self.env.queue_name = queue_name
        self.env.exchange = Exchange(exchange, type='fanout')
        self.env.queue = Queue(self.env.queue_name, self.env.exchange)
