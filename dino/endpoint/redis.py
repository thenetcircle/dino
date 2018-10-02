from kombu import pools
pools.set_limit(200)  # default is 200

from dino.config import ConfigKeys
from dino.endpoint.base import BasePublisher

from kombu import Exchange
from kombu import Queue
from kombu import Connection

import logging

logger = logging.getLogger(__name__)


class RedisPublisher(BasePublisher):
    """
    similar to AmqpPublisher, but differs in initialization since we can choose redis db and don't have virtual hosts
    """
    def __init__(self, env, is_external_queue: bool):
        super().__init__(env, is_external_queue, queue_type='redis', logger=logger)

        conf = env.config

        bind_port = self.get_port()
        if bind_port is None:
            logger.info('skipping pubsub setup, no port specified')
            return

        queue_host = conf.get(ConfigKeys.HOST, domain=self.domain_key, default=None)
        exchange = conf.get(ConfigKeys.EXCHANGE, domain=self.domain_key, default='node_exchange')
        queue_db = conf.get(ConfigKeys.DB, domain=self.domain_key, default=0)
        queue_name = conf.get(ConfigKeys.QUEUE, domain=self.domain_key, default=None)

        if queue_name is None or len(queue_name.strip()) == 0:
            queue_name = 'node_queue_%s_%s_%s' % (
                conf.get(ConfigKeys.ENVIRONMENT),
                self.get_host(),
                bind_port
            )

        if self.is_external_queue:
            self.exchange = Exchange(exchange, type='direct')
        else:
            self.exchange = Exchange(exchange, type='fanout')

        self.queue_connection = Connection(queue_host, transport_options={'db': queue_db})
        logger.info('queue connection: {}'.format(str(self.queue_connection)))
        self.queue_name = queue_name
        self.queue = Queue(self.queue_name, self.exchange)
