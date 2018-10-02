from kombu import pools
pools.set_limit(200)  # default is 200

from dino.config import ConfigKeys
from dino.endpoint.base import BasePublisher

from kombu import Exchange
from kombu import Queue
from kombu import Connection

import logging

logger = logging.getLogger(__name__)


class AmqpPublisher(BasePublisher):
    def __init__(self, env, is_external_queue: bool):
        super().__init__(env, is_external_queue, queue_type='amqp', logger=logger)
        conf = env.config

        queue_host = conf.get(ConfigKeys.HOST, domain=self.domain_key, default='')
        if queue_host is None or len(queue_host.strip()) == 0:
            return

        queue_port = conf.get(ConfigKeys.PORT, domain=self.domain_key, default=None)
        queue_vhost = conf.get(ConfigKeys.VHOST, domain=self.domain_key, default=None)
        queue_user = conf.get(ConfigKeys.USER, domain=self.domain_key, default=None)
        queue_pass = conf.get(ConfigKeys.PASSWORD, domain=self.domain_key, default=None)

        queue_host = ';'.join(['amqp://%s' % host for host in queue_host.split(';')])
        queue_exchange = '%s_%s' % (
            conf.get(ConfigKeys.EXCHANGE, domain=self.domain_key, default=None),
            conf.get(ConfigKeys.ENVIRONMENT)
        )

        bind_port = self.get_port()
        if bind_port is None:
            logging.info('skipping pubsub setup, no port specified')
            return

        queue_name = conf.get(ConfigKeys.QUEUE, domain=self.domain_key, default=None)
        if queue_name is None or len(queue_name.strip()) == 0:
            queue_name = 'node_queue_%s_%s_%s' % (
                conf.get(ConfigKeys.ENVIRONMENT),
                self.get_host(),
                bind_port
            )

        if self.is_external_queue:
            self.exchange = Exchange(queue_exchange, type='direct')
        else:
            self.exchange = Exchange(queue_exchange, type='fanout')

        self.queue_connection = Connection(
            hostname=queue_host,
            port=queue_port,
            virtual_host=queue_vhost,
            userid=queue_user,
            password=queue_pass
        )
        self.queue = Queue(queue_name, self.exchange)
        self.logger.info('setting up pubsub for type "{}: and host(s) "{}"'.format(self.queue_type, queue_host))
