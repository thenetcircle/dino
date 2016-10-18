import yaml
import json
import os
import pkg_resources
import logging

from logging import RootLogger
from redis import Redis
from typing import Union

from kombu import Exchange
from kombu import Queue
from kombu import Connection
from kombu.pools import producers

from flask_socketio import emit as _flask_emit
from flask_socketio import send as _flask_send
from flask_socketio import join_room as _flask_join_room
from flask_socketio import leave_room as _flask_leave_room

from flask_wtf import Form as _flask_Form
from wtforms.fields import StringField as _wtf_StringField
from wtforms.fields import SubmitField as _wtf_SubmitField
from wtforms.fields import SelectField as _wtf_SelectField
from wtforms.validators import DataRequired as _wtf_DataRequired

from flask import redirect as _flask_redirect
from flask import url_for as _flask_url_for
from flask import request as _flask_request
from flask import send_from_directory as _flask_send_from_directory
from flask import render_template as _flask_render_template
from flask import session as _flask_session

from dino.config import ConfigKeys

ENV_KEY_ENVIRONMENT = 'ENVIRONMENT'


class ConfigDict:
    class DefaultValue:
        def __init__(self):
            pass

        def lower(self):
            raise NotImplementedError()

        def format(self):
            raise NotImplementedError()

    def __init__(self, params=None, override=None):
        self.params = params or dict()
        self.override = override

    def subp(self, parent):
        p = dict(parent.params)
        p.update(self.params)
        p.update(self.override)
        return ConfigDict(p, self.override)

    def sub(self, **params):
        p = dict(self.params)
        p.update(params)
        p.update(self.override)
        return ConfigDict(p, self.override)

    def set(self, key, val, domain: str=None):
        if domain is None:
            self.params[key] = val
        else:
            if domain not in self.params:
                self.params[domain] = dict()
            self.params[domain][key] = val

    def keys(self):
        return self.params.keys()

    def get(self, key, default: Union[None, object]=DefaultValue, params=None, domain=None):
        def config_format(s, _params):
            if s is None:
                return s

            if isinstance(s, list):
                return [config_format(r, _params) for r in s]

            if isinstance(s, dict):
                kw = dict()
                for k, v in s.items():
                    kw[k] = config_format(v, _params)
                return kw

            if not isinstance(s, str):
                return s

            if s.lower() == 'null' or s.lower() == 'none':
                return ''

            try:
                import re
                keydb = set('{' + key + '}')

                while True:
                    sres = re.search("{.*?}", s)
                    if sres is None:
                        break

                    # avoid using the same reference twice
                    if sres.group() in keydb:
                        raise RuntimeError(
                                "found circular dependency in config value '{0}' using reference '{1}'".format(
                                        s, sres.group()))
                    keydb.add(sres.group())
                    s = s.format(**_params)

                return s
            except KeyError as e:
                raise RuntimeError("missing configuration key: " + str(e))

        if params is None:
            params = self.params

        if domain is not None:
            if domain in self.params:
                # domain keys are allowed to be empty, e.g. for default amqp exchange etc.
                value = self.params.get(domain).get(key)
                if value is None:
                    if default is None:
                        return ''
                    return default

                return config_format(value, params)

        if key in self.params:
            return config_format(self.params.get(key), params)

        if default == ConfigDict.DefaultValue:
            raise KeyError(key)

        return config_format(default, params)

    def __contains__(self, key):
        if key in self.params:
            return True
        return False

    def __iter__(self):
        for k in sorted(self.params.keys()):
            yield k

    def __len__(self, *args, **kwargs):
        return len(self.params)


class GNEnvironment(object):
    def __init__(self, root_path: Union[str, None], config: ConfigDict):
        """
        Initialize the environment
        """
        self.root_path = root_path
        self.config = config
        self.storage = None

        self.out_of_scope_emit = None  # needs to be set later after socketio object has been created
        self.emit = _flask_emit
        self.send = _flask_send
        self.join_room = _flask_join_room
        self.leave_room = _flask_leave_room
        self.render_template = _flask_render_template
        self.Form = _flask_Form
        self.SubmitField = _wtf_SubmitField
        self.DataRequired = _wtf_DataRequired
        self.StringField = _wtf_StringField
        self.SelectField = _wtf_SelectField

        self.redirect = _flask_redirect
        self.url_for = _flask_url_for
        self.request = _flask_request
        self.send_from_directory = _flask_send_from_directory

        self.logger = config.get(ConfigKeys.LOGGER, None)
        self.session = config.get(ConfigKeys.SESSION, None)
        self.auth = config.get(ConfigKeys.AUTH_SERVICE, None)
        self.db = None
        self.publish = None
        self.queue_connection = None
        self.queue = None
        self.exchange = None
        self.consume_worker = None
        self.start_consumer = None

        # TODO: remove this, go through storage interface
        self.redis = config.get(ConfigKeys.REDIS, None)

    def __setattr__(self, attr, value):
        if attr == 'config' and hasattr(self, attr):
            raise Exception("Attempting to alter read-only value")

        self.__dict__[attr] = value


def create_logger(_config_dict: dict) -> RootLogger:
    logging.basicConfig(
            level=getattr(logging, _config_dict.get(ConfigKeys.LOG_LEVEL, 'INFO')),
            format=_config_dict.get(ConfigKeys.LOG_FORMAT, ConfigKeys.DEFAULT_LOG_FORMAT))
    logging.getLogger('engineio').setLevel(logging.WARNING)
    logging.getLogger('cassandra').setLevel(logging.WARNING)
    return logging.getLogger(__name__)


def find_config(config_paths: list) -> str:
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
                config_dict = yaml.load(open(path))
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


def choose_queue_instance(config_dict: dict) -> object:
    # TODO: should choose between RabbitMQ and Redis
    queue_type = config_dict.get(ConfigKeys.QUEUE).get(ConfigKeys.TYPE, 'mock')

    if queue_type == 'mock':
        from fakeredis import FakeStrictRedis
        return FakeStrictRedis()
    elif queue_type == 'redis':
        redis_host = config_dict.get(ConfigKeys.QUEUE).get(ConfigKeys.HOST, 'localhost')
        redis_port = 6379

        if redis_host.startswith('redis://'):
            redis_host = redis_host.replace('redis://', '')

        if ':' in redis_host:
            redis_host, redis_port = redis_host.split(':', 1)

        return Redis(redis_host, port=redis_port)

    raise RuntimeError('unknown queue type "%s"' % queue_type)


def create_env(config_paths: list = None) -> GNEnvironment:
    gn_environment = os.getenv(ENV_KEY_ENVIRONMENT)

    # assuming tests are running
    if gn_environment is None:
        return GNEnvironment(None, ConfigDict(dict()))

    config_dict, config_path = find_config(config_paths)

    if gn_environment not in config_dict:
        raise RuntimeError('no configuration found for environment "%s"' % gn_environment)

    config_dict = config_dict[gn_environment]

    if ConfigKeys.STORAGE not in config_dict:
        raise RuntimeError('no storage configured for environment %s' % gn_environment)

    # TODO: rename to ConfigKeys.QUEUE, could be either redis or rabbitmq
    config_dict[ConfigKeys.REDIS] = choose_queue_instance(config_dict)

    config_dict[ConfigKeys.ENVIRONMENT] = gn_environment
    config_dict[ConfigKeys.VERSION] = pkg_resources.require('dino')[0].version
    config_dict[ConfigKeys.LOGGER] = create_logger(config_dict)
    config_dict[ConfigKeys.SESSION] = _flask_session

    if ConfigKeys.LOG_FORMAT not in config_dict:
        log_format = ConfigKeys.DEFAULT_LOG_FORMAT
        config_dict[ConfigKeys.LOG_FORMAT] = log_format

    if ConfigKeys.LOG_LEVEL not in config_dict:
        config_dict[ConfigKeys.LOG_LEVEL] = ConfigKeys.DEFAULT_LOG_LEVEL

    root_path = os.path.dirname(config_path)

    gn_env = GNEnvironment(root_path, ConfigDict(config_dict))

    gn_env.config.get(ConfigKeys.LOGGER).info('read config and created environment')
    gn_env.config.get(ConfigKeys.LOGGER).debug(str(config_dict))
    return gn_env


def init_storage_engine(gn_env: GNEnvironment) -> None:
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    storage_engine = gn_env.config.get(ConfigKeys.STORAGE, None)

    if storage_engine is None:
        raise RuntimeError('no storage engine specified')

    storage_type = storage_engine.get(ConfigKeys.TYPE)
    if storage_type is None:
        raise RuntimeError('no storage type specified, use redis, cassandra, mysql etc.')

    if storage_type == 'redis':
        from dino.storage.redis import StorageRedis

        storage_host, storage_port = storage_engine.get(ConfigKeys.HOST), None
        if ':' in storage_host:
            storage_host, storage_port = storage_host.split(':', 1)

        storage_db = storage_engine.get(ConfigKeys.DB, 0)
        gn_env.storage = StorageRedis(host=storage_host, port=storage_port, db=storage_db)
    elif storage_type == 'cassandra':
        from dino.storage.cassandra import CassandraStorage

        storage_hosts = storage_engine.get(ConfigKeys.HOST)
        strategy = storage_engine.get(ConfigKeys.STRATEGY, None)
        replication = storage_engine.get(ConfigKeys.REPLICATION, None)
        gn_env.storage = CassandraStorage(storage_hosts, replications=replication, strategy=strategy)
        gn_env.storage.init()
    else:
        raise RuntimeError('unknown storage engine type "%s"' % storage_type)


def init_database(gn_env: GNEnvironment):
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    db_engine = gn_env.config.get(ConfigKeys.DATABASE, None)
    if db_engine is None:
        raise RuntimeError('no db service specified')

    db_type = db_engine.get(ConfigKeys.TYPE, None)
    if db_type is None:
        db_type = 'redis'

    if db_type == 'redis':
        from dino.db.redis import DatabaseRedis

        db_host, db_port = db_engine.get(ConfigKeys.HOST), None
        if ':' in db_host:
            db_host, db_port = db_host.split(':', 1)

        db_number = db_engine.get(ConfigKeys.DB, 0)
        gn_env.db = DatabaseRedis(host=db_host, port=db_port, db=db_number)
    elif db_type == 'postgres':
        from dino.db.postgres.postgres import DatabasePostgres
        gn_env.db = DatabasePostgres()
    else:
        raise RuntimeError('unknown db type "%s", use one of [mock, redis, postgres, mysql]' % db_type)


def init_auth_service(gn_env: GNEnvironment):
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    auth_engine = gn_env.config.get(ConfigKeys.AUTH_SERVICE, None)

    if auth_engine is None:
        raise RuntimeError('no auth service specified')

    auth_type = auth_engine.get(ConfigKeys.TYPE, None)
    if auth_type is None:
        raise RuntimeError('no auth type specified, use one of [redis, allowall, denyall]')

    if auth_type == 'redis':
        from dino.auth.redis import AuthRedis

        auth_host, auth_port = auth_engine.get(ConfigKeys.HOST), None
        if ':' in auth_host:
            auth_host, auth_port = auth_host.split(':', 1)

        auth_db = auth_engine.get(ConfigKeys.DB, 0)
        gn_env.auth = AuthRedis(host=auth_host, port=auth_port, db=auth_db)
    elif auth_type == 'allowall':
        from dino.auth.simple import AllowAllAuth
        gn_env.auth = AllowAllAuth()
    elif auth_type == 'denyall':
        from dino.auth.simple import DenyAllAuth
        gn_env.auth = DenyAllAuth()
    else:
        raise RuntimeError('unknown auth type, use one of [redis, allowall, denyall]')


def init_cache_service(gn_env: GNEnvironment):
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    cache_engine = gn_env.config.get(ConfigKeys.CACHE_SERVICE, None)

    if cache_engine is None:
        raise RuntimeError('no cache service specified')

    cache_type = cache_engine.get(ConfigKeys.TYPE, None)
    if cache_type is None:
        raise RuntimeError('no cache type specified, use one of [redis, mock, missall]')

    if cache_type == 'redis':
        from dino.cache.redis import CacheRedis

        cache_host, cache_port = cache_engine.get(ConfigKeys.HOST), None
        if ':' in cache_host:
            cache_host, cache_port = cache_host.split(':', 1)

        cache_db = cache_engine.get(ConfigKeys.DB, 0)
        gn_env.cache = CacheRedis(host=cache_host, port=cache_port, db=cache_db)
    elif cache_type == 'memory':
        from dino.cache.redis import CacheRedis
        gn_env.cache = CacheRedis(host='mock')
    elif cache_type == 'missall':
        from dino.cache.miss import CacheAllMiss
        gn_env.cache = CacheAllMiss()
    else:
        raise RuntimeError('unknown cache type %s, use one of [redis, mock, missall]' % cache_type)


def init_pub_sub(gn_env: GNEnvironment):
    def publish(message):
        with producers[gn_env.queue_connection].acquire(block=True) as producer:
            producer.publish(message, exchange=gn_env.exchange, declare=[gn_env.exchange, gn_env.queue])

    def mock_publish(message):
        pass

    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        gn_env.publish = mock_publish
        return

    gn_env.queue_connection = Connection('redis://localhost:6379/')
    gn_env.exchange = Exchange('node_exchange', type='direct')
    gn_env.queue = Queue('node_queue', gn_env.exchange)
    gn_env.publish = publish


def initialize_env(dino_env):
    init_storage_engine(dino_env)
    init_database(dino_env)
    init_auth_service(dino_env)
    init_cache_service(dino_env)
    init_pub_sub(dino_env)


_config_paths = None
if 'CONFIG' in os.environ:
    _config_paths = [os.environ['CONFIG']]
    print(_config_paths)
env = create_env(_config_paths)
initialize_env(env)
