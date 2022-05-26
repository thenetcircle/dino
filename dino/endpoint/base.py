import socket
import sys
import time
import traceback
from abc import ABC

from eventlet.semaphore import Semaphore
from kombu.pools import producers

from dino import environ
from dino.config import ConfigKeys
from dino.utils.decorators import locked_method


class PublishException(Exception):
    pass


class BasePublisher(ABC):
    def __init__(self, env, is_external_queue: bool, queue_type: str, logger):
        self._lock = Semaphore(value=1)
        self.env = env
        self.logger = logger
        self.queue_type = queue_type
        self.recently_sent_external_hash = set()
        self.recently_sent_external_list = list()

        self.is_external_queue = is_external_queue
        if is_external_queue:
            self.domain_key = ConfigKeys.EXTERNAL_QUEUE
        else:
            self.domain_key = ConfigKeys.QUEUE

        self.queue_connection = None
        self.queue = None
        self.exchange = None
        self.message_type = 'external' if self.is_external_queue else 'internal'

    def error_callback(self, exc, interval) -> None:
        self.logger.warning('could not connect to MQ (interval: %s): %s' % (str(interval), str(exc)))

    def try_publish(self, message, topic: str = None):
        self.logger.info('sending "{}" with "{}"'.format(self.message_type, str(self.queue_connection)))

        with producers[self.queue_connection].acquire(block=False) as producer:
            amqp_publish = self.queue_connection.ensure(
                producer,
                producer.publish,
                errback=self.error_callback,
                max_retries=3
            )

            amqp_publish(
                message,
                exchange=self.exchange,
                declare=[self.exchange, self.queue]
            )

    def publish(self, message: dict) -> None:
        if self.recently_sent_has(message['id']):
            self.logger.debug('ignoring external event with verb %s and id %s, already sent' %
                         (message['verb'], message['id']))
            return

        n_tries = 3
        current_try = 0
        failed = False

        for current_try in range(n_tries):
            try:
                self.try_publish(message)
                failed = False
                self.update_recently_sent(message['id'])
                break

            except Exception as pe:
                failed = True
                self.logger.error('[%s/%s tries] failed to publish external: %s' % (
                    str(current_try+1), str(n_tries), str(pe)))
                self.logger.exception(traceback.format_exc())
                self.env.stats.incr('publish.error')
                environ.env.capture_exception(pe)
                time.sleep(0.1)

        if failed:
            raise PublishException()
        elif current_try > 0:
            self.logger.info('published {} event on attempt {}/{}'.format(
                self.message_type, str(current_try+1), str(n_tries))
            )
        else:
            self.logger.debug('published {} event with verb {} id {}'.format(
                self.message_type, message['verb'], message['id'])
            )

    def get_port(self):
        args = sys.argv
        for a in ['--bind', '-b']:
            bind_arg_pos = [i for i, x in enumerate(args) if x == a]
            if len(bind_arg_pos) > 0:
                bind_arg_pos = bind_arg_pos[0]
                break

        try:
            return args[bind_arg_pos + 1].split(':')[1]
        except TypeError:
            self.logger.info('skipping pubsub setup, no port specified')
            return None

    def get_host(self):
        return socket.gethostname()

    @locked_method
    def recently_sent_has(self, msg_id: str) -> bool:
        return msg_id in self.recently_sent_external_hash

    @locked_method
    def update_recently_sent(self, msg_id: str) -> None:
        self.recently_sent_external_hash.add(msg_id)
        self.recently_sent_external_list.append(msg_id)
        if len(self.recently_sent_external_list) > 100:
            old_id = self.recently_sent_external_list.pop(0)
            self.recently_sent_external_hash.remove(old_id)
