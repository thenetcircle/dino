import logging
import random
import traceback

from dino import environ
from dino.config import ConfigKeys
from dino.endpoint.base import BasePublisher

logger = logging.getLogger(__name__)


class KafkaPublisher(BasePublisher):
    def __init__(self, env, is_external_queue: bool):
        super().__init__(env, is_external_queue, queue_type='kafka', logger=logger)

        # todo: ask kafka client how many partitions we have available
        self.n_partitions = 3

        eq_host = env.config.get(ConfigKeys.HOST, domain=self.domain_key, default=None)
        eq_queue = env.config.get(ConfigKeys.QUEUE, domain=self.domain_key, default=None)

        if eq_host is None or len(eq_host) == 0 or (type(eq_host) == str and len(eq_host.strip()) == 0):
            logging.warning('blank external host specified, not setting up external publishing')
            return

        if eq_queue is None or len(eq_queue.strip()) == 0:
            logging.warning('blank external queue specified, not setting up external publishing')
            return

        if type(eq_host) == str:
            eq_host = [eq_host]

        from kafka import KafkaProducer
        import json

        self.queue = eq_queue
        self.queue_connection = KafkaProducer(
            bootstrap_servers=eq_host,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'))
        logger.info('setting up pubsub for type "{}: and host(s) "{}"'.format(self.queue_type, ','.join(eq_host)))

    def try_publish(self, message):
        message = self.env.enrichment_manager.handle(message)
        partition = 0

        # try to get some consistency
        try:
            target = message.get('target', dict())
            partition_id = target.get('id', None)

            if partition_id is None:
                actor = message.get('actor', dict())
                partition_id = actor.get('id', None)

            # system/admin events don't have an actor id and not necessarily a target id either
            if partition_id is None:
                partition = random.choice(range(self.n_partitions))
            else:
                partition_id = int(float(partition_id))
                partition = partition_id % self.n_partitions

        except Exception as partition_e:
            logger.exception(traceback.format_exc())
            environ.env.capture_exception(partition_e)

        # for kafka, the queue_connection is the KafkaProducer and queue is the topic name
        self.queue_connection.send(
            topic=self.queue, value=message, partition=partition)
