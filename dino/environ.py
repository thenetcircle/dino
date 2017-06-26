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
import time

from redis import Redis
from typing import Union
from types import MappingProxyType
from base64 import b64encode

from kombu import Exchange
from kombu import Queue
from kombu import Connection
from kombu.pools import producers

from flask_socketio import emit as _flask_emit
from flask_socketio import send as _flask_send
from flask_socketio import join_room as _flask_join_room
from flask_socketio import leave_room as _flask_leave_room

from flask_wtf import FlaskForm as _flask_Form
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
from dino.utils.decorators import timeit
from dino.exceptions import AclValueNotFoundException

from dino.validation.acl import AclConfigValidator
from dino.validation.acl import AclRangeValidator
from dino.validation.acl import AclStrInCsvValidator
from dino.validation.acl import AclSameChannelValidator
from dino.validation.acl import AclSameRoomValidator
from dino.validation.acl import AclDisallowValidator
from dino.validation.acl import AclIsAdminValidator
from dino.validation.acl import AclIsSuperUserValidator
from dino.validation.acl import AclPatternValidator

ENV_KEY_ENVIRONMENT = 'DINO_ENVIRONMENT'

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
        self.observer = None

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
        self._force_disconnect_by_sid = None
        self.disconnect_by_sid = None

        self.logger = config.get(ConfigKeys.LOGGER, None)
        self.session = config.get(ConfigKeys.SESSION, None)
        self.auth = config.get(ConfigKeys.AUTH_SERVICE, None)
        self.db = None
        self.publish = lambda message, external: None
        self.queue_connection = None
        self.queue = None
        self.pubsub = None
        self.exchange = None
        self.consume_worker = None
        self.start_consumer = None
        self.blacklist = None
        self.node = None

        self.event_validator_map = dict()
        self.event_validators = dict()
        self.connected_user_ids = dict()

        # TODO: remove this, go through storage interface
        self.redis = config.get(ConfigKeys.REDIS, None)


def b64e(s: str) -> str:
    if s is None:
        return ''

    s = s.strip()
    if len(s) == 0:
        return ''

    try:
        return str(b64encode(bytes(s, 'utf-8')), 'utf-8')
    except Exception as e:
        logger.error('could not b64encode because: %s, value was: \n%s' % (str(e), str(s)))
    return ''


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
    if len(config_dict) == 0 or ConfigKeys.CACHE_SERVICE not in config_dict:
        # assume we're testing
        from fakeredis import FakeStrictRedis
        return FakeStrictRedis()

    queue_type = config_dict.get(ConfigKeys.CACHE_SERVICE).get(ConfigKeys.TYPE, 'mock')

    if queue_type == 'mock':
        from fakeredis import FakeStrictRedis
        return FakeStrictRedis()
    elif queue_type == 'redis':
        redis_host = config_dict.get(ConfigKeys.CACHE_SERVICE).get(ConfigKeys.HOST, 'localhost')
        redis_port = 6379

        if redis_host.startswith('redis://'):
            redis_host = redis_host.replace('redis://', '')

        if ':' in redis_host:
            redis_host, redis_port = redis_host.split(':', 1)

        return Redis(redis_host, port=redis_port)

    raise RuntimeError('unknown queue type "%s"' % queue_type)


def load_secrets_file(config_dict: dict) -> dict:
    from string import Template
    import ast

    gn_env = os.getenv(ENV_KEY_ENVIRONMENT)
    secrets_path = 'secrets/%s.yaml' % gn_env

    # first substitute environment variables, which holds precedence over the yaml config (if it exists)
    template = Template(str(config_dict))
    template = template.safe_substitute(os.environ)

    if os.path.isfile(secrets_path):
        try:
            secrets = yaml.load(open(secrets_path))
        except Exception as e:
            raise RuntimeError("Failed to open secrets configuration {0}: {1}".format(secrets_path, str(e)))
        template = Template(template)
        template = template.safe_substitute(secrets)

    return ast.literal_eval(template)


@timeit(logger, 'creating base environment')
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
    config_dict = load_secrets_file(config_dict)

    if ConfigKeys.STORAGE not in config_dict:
        raise RuntimeError('no storage configured for environment %s' % gn_environment)

    config_dict[ConfigKeys.REDIS] = choose_queue_instance(config_dict)

    try:
        config_dict[ConfigKeys.VERSION] = pkg_resources.require('dino')[0].version
    except Exception:
        # ignore, it will fail when running tests on CI because we don't include all requirements for dino; no need
        pass

    config_dict[ConfigKeys.ENVIRONMENT] = gn_environment
    config_dict[ConfigKeys.SESSION] = _flask_session

    logging.basicConfig(
            level=getattr(logging, config_dict.get(ConfigKeys.LOG_LEVEL, 'DEBUG')),
            format=config_dict.get(ConfigKeys.LOG_FORMAT, ConfigKeys.DEFAULT_LOG_FORMAT))
    logging.getLogger('engineio').setLevel(logging.WARNING)
    logging.getLogger('cassandra').setLevel(logging.WARNING)

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


@timeit(logger, 'init validation service')
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

        elif validation_type == 'custom':
            validation_config['value'] = AclPatternValidator()

        elif validation_type == 'sameroom':
            validation_config['value'] = AclSameRoomValidator()

        elif validation_type == 'is_admin':
            validation_config['value'] = AclIsAdminValidator()

        elif validation_type == 'is_super_user':
            validation_config['value'] = AclIsSuperUserValidator()

        else:
            raise RuntimeError('unknown validation type "%s"' % validation_type)

    gn_env.config.set(ConfigKeys.ACL, MappingProxyType(acl_config))


@timeit(logger, 'init storage service')
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
        key_space = gn_env.config.get(ConfigKeys.ENVIRONMENT, 'dino')
        gn_env.storage = CassandraStorage(storage_hosts, replications=replication, strategy=strategy, key_space=key_space)
        gn_env.storage.init()
    else:
        raise RuntimeError('unknown storage engine type "%s"' % storage_type)


@timeit(logger, 'init db service')
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


@timeit(logger, 'init auth service')
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


@timeit(logger, 'init cache service')
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


@timeit(logger, 'init pub/sub service')
def init_pub_sub(gn_env: GNEnvironment) -> None:
    recently_sent_external_hash = set()
    recently_sent_external_list = list()

    def error_callback(exc, interval):
        logger.warn('could not connect to MQ: %s' % str(exc))

    def publish(message, external=None):
        logger.debug('publish: verb %s id %s external? %s' % (message['verb'], message['id'], str(external or False)))
        if external is None or not external:
            external = False

        if external and gn_env.node != 'rest':
            # avoid publishing duplicate events by only letting the rest node publish external events
            return

        if external and message['id'] in recently_sent_external_hash:
            logger.debug(
                    'ignoring external event with verb %s and id %s, already sent' %
                    (message['verb'], message['id']))
            return

        try:
            start = time.time()
            n_tries = 3
            current_try = 0
            failed = False

            if external:
                message_type = 'external'
                queue_connection = gn_env.external_queue_connection
                if queue_connection is None:
                    return
                exchange = gn_env.external_exchange
                queue = gn_env.external_queue
            else:
                message_type = 'internal'
                queue_connection = gn_env.queue_connection
                if queue_connection is None:
                    return
                exchange = gn_env.exchange
                queue = gn_env.queue

            with producers[queue_connection].acquire(block=True) as producer:
                amqp_publish = queue_connection.ensure(producer, producer.publish, errback=error_callback, max_retries=3)

                for current_try in range(n_tries):
                    try:
                        amqp_publish(message, exchange=exchange, declare=[exchange, queue])
                        gn_env.stats.incr('publish.%s.count' % message_type)
                        gn_env.stats.timing('publish.%s.time' % message_type, (time.time()-start)*1000)
                        failed = False

                        if external:
                            recently_sent_external_hash.add(message['id'])
                            recently_sent_external_list.append(message['id'])
                            if len(recently_sent_external_list) > 100:
                                old_id = recently_sent_external_list.pop(0)
                                recently_sent_external_hash.remove(old_id)

                        break
                    except Exception as pe:
                        failed = True
                        logger.error('[%s/%s tries] failed to publish %s: %s' % (str(current_try+1), str(n_tries), message_type, str(pe)))
                        logger.exception(traceback.format_exc())
                        gn_env.stats.incr('publish.error')
                        time.sleep(0.1)

            if failed:
                logger.error(
                        'failed to publish %s event %s times! Republishing to internal queue' %
                        (message_type, str(n_tries)))
                publish(message)
            elif current_try > 0:
                logger.info('published successfully on attempt %s/%s' % (str(current_try+1), str(n_tries)))
            else:
                logger.debug(
                        'published %s event with verb %s id %s' %
                        (message_type, message['verb'], message['id']))

        except Exception as e:
            logger.error('could not publish message "%s", because: %s' % (str(message), str(e)))
            logger.exception(traceback.format_exc())
            gn_env.stats.incr('publish.error')

    def mock_publish(message, external=False):
        pass

    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        gn_env.publish = mock_publish
        return

    conf = gn_env.config
    gn_env.publish = publish

    queue_host = conf.get(ConfigKeys.HOST, domain=ConfigKeys.QUEUE, default=None)
    queue_type = conf.get(ConfigKeys.TYPE, domain=ConfigKeys.QUEUE, default=None)
    gn_env.queue_connection = None

    import sys
    import socket

    args = sys.argv
    bind_arg_pos = None
    for a in ['--bind', '-b']:
        bind_arg_pos = [i for i,x in enumerate(args) if x == a]
        if len(bind_arg_pos) > 0:
            bind_arg_pos = bind_arg_pos[0]
            break

    port = args[bind_arg_pos+1].split(':')[1]
    hostname = socket.gethostname()

    if queue_host is not None:
        if queue_type == 'redis':
            gn_env.queue_connection = Connection(queue_host)
            gn_env.queue_name = conf.get(ConfigKeys.QUEUE, domain=ConfigKeys.QUEUE, default=None)
            if gn_env.queue_name is None or len(gn_env.queue_name.strip()) == 0:
                gn_env.queue_name = 'node_queue_%s_%s_%s' % (
                    conf.get(ConfigKeys.ENVIRONMENT),
                    hostname,
                    port
                )

            exchange = conf.get(ConfigKeys.EXCHANGE, domain=ConfigKeys.QUEUE, default='node_exchange')
            gn_env.exchange = Exchange(exchange, type='fanout')
            gn_env.queue = Queue(gn_env.queue_name, gn_env.exchange)

        elif queue_type == 'amqp':
            queue_port = conf.get(ConfigKeys.PORT, domain=ConfigKeys.QUEUE, default=None)
            queue_vhost = conf.get(ConfigKeys.VHOST, domain=ConfigKeys.QUEUE, default=None)
            queue_user = conf.get(ConfigKeys.USER, domain=ConfigKeys.QUEUE, default=None)
            queue_pass = conf.get(ConfigKeys.PASSWORD, domain=ConfigKeys.QUEUE, default=None)
            queue_exchange = '%s_%s' % (
                conf.get(ConfigKeys.EXCHANGE, domain=ConfigKeys.QUEUE, default=None),
                conf.get(ConfigKeys.ENVIRONMENT)
            )
            gn_env.queue_name = conf.get(ConfigKeys.QUEUE, domain=ConfigKeys.QUEUE, default=None)

            if gn_env.queue_name is None or len(gn_env.queue_name.strip()) == 0:
                gn_env.queue_name = 'node_queue_%s_%s_%s' % (
                    conf.get(ConfigKeys.ENVIRONMENT),
                    hostname,
                    port
                )

            queue_host = ';'.join(['amqp://%s' % host for host in queue_host.split(';')])
            gn_env.queue_connection = Connection(
                    hostname=queue_host, port=queue_port, virtual_host=queue_vhost, userid=queue_user, password=queue_pass)
            gn_env.exchange = Exchange(queue_exchange, type='fanout')
            gn_env.queue = Queue(gn_env.queue_name, gn_env.exchange)

    if gn_env.queue_connection is None:
        raise RuntimeError('no message queue specified, need either redis or amqp')

    ext_queue_host = conf.get(ConfigKeys.HOST, domain=ConfigKeys.EXTERNAL_QUEUE, default='')
    gn_env.external_queue_connection = None
    if ext_queue_host is not None and len(ext_queue_host.strip()) > 0:
        ext_port = conf.get(ConfigKeys.PORT, domain=ConfigKeys.EXTERNAL_QUEUE, default=None)
        ext_vhost = conf.get(ConfigKeys.VHOST, domain=ConfigKeys.EXTERNAL_QUEUE, default=None)
        ext_user = conf.get(ConfigKeys.USER, domain=ConfigKeys.EXTERNAL_QUEUE, default=None)
        ext_pass = conf.get(ConfigKeys.PASSWORD, domain=ConfigKeys.EXTERNAL_QUEUE, default=None)
        ext_exchange = conf.get(ConfigKeys.EXCHANGE, domain=ConfigKeys.EXTERNAL_QUEUE, default=None)
        ext_queue = conf.get(ConfigKeys.QUEUE, domain=ConfigKeys.EXTERNAL_QUEUE, default=None)

        gn_env.external_queue_connection = Connection(
                hostname=ext_queue_host, port=ext_port, virtual_host=ext_vhost, userid=ext_user, password=ext_pass)
        gn_env.external_exchange = Exchange(ext_exchange, type='direct')
        gn_env.external_queue = Queue(ext_queue, gn_env.external_exchange)


@timeit(logger, 'init stats service')
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
        gn_env.stats.set('connections', 0)


@timeit(logger, 'init observers')
def init_observer(gn_env: GNEnvironment) -> None:
    from pymitter import EventEmitter
    gn_env.observer = EventEmitter()


@timeit(logger, 'init request validators')
def init_request_validators(gn_env: GNEnvironment) -> None:
    from yapsy.PluginManager import PluginManager
    logging.getLogger('yapsy').setLevel(gn_env.config.get(ConfigKeys.LOG_LEVEL, logging.INFO))

    plugin_manager = PluginManager()
    plugin_manager.setPluginPlaces(['dino/validation/events'])
    plugin_manager.collectPlugins()

    for pluginInfo in plugin_manager.getAllPlugins():
        plugin_manager.activatePluginByName(pluginInfo.name)
        gn_env.event_validators[pluginInfo.name] = pluginInfo.plugin_object

    validation = gn_env.config.get(ConfigKeys.VALIDATION, None)
    if validation is None:
        return

    for key in validation.keys():
        if key not in gn_env.event_validator_map:
            gn_env.event_validator_map[key] = list()
        plugins = validation[key].copy()
        validation[key] = dict()
        for plugin_info in plugins:
            plugin_name = plugin_info.get('name')
            validation[key][plugin_name] = plugin_info
            try:
                gn_env.event_validator_map[key].append(gn_env.event_validators[plugin_name])
            except KeyError:
                raise KeyError('specified plugin "%s" does not exist' % key)

    gn_env.config.set(ConfigKeys.VALIDATION, validation)

    for pluginInfo in plugin_manager.getAllPlugins():
        pluginInfo.plugin_object.setup(gn_env)


@timeit(logger, 'init blacklist')
def init_blacklist_service(gn_env: GNEnvironment):
    from dino.utils.blacklist import BlackListChecker
    gn_env.blacklist = BlackListChecker(gn_env)


@timeit(logger, 'creating admin room')
def init_admin_and_admin_room(gn_env: GNEnvironment):
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return
    # will create the admin user and room if not already existing
    gn_env.db.create_admin_room()


@timeit(logger, 'deleting ephemeral rooms')
def delete_ephemeral_rooms(gn_env: GNEnvironment):
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return
    channel_dict = gn_env.db.get_channels()
    for channel_id, _ in channel_dict.items():
        rooms = gn_env.db.rooms_for_channel(channel_id)
        for room_uuid, room_info in rooms.items():
            logger.debug('checking room %s: %s' % (room_uuid, str(room_info)))
            if room_info['ephemeral']:
                logger.info('removing ephemeral room "%s" (%s)' % (room_info['name'], room_uuid))
                gn_env.db.remove_room(channel_id, room_uuid)


def initialize_env(dino_env):
    init_storage_engine(dino_env)
    init_database(dino_env)
    init_auth_service(dino_env)
    init_cache_service(dino_env)
    init_pub_sub(dino_env)
    init_acl_validators(dino_env)
    init_stats_service(dino_env)
    init_observer(dino_env)
    init_request_validators(dino_env)
    init_blacklist_service(dino_env)
    init_admin_and_admin_room(dino_env)
    delete_ephemeral_rooms(dino_env)


_config_paths = None
if 'DINO_CONFIG' in os.environ:
    _config_paths = [os.environ['DINO_CONFIG']]

env = create_env(_config_paths)
initialize_env(env)
