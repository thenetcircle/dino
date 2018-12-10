import json
import logging
import os
import time
import traceback

import yaml
from kafka import KafkaConsumer
from kombu import Connection
from kombu import Exchange
from kombu import Queue
from kombu.pools import producers

logger = logging.getLogger(__name__)
logging.getLogger('kafka').setLevel(logging.WARNING)
logging.getLogger('kafka.conn').setLevel(logging.WARNING)

ENV_KEY_ENVIRONMENT = 'DINO_ENVIRONMENT'
ENV_KEY_SECRETS = 'DINO_SECRETS'

DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)-18s - %(levelname)-7s - %(message)s"
DEFAULT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

ONE_MINUTE = 60000


class ConfigKeys(object):
    AMQP = 'amqp'
    QUEUE = 'queue'
    EXTERNAL_QUEUE = 'ext_queue'
    EXCHANGE = 'exchange'
    HOST = 'host'
    TYPE = 'type'
    DATABASE = 'database'
    POOL_SIZE = 'pool_size'
    DB = 'db'
    PORT = 'port'
    VHOST = 'vhost'
    USER = 'user'
    PASSWORD = 'password'
    ENVIRONMENT = '_environment'


class PublishException(Exception):
    pass


class AmqpPublisher(object):
    def __init__(self, _conf):
        amqp_conf = conf.get(ConfigKeys.AMQP)
        queue_host = amqp_conf.get(ConfigKeys.HOST)
        if queue_host is None or len(queue_host.strip()) == 0:
            return

        queue_port = amqp_conf.get(ConfigKeys.PORT)
        queue_vhost = amqp_conf.get(ConfigKeys.VHOST)
        queue_user = amqp_conf.get(ConfigKeys.USER)
        queue_pass = amqp_conf.get(ConfigKeys.PASSWORD)

        queue_host = ';'.join(['amqp://%s' % host for host in queue_host.split(';')])
        queue_exchange = '%s_%s' % (
            amqp_conf.get(ConfigKeys.EXCHANGE),
            amqp_conf.get(ConfigKeys.ENVIRONMENT)
        )

        queue_name = amqp_conf.get(ConfigKeys.QUEUE)
        self.exchange = Exchange(queue_exchange, type='direct')

        self.queue_connection = Connection(
            hostname=queue_host,
            port=queue_port,
            virtual_host=queue_vhost,
            userid=queue_user,
            password=queue_pass
        )
        self.queue = Queue(queue_name, self.exchange)
        logger.info('setting up pubsub for host(s) "{}"'.format(queue_host))

    def error_callback(self, exc, interval) -> None:
        logger.warning('could not connect to MQ (interval: %s): %s' % (str(interval), str(exc)))

    def try_publish(self, message):
        logger.info('sending with "{}"'.format(str(self.queue_connection)))

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
        n_tries = 3
        current_try = 0
        failed = False

        for current_try in range(n_tries):
            try:
                self.try_publish(message)
                failed = False
                break

            except Exception as pe:
                failed = True
                logger.error('[%s/%s tries] failed to publish external: %s' % (
                    str(current_try+1), str(n_tries), str(pe)))
                logger.exception(traceback.format_exc())
                time.sleep(0.1)

        if failed:
            raise PublishException()
        elif current_try > 0:
            logger.info('published event on attempt {}/{}'.format(str(current_try+1), str(n_tries)))
        else:
            logger.debug('published event with verb {} id {}'.format(message['verb'], message['id']))


class KafkaReader(object):
    def __init__(self, _conf):
        self.conf = _conf
        self.consumer = None
        self.failed_msg_log = None
        self.dropped_msg_log = None
        self.publisher = AmqpPublisher(_conf)

    def run(self) -> None:
        self.create_loggers()
        logger.info('sleeping for 3 second before consuming')
        time.sleep(3)

        kafka_conf = self.conf.get(ConfigKeys.EXTERNAL_QUEUE)
        bootstrap_servers = kafka_conf.get(ConfigKeys.HOST)
        logger.info('bootstrapping from servers: %s' % (str(bootstrap_servers)))

        topic_name = kafka_conf.get(ConfigKeys.QUEUE)
        logger.info('consuming from topic {}'.format(topic_name))

        group_id = 'dino-kafka-to-rabbitmq'
        logger.info('using Group ID {}'.format(group_id))

        self.consumer = KafkaConsumer(
            topic_name,
            group_id=group_id,
            bootstrap_servers=bootstrap_servers,
            enable_auto_commit=True,
            connections_max_idle_ms=180 * ONE_MINUTE,  # default: 9min
            max_poll_interval_ms=10 * ONE_MINUTE,  # default: 5min
            session_timeout_ms=ONE_MINUTE,  # default: 10s
            max_poll_records=10  # default: 500
        )

        while True:
            try:
                self.try_to_read()
            except InterruptedError:
                logger.info('got interrupted, shutting down...')
                break
            except Exception as e:
                logger.error('could not read from kafka: {}'.format(str(e)))
                logger.exception(e)
                time.sleep(1)

    def create_loggers(self):
        def _create_logger(_path: str, _name: str) -> logging.Logger:
            msg_formatter = logging.Formatter('%(asctime)s: %(message)s')
            msg_handler = logging.FileHandler(_path)
            msg_handler.setFormatter(msg_formatter)
            msg_logger = logging.getLogger(_name)
            msg_logger.setLevel(logging.INFO)
            msg_logger.addHandler(msg_handler)
            return msg_logger

        f_msg_path = '/var/log/dino/dino-kafka-failed-msgs.log'
        d_msg_path = '/var/log/dino/dino-kafka-dropped-msgs.log'

        self.failed_msg_log = _create_logger(f_msg_path, 'FailedMessages')
        self.dropped_msg_log = _create_logger(d_msg_path, 'DroppedMessages')

    def try_to_read(self):
        for message in self.consumer:
            try:
                self.handle_message(message)
            except InterruptedError:
                raise
            except Exception as e:
                logger.error('failed to handle message: {}'.format(str(e)))
                logger.exception(e)
                self.fail_msg(message)
                time.sleep(1)

    def fail_msg(self, message):
        try:
            self.failed_msg_log.info(str(message))
        except Exception as e:
            logger.error('could not log failed message: {}'.format(str(e)))
            logger.exception(e)

    def drop_msg(self, message):
        try:
            self.dropped_msg_log.info(str(message))
        except Exception as e:
            logger.error('could not log dropped message: {}'.format(str(e)))
            logger.exception(e)

    def handle_message(self, message) -> None:
        logger.debug("%s:%d:%d: key=%s" % (
            message.topic, message.partition,
            message.offset, message.key)
        )

        try:
            message_value = json.loads(message.value.decode('ascii'))
        except Exception as e:
            logger.error('could not decode message from kafka, dropping: {}'.format(str(e)))
            logger.exception(e)
            self.dropped_msg_log.info("[{}:{}:{}:key={}] {}".format(
                message.topic, message.partition,
                message.offset, message.key, str(message.value))
            )
            return

        try:
            logger.info(message_value)
        except Exception as e:
            logger.error('could not log event: {}'.format(str(e)))
            logger.exception(traceback.format_exc())

        try:
            self.write_to_rabbitmq(message_value)
        except InterruptedError:
            raise
        except Exception as e:
            logger.error('got uncaught exception: {}'.format(str(e)))
            logger.error('event was: {}'.format(str(message_value)))
            logger.exception(traceback.format_exc())
            self.fail_msg(message_value)

    def write_to_rabbitmq(self, message):
        self.publisher.publish(message)


def load_secrets_file(config_dict: dict) -> dict:
    from string import Template
    import ast

    gn_env = os.getenv(ENV_KEY_ENVIRONMENT)
    secrets_path = os.getenv(ENV_KEY_SECRETS)
    if secrets_path is None:
        secrets_path = 'secrets/%s.yaml' % gn_env

    logger.debug('loading secrets file "%s"' % secrets_path)

    # first substitute environment variables, which holds precedence over the yaml config (if it exists)
    template = Template(str(config_dict))
    template = template.safe_substitute(os.environ)

    if os.path.isfile(secrets_path):
        try:
            secrets = yaml.safe_load(open(secrets_path))
        except Exception as e:
            raise RuntimeError("Failed to open secrets configuration {0}: {1}".format(secrets_path, str(e)))
        template = Template(template)
        template = template.safe_substitute(secrets)

    return ast.literal_eval(template)


def find_config(config_paths: list=None) -> tuple:
    default_paths = ["dino.yaml", "dino.json"]
    config_dict = dict()
    config_path = None

    if config_paths is None:
        config_paths = default_paths

    for conf in config_paths:
        path = os.path.join(os.getcwd(), conf)

        if not os.path.isfile(path):
            continue

        try:
            if conf.endswith(".yaml"):
                config_dict = yaml.safe_load(open(path))
            elif conf.endswith(".json"):
                config_dict = json.load(open(path))
            else:
                raise RuntimeError("Unsupported file extension: {0}".format(conf))

        except Exception as e:
            raise RuntimeError("Failed to open configuration {0}: {1}".format(conf, str(e)))

        config_path = path
        break

    if not config_dict:
        raise RuntimeError('No configuration found: {0}\n'.format(', '.join(config_paths)))

    return config_dict, config_path


def create_env():
    logging.basicConfig(level='DEBUG', format=DEFAULT_LOG_FORMAT)

    gn_environment = os.getenv(ENV_KEY_ENVIRONMENT)
    logger.info('using environment %s' % gn_environment)

    config_dict, config_path = find_config()

    if gn_environment not in config_dict:
        raise RuntimeError('no configuration found for environment "%s"' % gn_environment)

    config_dict = config_dict[gn_environment]
    config_dict[ConfigKeys.ENVIRONMENT] = gn_environment
    config_dict[ConfigKeys.AMQP] = {
        'type': 'rabbitmq',
        'host': '$DINO_AMQP_HOST',
        'port': 5672,
        'user': '$DINO_AMQP_USER',
        'password': '$DINO_AMQP_PASS',
        'queue': 'chat',
        'vhost': '$DINO_AMQP_VHOST',
        'exchange': 'chat_exchange'
    }
    config_dict = load_secrets_file(config_dict)

    return config_dict


if __name__ == '__main__':
    conf = create_env()
    reader = KafkaReader(conf)
    reader.run()
