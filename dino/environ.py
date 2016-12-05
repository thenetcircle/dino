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

import yaml
import json
import os
import pkg_resources
import logging
import traceback

from logging import RootLogger
from redis import Redis
from typing import Union
from types import MappingProxyType

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
from wtforms.fields import HiddenField as _wtf_HiddenField
from wtforms.validators import DataRequired as _wtf_DataRequired

from flask import redirect as _flask_redirect
from flask import url_for as _flask_url_for
from flask import request as _flask_request
from flask import send_from_directory as _flask_send_from_directory
from flask import render_template as _flask_render_template
from flask import session as _flask_session
from flask_socketio import disconnect as _flask_disconnect

from dino.config import ConfigKeys
from dino.exceptions import AclValueNotFoundException

from dino.validation.acl import AclConfigValidator
from dino.validation.acl import AclRangeValidator
from dino.validation.acl import AclStrInCsvValidator
from dino.validation.acl import AclSameChannelValidator
from dino.validation.acl import AclSameRoomValidator
from dino.validation.acl import AclDisallowValidator
from dino.validation.acl import AclIsAdminValidator
from dino.validation.acl import AclIsSuperUserValidator

ENV_KEY_ENVIRONMENT = 'ENVIRONMENT'

logger = logging.getLogger(__name__)


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
        if self.override is not None:
            p.update(self.override)
        return ConfigDict(p, self.override)

    def sub(self, **params):
        p = dict(self.params)
        p.update(params)
        if self.override is not None:
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
    def __init__(self, root_path: Union[str, None], config: ConfigDict, skip_init=False):
        """
        Initialize the environment
        """
        # can skip when testing
        if skip_init:
            return

        self.root_path = root_path
        self.config = config
        self.storage = None
        self.cache = None
        self.stats = None

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
        self.HiddenField = _wtf_HiddenField

        self.redirect = _flask_redirect
        self.url_for = _flask_url_for
        self.request = _flask_request
        self.send_from_directory = _flask_send_from_directory
        self.disconnect = _flask_disconnect

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


def find_config_acl(acl_paths: list) -> str:
    default_paths = ["acl.yaml", "acl.json"]
    acl_dict = dict()
    acl_path = None

    if acl_paths is None:
        acl_paths = default_paths

    for conf in acl_paths:
        path = os.path.join(os.getcwd(), conf)

        if not os.path.isfile(path):
            continue

        try:
            if conf.endswith(".yaml"):
                acl_dict = yaml.load(open(path))
            elif conf.endswith(".json"):
                acl_dict = json.load(open(path))
            else:
                raise RuntimeError("Unsupported file extension: {0}".format(conf))
        except Exception as e:
            raise RuntimeError("Failed to open acl configuration {0}: {1}".format(conf, str(e)))

        acl_path = path
        break

    if not acl_dict:
        raise RuntimeError('No acl configuration found: {0}\n'.format(', '.join(acl_paths)))

    return acl_dict, acl_path


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
    logger.info('using environment %s' % gn_environment)

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

    try:
        config_dict[ConfigKeys.VERSION] = pkg_resources.require('dino')[0].version
    except Exception:
        # ignore, it will fail when running tests on CI because we don't include all requirements for dino; no need
        pass

    config_dict[ConfigKeys.ENVIRONMENT] = gn_environment
    config_dict[ConfigKeys.LOGGER] = create_logger(config_dict)
    config_dict[ConfigKeys.SESSION] = _flask_session

    if ConfigKeys.HISTORY not in config_dict:
        config_dict[ConfigKeys.HISTORY] = {
            ConfigKeys.TYPE: 'unread',
            ConfigKeys.LIMIT: 100
        }
        logger.info('setting default history strategy: %s' % str(config_dict[ConfigKeys.HISTORY]))
    else:
        if ConfigKeys.TYPE not in config_dict[ConfigKeys.HISTORY]:
            config_dict[ConfigKeys.HISTORY][ConfigKeys.TYPE] = ConfigKeys.HISTORY_TYPE_UNREAD
            logger.info('setting default history type: %s' % ConfigKeys.HISTORY_TYPE_UNREAD)

        if ConfigKeys.LIMIT not in config_dict[ConfigKeys.HISTORY]:
            config_dict[ConfigKeys.HISTORY][ConfigKeys.LIMIT] = ConfigKeys.DEFAULT_HISTORY_LIMIT
            logger.info('setting default history limit: %s' % ConfigKeys.DEFAULT_HISTORY_LIMIT)

    history_type = config_dict[ConfigKeys.HISTORY][ConfigKeys.TYPE]
    if history_type not in [ConfigKeys.HISTORY_TYPE_UNREAD, ConfigKeys.HISTORY_TYPE_TOP]:
        raise ValueError('unkonwn history type %s' % history_type)

    try:
        limit = int(config_dict[ConfigKeys.HISTORY][ConfigKeys.LIMIT])
        if limit < 1 or limit > 10000:
            raise ValueError('limit not in range [1, 10000]')
    except Exception as e:
        raise RuntimeError(
                'invalid history limit "%s": %s' %
                (str(config_dict[ConfigKeys.HISTORY][ConfigKeys.LIMIT]), str(e)))

    if ConfigKeys.DATE_FORMAT not in config_dict:
        date_format = ConfigKeys.DEFAULT_DATE_FORMAT
        config_dict[ConfigKeys.DATE_FORMAT] = date_format
    else:
        from datetime import datetime
        date_format = config_dict[ConfigKeys.DATE_FORMAT]
        try:
            datetime.utcnow().strftime(date_format)
        except:
            raise RuntimeError('invalid date format: %s' % date_format)

    if ConfigKeys.LOG_FORMAT not in config_dict:
        log_format = ConfigKeys.DEFAULT_LOG_FORMAT
        config_dict[ConfigKeys.LOG_FORMAT] = log_format

    if ConfigKeys.LOG_LEVEL not in config_dict:
        config_dict[ConfigKeys.LOG_LEVEL] = ConfigKeys.DEFAULT_LOG_LEVEL

    config_dict[ConfigKeys.ACL] = get_acl_config()

    root_path = os.path.dirname(config_path)

    gn_env = GNEnvironment(root_path, ConfigDict(config_dict))

    logger.info('read config and created environment')
    logger.debug(str(config_dict))
    return gn_env


def get_acl_config() -> dict:
    acl_paths = None
    if 'DINO_ACL' in os.environ:
        acl_paths = [os.environ['DINO_ACL']]

    acls, _ = find_config_acl(acl_paths)

    if acls is None or len(acls) == 0:
        return MappingProxyType({
            'room': dict(),
            'channel': dict(),
            'available': dict(),
        })

    check_acls = [
        ('channel', acls.get('channel', None)),
        ('room', acls.get('room', None))
    ]
    checked_acls = {
        'available': dict(),
        'room': dict(),
        'channel': dict()
    }

    AclConfigValidator.validate_acl_config(acls, check_acls)

    for acl_target, target_acls in check_acls:
        if target_acls is None or len(target_acls) == 0:
            continue
        for action in target_acls:
            if target_acls[action] is None:
                continue

            keys = set(target_acls[action]['acls'])

            if 'exclude' in target_acls[action]:
                excludes = target_acls[action]['exclude']
                for exclude in excludes:
                    keys.remove(exclude)

            if action not in checked_acls[acl_target]:
                checked_acls[acl_target][action] = list()
            for acl in keys:
                checked_acls[acl_target][action].append(acl)
    return acls


def init_acl_validators(gn_env: GNEnvironment) -> None:
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    acl_config = gn_env.config.get(ConfigKeys.ACL)

    validators = acl_config['validation']
    for acl_type, validation_config in validators.items():
        validation_type = validation_config['type']

        if validation_type == 'str_in_csv':
            csv = None
            if 'value' in validation_config:
                csv = validation_config['value']

            if csv == '##db##':
                try:
                    csv = gn_env.db.get_acl_validation_value(acl_type, 'str_in_csv')
                except AclValueNotFoundException:
                    logger.warning(
                            'acl config specifies to get value from db but no value found for type '
                            '"%s" and method "str_in_csv", will check for default value' % acl_type)
                    if 'default' not in validation_config or len(validation_config['default'].strip()) == 0:
                        raise RuntimeError('no default value found for type "%s" and method "str_in_csv"' % acl_type)

                    csv = validation_config['default']

            validation_config['value'] = AclStrInCsvValidator(csv)

        elif validation_type == 'range':
            validation_config['value'] = AclRangeValidator()

        elif validation_type == 'disallow':
            validation_config['value'] = AclDisallowValidator()

        elif validation_type == 'samechannel':
            validation_config['value'] = AclSameChannelValidator()

        elif validation_type == 'sameroom':
            validation_config['value'] = AclSameRoomValidator()

        elif validation_type == 'is_admin':
            validation_config['value'] = AclIsAdminValidator()

        elif validation_type == 'is_super_user':
            validation_config['value'] = AclIsSuperUserValidator()

        else:
            raise RuntimeError('unknown validation type "%s"' % validation_type)

    gn_env.config.set(ConfigKeys.ACL, MappingProxyType(acl_config))


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
        gn_env.db = DatabaseRedis(gn_env, host=db_host, port=db_port, db=db_number)
    elif db_type == 'rdbms':
        from dino.db.rdbms.handler import DatabaseRdbms
        gn_env.db = DatabaseRdbms(gn_env)
    else:
        raise RuntimeError('unknown db type "%s", use one of [mock, redis, rdbms]' % db_type)


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
        gn_env.cache = CacheRedis(gn_env, host=cache_host, port=cache_port, db=cache_db)
    elif cache_type == 'memory':
        from dino.cache.redis import CacheRedis
        gn_env.cache = CacheRedis(gn_env, host='mock')
    elif cache_type == 'missall':
        from dino.cache.miss import CacheAllMiss
        gn_env.cache = CacheAllMiss()
    else:
        raise RuntimeError('unknown cache type %s, use one of [redis, mock, missall]' % cache_type)


def init_pub_sub(gn_env: GNEnvironment) -> None:
    def publish(message):
        try:
            with producers[gn_env.queue_connection].acquire(block=True) as producer:
                producer.publish(message, exchange=gn_env.exchange, declare=[gn_env.exchange, gn_env.queue])
        except Exception as e:
            logger.error('could not publish message "%s", because: %s' % (str(message), str(e)))
            print(traceback.format_exc())

    def mock_publish(message):
        pass

    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        gn_env.publish = mock_publish
        return

    gn_env.queue_connection = Connection('redis://localhost:6379/')
    gn_env.exchange = Exchange('node_exchange', type='direct')
    gn_env.queue = Queue('node_queue', gn_env.exchange)
    gn_env.publish = publish


def init_stats_service(gn_env: GNEnvironment) -> None:
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    stats_engine = gn_env.config.get(ConfigKeys.STATS_SERVICE, None)

    if stats_engine is None:
        raise RuntimeError('no stats service specified')

    stats_type = stats_engine.get(ConfigKeys.TYPE, None)
    if stats_type is None:
        raise RuntimeError('no stats type specified, use one of [redis, mock, missall]')

    if stats_type == 'statsd':
        from dino.stats.statsd import StatsdService
        gn_env.stats = StatsdService(gn_env)


def initialize_env(dino_env):
    init_storage_engine(dino_env)
    init_database(dino_env)
    init_auth_service(dino_env)
    init_cache_service(dino_env)
    init_pub_sub(dino_env)
    init_acl_validators(dino_env)
    init_stats_service(dino_env)


_config_paths = None
if 'DINO_CONFIG' in os.environ:
    _config_paths = [os.environ['DINO_CONFIG']]
env = create_env(_config_paths)
initialize_env(env)
