# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from concurrent.futures import ThreadPoolExecutor

from dino.environ import GNEnvironment
from dino.config import ConfigKeys

from kombu import Exchange
from kombu import Queue
from kombu import Connection
from kombu.pools import producers

import traceback
import logging
import time

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


def locked_method(method):
    """Method decorator. Requires a lock object at self._lock"""
    def newmethod(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return newmethod


class PubSub(object):
    def __init__(self, env: GNEnvironment):
        self.env = env
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.recently_sent_external_hash = set()
        self.recently_sent_external_list = list()

        if len(self.env.config) == 0 or self.env.config.get(ConfigKeys.TESTING, False):
            self.env.publish = PubSub.mock_publish
            return

        conf = self.env.config
        self.env.publish = self.do_publish

        queue_host = conf.get(ConfigKeys.HOST, domain=ConfigKeys.QUEUE, default=None)
        queue_type = conf.get(ConfigKeys.TYPE, domain=ConfigKeys.QUEUE, default=None)
        self.env.queue_connection = None

        import sys
        import socket

        args = sys.argv
        bind_arg_pos = None
        for a in ['--bind', '-b']:
            bind_arg_pos = [i for i, x in enumerate(args) if x == a]
            if len(bind_arg_pos) > 0:
                bind_arg_pos = bind_arg_pos[0]
                break

        port = args[bind_arg_pos + 1].split(':')[1]
        hostname = socket.gethostname()

        if queue_host is not None:
            if queue_type == 'redis':
                self.env.queue_connection = Connection(queue_host)
                exchange = conf.get(ConfigKeys.EXCHANGE, domain=ConfigKeys.QUEUE, default='node_exchange')
                queue_name = conf.get(ConfigKeys.QUEUE, domain=ConfigKeys.QUEUE, default=None)
                if queue_name is None or len(queue_name.strip()) == 0:
                    queue_name = 'node_queue_%s_%s_%s' % (
                        conf.get(ConfigKeys.ENVIRONMENT),
                        hostname,
                        port
                    )

                self.env.queue_name = queue_name
                self.env.exchange = Exchange(exchange, type='fanout')
                self.env.queue = Queue(self.env.queue_name, self.env.exchange)

            elif queue_type == 'amqp':
                queue_port = conf.get(ConfigKeys.PORT, domain=ConfigKeys.QUEUE, default=None)
                queue_vhost = conf.get(ConfigKeys.VHOST, domain=ConfigKeys.QUEUE, default=None)
                queue_user = conf.get(ConfigKeys.USER, domain=ConfigKeys.QUEUE, default=None)
                queue_pass = conf.get(ConfigKeys.PASSWORD, domain=ConfigKeys.QUEUE, default=None)
                queue_host = ';'.join(['amqp://%s' % host for host in queue_host.split(';')])
                queue_exchange = '%s_%s' % (
                    conf.get(ConfigKeys.EXCHANGE, domain=ConfigKeys.QUEUE, default=None),
                    conf.get(ConfigKeys.ENVIRONMENT)
                )

                queue_name = conf.get(ConfigKeys.QUEUE, domain=ConfigKeys.QUEUE, default=None)
                if queue_name is None or len(queue_name.strip()) == 0:
                    queue_name = 'node_queue_%s_%s_%s' % (
                        conf.get(ConfigKeys.ENVIRONMENT),
                        hostname,
                        port
                    )

                self.env.queue_name = queue_name
                self.env.queue_connection = Connection(
                    hostname=queue_host, port=queue_port, virtual_host=queue_vhost, userid=queue_user,
                    password=queue_pass)
                self.env.exchange = Exchange(queue_exchange, type='fanout')
                self.env.queue = Queue(self.env.queue_name, self.env.exchange)

        if self.env.queue_connection is None:
            raise RuntimeError('no message queue specified, need either redis or amqp')

        ext_queue_host = conf.get(ConfigKeys.HOST, domain=ConfigKeys.EXTERNAL_QUEUE, default='')
        self.env.external_queue_connection = None
        if ext_queue_host is not None and len(ext_queue_host.strip()) > 0:
            ext_port = conf.get(ConfigKeys.PORT, domain=ConfigKeys.EXTERNAL_QUEUE, default=None)
            ext_vhost = conf.get(ConfigKeys.VHOST, domain=ConfigKeys.EXTERNAL_QUEUE, default=None)
            ext_user = conf.get(ConfigKeys.USER, domain=ConfigKeys.EXTERNAL_QUEUE, default=None)
            ext_pass = conf.get(ConfigKeys.PASSWORD, domain=ConfigKeys.EXTERNAL_QUEUE, default=None)
            ext_exchange = conf.get(ConfigKeys.EXCHANGE, domain=ConfigKeys.EXTERNAL_QUEUE, default=None)
            ext_queue = conf.get(ConfigKeys.QUEUE, domain=ConfigKeys.EXTERNAL_QUEUE, default=None)

            self.env.external_queue_connection = Connection(
                hostname=ext_queue_host, port=ext_port, virtual_host=ext_vhost, userid=ext_user, password=ext_pass)
            self.env.external_exchange = Exchange(ext_exchange, type='direct')
            self.env.external_queue = Queue(ext_queue, self.env.external_exchange)

    def do_publish(self, message: dict, external: bool=None):
        logger.debug('publish: verb %s id %s external? %s' % (message['verb'], message['id'], str(external or False)))
        if external is None or not external:
            external = False

        # avoid hanging clients
        self.executor.submit(self._do_publish_async, message, external)

    @locked_method
    def _recently_sent_has(self, msg_id: str) -> bool:
        return msg_id in self.recently_sent_external_hash

    def _do_publish_async(self, message: dict, external: bool):
        if external:
            # avoid publishing duplicate events by only letting the rest node publish external events
            if self.env.node != 'rest':
                return

            if self._recently_sent_has(message['id']):
                logger.debug('ignoring external event with verb %s and id %s, already sent' %
                             (message['verb'], message['id']))
                return

            return self.do_publish_external(message)
        return self.do_publish_internal(message)

    def do_publish_external(self, message: dict):
        def try_publish_external() -> None:
            return self.try_publish(message, message_type, queue_connection, exchange, queue)

        message_type = 'external'
        queue_connection = self.env.external_queue_connection
        if queue_connection is None:
            return None
        exchange = self.env.external_exchange
        queue = self.env.external_queue

        try:
            return try_publish_external()
        except Exception as e:
            logger.error('could not publish message "%s", because: %s' % (str(message), str(e)))
            logger.exception(traceback.format_exc())
            self.env.stats.incr('publish.error')
        return None

    def do_publish_internal(self, message: dict):
        def try_publish_internal() -> None:
            return self.try_publish(message, message_type, queue_connection, exchange, queue)

        message_type = 'internal'
        queue_connection = self.env.queue_connection
        if queue_connection is None:
            return None
        exchange = self.env.exchange
        queue = self.env.queue

        try:
            return try_publish_internal()
        except Exception as e:
            logger.error('could not publish message "%s", because: %s' % (str(message), str(e)))
            logger.exception(traceback.format_exc())
            self.env.stats.incr('publish.error')
        return None

    def try_publish(self, message: dict, message_type: str, queue_connection, exchange, queue) -> None:
        start = time.time()
        n_tries = 3
        current_try = 0
        failed = False

        with producers[queue_connection].acquire(block=True) as producer:
            amqp_publish = queue_connection.ensure(
                producer, producer.publish, errback=PubSub.error_callback, max_retries=3)

            for current_try in range(n_tries):
                try:
                    amqp_publish(message, exchange=exchange, declare=[exchange, queue])
                    self.env.stats.incr('publish.%s.count' % message_type)
                    self.env.stats.timing('publish.%s.time' % message_type, (time.time()-start)*1000)
                    failed = False
                    if message_type == 'external':
                        self.update_recently_sent(message['id'])
                    break
                except Exception as pe:
                    failed = True
                    logger.error('[%s/%s tries] failed to publish %s: %s' % (
                        str(current_try+1), str(n_tries), message_type, str(pe)))
                    logger.exception(traceback.format_exc())
                    self.env.stats.incr('publish.error')
                    time.sleep(0.1)

        if failed:
            logger.error(
                    'failed to publish %s event %s times! Republishing to internal queue' %
                    (message_type, str(n_tries)))
            self.do_publish(message)
        elif current_try > 0:
            logger.info('published %s event on attempt %s/%s' % (message_type, str(current_try+1), str(n_tries)))
        else:
            logger.debug('published %s event with verb %s id %s' % (message_type, message['verb'], message['id']))

    @locked_method
    def update_recently_sent(self, msg_id: str) -> None:
        self.recently_sent_external_hash.add(msg_id)
        self.recently_sent_external_list.append(msg_id)
        if len(self.recently_sent_external_list) > 100:
            old_id = self.recently_sent_external_list.pop(0)
            self.recently_sent_external_hash.remove(old_id)

    @staticmethod
    def mock_publish(message, external=False):
        pass

    @staticmethod
    def error_callback(exc, interval) -> None:
        logger.warning('could not connect to MQ (interval: %s): %s' % (str(interval), str(exc)))
