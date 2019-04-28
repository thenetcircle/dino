from dino.config import ConfigKeys
from dino import environ

import eventlet
import traceback
import logging
import sys
import os

from dino.endpoint.base import PublishException

logger = logging.getLogger(__name__)
DINO_DEBUG = os.environ.get('DINO_DEBUG')
if DINO_DEBUG is not None and DINO_DEBUG.lower() in {'1', 'true', 'yes'}:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


class PubSub(object):
    def __init__(self, env):
        self.env = env

        if len(self.env.config) == 0 or self.env.config.get(ConfigKeys.TESTING, False):
            self.env.publish = PubSub.mock_publish
            return

        conf = self.env.config
        self.env.publish = self.do_publish

        self._setup_internal_queue(conf, env)
        self._setup_external_queue(conf, env)

    def _setup_internal_queue(self, conf, env):
        queue_type = conf.get(ConfigKeys.TYPE, domain=ConfigKeys.QUEUE, default=None)
        if queue_type is None:
            raise RuntimeError('no message queue specified')

        if queue_type == 'redis':
            from dino.endpoint.redis import RedisPublisher
            self.env.internal_publisher = RedisPublisher(env, is_external_queue=False)

        elif queue_type == 'amqp':
            from dino.endpoint.amqp import AmqpPublisher
            self.env.internal_publisher = AmqpPublisher(env, is_external_queue=False)

        elif queue_type == 'mock':
            from dino.endpoint.mock import MockPublisher
            self.env.internal_publisher = MockPublisher(env, is_external_queue=False)

        else:
            raise RuntimeError('unknown message queue type "{}"'.format(queue_type))

    def _setup_external_queue(self, conf, env):
        ext_queue_type = conf.get(ConfigKeys.TYPE, domain=ConfigKeys.EXTERNAL_QUEUE)
        if ext_queue_type is None:
            # external queue not required
            self.env.external_publisher = PubSub.mock_publish
            return

        if ext_queue_type in {'rabbitmq', 'amqp'}:
            from dino.endpoint.amqp import AmqpPublisher
            self.env.external_publisher = AmqpPublisher(env, is_external_queue=True)

        elif ext_queue_type == 'redis':
            from dino.endpoint.redis import RedisPublisher
            self.env.external_publisher = RedisPublisher(env, is_external_queue=True)

        elif ext_queue_type == 'kafka':
            from dino.endpoint.kafka import KafkaPublisher
            self.env.external_publisher = KafkaPublisher(env, is_external_queue=True)

        elif ext_queue_type == 'mock':
            from dino.endpoint.mock import MockPublisher
            self.env.external_publisher = MockPublisher(env, is_external_queue=True)

        else:
            raise RuntimeError(
                'unknown external queue type "{}"; available types are [mock,redis,amqp,rabbitmq,kafka]'.format(
                    ext_queue_type)
            )

    def do_publish(self, message: dict, external: bool=None):
        logger.debug('publish: verb %s id %s external? %s' % (message['verb'], message['id'], str(external or False)))
        if external is None or not external:
            external = False

        # avoid hanging clients
        eventlet.spawn(self._do_publish_async, message, external)

    def _do_publish_async(self, message: dict, external: bool):
        if external:
            return self._do_publish_external(message)
        else:
            return self._do_publish_internal(message)

    def _do_publish_external(self, message: dict):
        try:
            return self.env.external_publisher.publish(message)
        except PublishException:
            logger.error('failed to publish external event multiple times! Republishing to internal queue')
            return self.env.internal_publisher.publish(message)
        except Exception as e:
            logger.error('could not publish message "%s", because: %s' % (str(message), str(e)))
            logger.exception(traceback.format_exc())
            self.env.stats.incr('publish.error')
            environ.env.capture_exception(sys.exc_info())
        return None

    def _do_publish_internal(self, message: dict):
        try:
            return self.env.internal_publisher.publish(message)
        except Exception as e:
            logger.error('could not publish message "%s", because: %s' % (str(message), str(e)))
            logger.exception(traceback.format_exc())
            self.env.stats.incr('publish.error')
            environ.env.capture_exception(sys.exc_info())
        return None

    @staticmethod
    def mock_publish(message, external=False):
        pass
