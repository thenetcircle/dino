import yaml
import json
import os
import pkg_resources
import logging
from enum import Enum
from logging import RootLogger
from redis import Redis
from typing import Union

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

ENV_KEY_ENVIRONMENT = 'ENVIRONMENT'


class SessionKeys(Enum):
    user_id = 'user_id'
    user_name = 'user_name'
    age = 'age'
    gender = 'gender'
    membership = 'membership'
    country = 'country'
    city = 'city'
    image = 'image'
    has_webcam = 'has_webcam'
    fake_checked = 'fake_checked'
    token = 'token'


class ConfigKeys(object):
    LOG_LEVEL = 'log_level'
    LOG_FORMAT = 'log_format'
    DEBUG = 'debug'
    QUEUE = 'queue'
    TESTING = 'testing'
    STORAGE = 'storage'
    HOST = 'host'
    TYPE = 'type'
    MAX_HISTORY = 'max_history'

    # will be overwritten even if specified in config file
    ENVIRONMENT = '_environment'
    VERSION = '_version'
    LOGGER = '_logger'
    REDIS = '_redis'
    SESSION = '_session'

    DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)-18s - %(levelname)-7s - %(message)s"
    DEFAULT_LOG_LEVEL = 'INFO'
    DEFAULT_REDIS_HOST = 'localhost'


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

    def set(self, key, val):
        self.params[key] = val

    def keys(self):
        return self.params.keys()

    def get(self, key, default: Union[DefaultValue, object]=DefaultValue, params=None, domain=None):
        def config_format(s, params):
            if s is None:
                return s

            if isinstance(s, list):
                return [config_format(r, params) for r in s]

            if isinstance(s, dict):
                kw = dict()
                for k, v in s.items():
                    kw[k] = config_format(v, params)
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
                    s = s.format(**params)

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
    redis_host = config_dict.get(ConfigKeys.QUEUE).get(ConfigKeys.HOST, 'localhost')
    redis_port = 6379

    if ':' in redis_host:
        redis_host, redis_port = redis_host.split(':', 1)

    if redis_host == 'mock':
        from fakeredis import FakeStrictRedis
        return FakeStrictRedis()

    return Redis(redis_host, port=redis_port)


def create_env(config_paths: list=None) -> GNEnvironment:
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
        from dino.storage.redis import RedisStorage

        storage_host, storage_port = storage_engine.get(ConfigKeys.HOST), None
        if ':' in storage_host:
            storage_host, storage_port = storage_host.split(':', 1)

        gn_env.storage = RedisStorage(host=storage_host, port=storage_port)
    else:
        raise RuntimeError('unknown storage engine type "%s"' % storage_type)


env = create_env()
init_storage_engine(env)
