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
        topic_key = None

        # try to get some consistency
        try:
            target = message.get('target', dict())
            topic_key = target.get('id', None)

            if topic_key is None:
                actor = message.get('actor', dict())
                topic_key = actor.get('id', None)

            # kafka publisher can't handle string keys
            topic_key = bytes(topic_key)

        except Exception as partition_e:
            logger.exception(traceback.format_exc())
            environ.env.capture_exception(partition_e)

        # for kafka, the queue_connection is the KafkaProducer and queue is the topic name
        self.queue_connection.send(
            topic=self.queue, value=message, key=topic_key)
