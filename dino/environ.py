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
import eventlet

from typing import Union
from types import MappingProxyType
from base64 import b64encode

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
from dino.exceptions import NoSuchRoomException

from dino.validation.acl import AclConfigValidator
from dino.validation.acl import AclRangeValidator
from dino.validation.acl import AclStrInCsvValidator
from dino.validation.acl import AclSameChannelValidator
from dino.validation.acl import AclSameRoomValidator
from dino.validation.acl import AclDisallowValidator
from dino.validation.acl import AclIsAdminValidator
from dino.validation.acl import AclIsSuperUserValidator
from dino.validation.acl import AclPatternValidator
from dino.validation.acl import AclIsRoomOwnerValidator

ENV_KEY_ENVIRONMENT = 'DINO_ENVIRONMENT'
ENV_KEY_SECRETS = 'DINO_SECRETS'

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
    def __init__(self, root_path: Union[str, None]=None, config: ConfigDict=None, skip_init=False):
        """
        Initialize the environment
        """

        self.root_path = root_path
        self.config = config

        # can skip when testing
        if skip_init:
            return
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
        self.response_formatter = lambda status_code, data: {'status_code': status_code, 'data': data}

        self.logger = config.get(ConfigKeys.LOGGER, None)
        self.session = config.get(ConfigKeys.SESSION, None)
        self.auth = config.get(ConfigKeys.AUTH_SERVICE, None)
        self.db = None
        self.capture_exception = lambda e: False

        self.web_auth = None

        # self.enrichment_manager: IEnrichmentManager = None
        # self.enrichers: List[Tuple[str, IEnricher]] = list()

        self.enrich = lambda d: d
        self.enrichment_manager = None
        self.enrichers = list()

        self.pub_sub = None
        self.publish = lambda message, external: None
        self.internal_publisher = None
        self.external_publisher = None
        self.consume_worker = None

        self.blacklist = None
        self.node = None
        self.service_config = None
        self.spam = None
        self.heartbeat = None
        self.remote = None

        self.event_validator_map = dict()
        self.event_validators = dict()
        self.connected_user_ids = dict()


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


def find_config(config_paths: list) -> tuple:
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


def find_config_acl(acl_paths: list) -> (dict, str):
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
                acl_dict = yaml.safe_load(open(path))
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


def configure_request_log(gn_environment: str, config_dict: dict):
    request_log_location = config_dict.get(ConfigKeys.REQ_LOG_LOC, None)
    request_log_disabled = \
        request_log_location is None or str(request_log_location).lower() in {'false', 'mock', 'no', '', 'none', 'n'}

    if request_log_disabled:
        logging.getLogger('engineio').setLevel(logging.WARNING)
        return

    log_level = config_dict.get(ConfigKeys.LOG_LEVEL, ConfigKeys.DEFAULT_LOG_LEVEL)
    debug_enabled = str(os.environ.get('DINO_DEBUG', 0)).lower() in {'1', 'true', 'yes', 'y'}

    if log_level == 'DEBUG' or debug_enabled:
        import sys
        args = sys.argv
        for a in ['--bind', '-b']:
            bind_arg_pos = [i for i, x in enumerate(args) if x == a]
            if len(bind_arg_pos) > 0:
                bind_arg_pos = bind_arg_pos[0]
                break

        port = 'standalone'
        if bind_arg_pos is not None and not isinstance(bind_arg_pos, list):
            port = args[bind_arg_pos + 1].split(':')[1]

        engineio_logger = logging.getLogger('engineio')
        log_loc = config_dict.get(ConfigKeys.REQ_LOG_LOC, '/var/log/dino')
        file_handler = logging.FileHandler('%s/engineio-%s-%s.log' % (log_loc, gn_environment, port))
        formatter = logging.Formatter(ConfigKeys.DEFAULT_LOG_FORMAT)
        file_handler.setFormatter(formatter)

        if engineio_logger.hasHandlers():
            for handler in engineio_logger.handlers.copy():
                engineio_logger.removeHandler(handler)

        engineio_logger.propagate = False
        engineio_logger.addHandler(file_handler)
        engineio_logger.setLevel(logging.DEBUG)
    else:
        logging.getLogger('engineio').setLevel(config_dict.get(ConfigKeys.LOG_LEVEL, ConfigKeys.DEFAULT_LOG_LEVEL))


@timeit(logger, 'creating base environment')
def create_env(config_paths: list = None) -> GNEnvironment:
    logging.basicConfig(level='DEBUG', format=ConfigKeys.DEFAULT_LOG_FORMAT)

    gn_environment = os.getenv(ENV_KEY_ENVIRONMENT)
    logger.info('using environment %s' % gn_environment)

    # assuming tests are running
    if gn_environment is None:
        logger.debug('no environment found, assuming tests are running')
        return GNEnvironment(None, ConfigDict(dict()))

    config_dict, config_path = find_config(config_paths)

    if gn_environment not in config_dict:
        raise RuntimeError('no configuration found for environment "%s"' % gn_environment)

    config_dict = config_dict[gn_environment]
    config_dict = load_secrets_file(config_dict)

    if ConfigKeys.STORAGE not in config_dict:
        raise RuntimeError('no storage configured for environment %s' % gn_environment)

    try:
        config_dict[ConfigKeys.VERSION] = pkg_resources.require('dino')[0].version
    except Exception:
        # ignore, it will fail when running tests on CI because we don't include all requirements for dino; no need
        pass

    config_dict[ConfigKeys.ENVIRONMENT] = gn_environment
    config_dict[ConfigKeys.SESSION] = _flask_session
    log_level = config_dict.get(ConfigKeys.LOG_LEVEL, ConfigKeys.DEFAULT_LOG_LEVEL)
    configure_request_log(gn_environment, config_dict)

    logging.basicConfig(
            level=getattr(logging, log_level),
            format=config_dict.get(ConfigKeys.LOG_FORMAT, ConfigKeys.DEFAULT_LOG_FORMAT))
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


def get_acl_config() -> Union[MappingProxyType, dict]:
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

        elif validation_type == 'is_room_owner':
            validation_config['value'] = AclIsRoomOwnerValidator()

        elif validation_type == 'is_super_user':
            validation_config['value'] = AclIsSuperUserValidator()

        else:
            raise RuntimeError('unknown validation type "%s"' % validation_type)

    gn_env.config.set(ConfigKeys.ACL, MappingProxyType(acl_config))


def init_fake_storage_engine(gn_env: GNEnvironment) -> None:
    class FakeStorage(object):
        def __getattr__(self, item):
            def method(*args, **kwargs):
                return list()
            return method

    gn_env.storage = FakeStorage()


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
        if db_port is not None:
            db_port = int(db_port)
        if db_number is not None:
            db_number = int(db_number)

        gn_env.db = DatabaseRedis(gn_env, host=db_host, port=db_port, db=db_number)

    elif db_type == 'rdbms':
        from dino.db.rdbms.handler import DatabaseRdbms
        gn_env.db = DatabaseRdbms(gn_env)
        gn_env.db.init_config()

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
        raise RuntimeError('no auth type specified, use one of [redis, nutcracker, allowall, denyall]')

    if auth_type == 'redis' or auth_type == 'nutcracker':
        from dino.auth.redis import AuthRedis

        auth_host, auth_port = auth_engine.get(ConfigKeys.HOST), None
        if ':' in auth_host:
            auth_host, auth_port = auth_host.split(':', 1)

        auth_db = auth_engine.get(ConfigKeys.DB, 0)
        gn_env.auth = AuthRedis(host=auth_host, port=auth_port, db=auth_db, env=gn_env)

    elif auth_type == 'allowall':
        from dino.auth.simple import AllowAllAuth
        gn_env.auth = AllowAllAuth()

    elif auth_type == 'denyall':
        from dino.auth.simple import DenyAllAuth
        gn_env.auth = DenyAllAuth()

    else:
        raise RuntimeError(
            'unknown auth type "{}", use one of [redis, nutcracker, allowall, denyall]'.format(auth_type))


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
        raise RuntimeError('no cache type specified, use one of [redis, nutcracker, memory, missall]')

    if cache_type == 'redis' or cache_type == 'nutcracker':
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
        raise RuntimeError('unknown cache type %s, use one of [redis, nutcracker, memory, missall]' % cache_type)


@timeit(logger, 'init pub/sub service')
def init_pub_sub(gn_env: GNEnvironment) -> None:
    from dino.endpoint.pubsub import PubSub
    gn_env.pub_sub = PubSub(gn_env)


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
        raise RuntimeError('no stats type specified, use one of [statsd] (set host to mock if no stats service wanted)')

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


@timeit(logger, 'init response formatter')
def init_response_formatter(gn_env: GNEnvironment):
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    def get_format_keys() -> list:
        _def_keys = ['status_code', 'data', 'error']

        res_format = gn_env.config.get(ConfigKeys.RESPONSE_FORMAT, None)
        if res_format is None:
            logger.info('using default response format, no config specified')
            return _def_keys

        if type(res_format) != str:
            logger.warning('configured response format is of type "%s", using default' % str(type(res_format)))
            return _def_keys

        if len(res_format.strip()) == 0:
            logger.warning('configured response format is blank, using default')
            return _def_keys

        keys = res_format.split(',')
        if len(keys) != 3:
            logger.warning('configured response format not "<code>,<data>,<error>" but "%s", using default' % res_format)
            return _def_keys

        for i, key in enumerate(keys):
            if len(key.strip()) == 0:
                logger.warning('response format key if index %s is blank in "%s", using default' % (str(i), keys))
                return _def_keys
        return keys

    code_key, data_key, error_key = get_format_keys()

    from dino.utils.formatter import SimpleResponseFormatter
    gn_env.response_formatter = SimpleResponseFormatter(code_key, data_key, error_key)
    logger.info('configured response formatting as %s' % str(gn_env.response_formatter))


@timeit(logger, 'deleting ephemeral rooms')
def delete_ephemeral_rooms(gn_env: GNEnvironment):
    from activitystreams import parse as as_parser

    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    def delete():
        from dino import utils

        channel_dict = gn_env.db.get_channels()

        for channel_id, *_ in channel_dict.items():
            rooms = gn_env.db.rooms_for_channel(channel_id)

            for room_id, room_info in rooms.items():
                short_id = room_id.split('-')[0]
                room_name = room_info['name']
                logger.debug('checking room %s: %s' % (room_id, room_name))

                users = gn_env.db.users_in_room(room_id)
                if len(users) > 0:
                    logger.debug('[%s] NOT removing room (%s), has % user(s) in it' % (short_id, room_name, len(users)))
                    continue

                if not room_info['ephemeral']:
                    logger.debug('[%s] NOT removing room (%s), not ephemeral' % (short_id, room_name))
                    continue

                logger.info('[%s] removing ephemeral room (%s)' % (short_id, room_name))

                try:
                    gn_env.db.get_room_name(room_id)
                except NoSuchRoomException:
                    logger.info('[%s] ephemeral room (%s) has already been removed' % (short_id, room_name))
                    continue

                activity = utils.activity_for_remove_room('0', 'server', room_id, room_name, 'empty ephemeral room')

                gn_env.db.remove_room(channel_id, room_id)

                # no need to notify for wio
                if gn_env.node is not None and 'wio' not in gn_env.node:
                    gn_env.out_of_scope_emit(
                        'gn_room_removed', activity, broadcast=True, include_self=True, namespace='/ws')

                gn_env.observer.emit('on_remove_room', (activity, as_parser(activity)))

    eventlet.spawn_after(seconds=30*60, func=delete)


@timeit(logger, 'init logging service')
def init_logging(gn_env: GNEnvironment) -> None:
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    logging_type = gn_env.config.get(ConfigKeys.TYPE, domain=ConfigKeys.LOGGING, default='logger')
    if logging_type is None or len(logging_type.strip()) == 0 or logging_type in ['logger', 'default', 'mock']:
        return
    if logging_type != 'sentry':
        raise RuntimeError('unknown logging type %s' % logging_type)

    dsn = gn_env.config.get(ConfigKeys.DSN, domain=ConfigKeys.LOGGING, default='')
    if dsn is None or len(dsn.strip()) == 0:
        logger.warning('sentry logging selected but no DSN supplied, not configuring senty')
        return

    import raven
    import socket
    from git.cmd import Git

    home_dir = os.environ.get('DINO_HOME', default=None)
    if home_dir is None:
        home_dir = '.'
    tag_name = Git(home_dir).describe()

    gn_env.sentry = raven.Client(
        dsn=dsn,
        environment=os.getenv(ENV_KEY_ENVIRONMENT),
        name=socket.gethostname(),
        release=tag_name
    )

    def capture_exception(e_info) -> None:
        try:
            gn_env.sentry.captureException(e_info)
        except Exception as e2:
            logger.exception(e_info)
            logger.error('could not capture exception with sentry: %s' % str(e2))

    gn_env.capture_exception = capture_exception


@timeit(logger, 'init spam service')
def init_spam_service(gn_env: GNEnvironment):
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    if not gn_env.config.get(ConfigKeys.SPAM_CLASSIFIER, default=False):
        return

    from dino.utils.spam import SpamClassifier
    gn_env.spam = SpamClassifier(gn_env)


@timeit(logger, 'init enrichment service')
def init_enrichment_service(gn_env: GNEnvironment):
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    if gn_env.config.get(ConfigKeys.ENRICH, None) is None:
        # not enabled
        return

    from dino.enrich.manager import EnrichmentManager
    from dino.enrich.title import TitleEnrichment

    gn_env.enrichment_manager = EnrichmentManager(gn_env)
    gn_env.enrichers = [
        ('title', TitleEnrichment(gn_env)),
    ]
    gn_env.enrich = lambda d: gn_env.enrichment_manager.handle(d)


@timeit(logger, 'init heartbeat service')
def init_heartbeat_service(gn_env: GNEnvironment):
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    from dino.heartbeat.manager import HeartbeatManager
    gn_env.heartbeat = HeartbeatManager(gn_env)


@timeit(logger, 'init web auth service')
def init_web_auth(gn_env: GNEnvironment) -> None:
    """
    manually invoked after app initialized
    """
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    web_auth_type = gn_env.config.get(ConfigKeys.TYPE, domain=ConfigKeys.WEB, default=None)
    if not web_auth_type or str(web_auth_type).strip().lower() in ['false', 'none', '']:
        logger.info('auth type was "{}", not initializing web auth'.format(web_auth_type))
        return

    if web_auth_type not in {'oauth'}:
        raise RuntimeError('unknown web auth type "{}", only "oauth" is available'.format(str(web_auth_type)))

    from dino.admin.auth.oauth import OAuthService
    gn_env.web_auth = OAuthService(gn_env)
    logger.info('initialized OAuthService')


@timeit(logger, 'init config service')
def init_service_config(gn_env: GNEnvironment) -> None:
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    from dino.config import ConfigService
    gn_env.service_config = ConfigService(gn_env)


@timeit(logger, 'init remote call handler')
def init_remote_handler(gn_env: GNEnvironment) -> None:
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    from dino.remote.handler import RemoteHandler
    gn_env.remote = RemoteHandler(gn_env)


def initialize_env(dino_env):
    init_logging(dino_env)
    init_database(dino_env)
    init_auth_service(dino_env)
    init_cache_service(dino_env)
    init_pub_sub(dino_env)
    init_stats_service(dino_env)
    init_observer(dino_env)
    init_request_validators(dino_env)
    init_response_formatter(dino_env)
    init_enrichment_service(dino_env)

    if 'wio' in dino_env.config.get(ConfigKeys.ENVIRONMENT, 'default'):
        init_fake_storage_engine(dino_env)
        init_heartbeat_service(dino_env)
        delete_ephemeral_rooms(dino_env)
    else:
        init_blacklist_service(dino_env)
        init_admin_and_admin_room(dino_env)
        init_acl_validators(dino_env)
        init_storage_engine(dino_env)
        init_spam_service(dino_env)
        init_service_config(dino_env)
        init_remote_handler(dino_env)


_config_paths = None
if 'DINO_CONFIG' in os.environ:
    _config_paths = [os.environ['DINO_CONFIG']]

env = create_env(_config_paths)
initialize_env(env)
