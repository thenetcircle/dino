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

from redis import Redis
from typing import Union
from types import MappingProxyType
from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor

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
from zope.interface import implementer

from dino.config import ConfigKeys
from dino.storage import IStorage
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


class WioEnvironment(object):
    def __init__(self, root_path: Union[str, None], config: ConfigDict, skip_init=False):
        """
        Initialize the environment
        """
        # can skip when testing
        if skip_init:
            return

        self.root_path = root_path
        self.config = config
        self.cache = None
        self.stats = None

        self.out_of_scope_emit = None  # needs to be set later after socketio object has been created
        self.emit = _flask_emit

        self.request = _flask_request
        self.disconnect = _flask_disconnect
        self._force_disconnect_by_sid = None
        self.disconnect_by_sid = None
        self.response_formatter = lambda status_code, data: {'status_code': status_code, 'data': data}

        self.auth = config.get(ConfigKeys.AUTH_SERVICE, None)
        self.db = None
        self.publish = lambda message, external: None
        self.capture_exception = lambda e: False

        self.external_queue_connection = None
        self.external_queue = None
        self.external_exchange = None
        self.queue_connection = None
        self.queue = None
        self.exchange = None

        # self.enrichment_manager: IEnrichmentManager = None
        # self.enrichers: List[Tuple[str, IEnricher]] = list()

        self.enrich = lambda d: d
        self.enrichment_manager = None
        self.enrichers = list()

        self.pub_sub = None
        self.node = None

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


def load_secrets_file(config_dict: dict) -> dict:
    from string import Template
    import ast

    wio_env = os.getenv(ENV_KEY_ENVIRONMENT)
    secrets_path = os.getenv(ENV_KEY_SECRETS)
    if secrets_path is None:
        secrets_path = 'secrets/%s.yaml' % wio_env

    logger.debug('loading secrets file "%s"' % secrets_path)

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
def create_env(config_paths: list = None) -> WioEnvironment:
    logging.basicConfig(level='DEBUG', format=ConfigKeys.DEFAULT_LOG_FORMAT)

    wio_environment = os.getenv(ENV_KEY_ENVIRONMENT)
    logger.info('using environment %s' % wio_environment)

    # assuming tests are running
    if wio_environment is None:
        logger.debug('no environment found, assuming tests are running')
        return WioEnvironment(None, ConfigDict(dict()))

    config_dict, config_path = find_config(config_paths)

    if wio_environment not in config_dict:
        raise RuntimeError('no configuration found for environment "%s"' % wio_environment)

    config_dict = config_dict[wio_environment]
    config_dict = load_secrets_file(config_dict)

    try:
        config_dict[ConfigKeys.VERSION] = pkg_resources.require('dino')[0].version
    except Exception:
        # ignore, it will fail when running tests on CI because we don't include all requirements for dino; no need
        pass

    config_dict[ConfigKeys.ENVIRONMENT] = wio_environment
    config_dict[ConfigKeys.SESSION] = _flask_session
    log_level = config_dict.get(ConfigKeys.LOG_LEVEL, ConfigKeys.DEFAULT_LOG_LEVEL)

    logging.basicConfig(
            level=getattr(logging, log_level),
            format=config_dict.get(ConfigKeys.LOG_FORMAT, ConfigKeys.DEFAULT_LOG_FORMAT))
    logging.getLogger('cassandra').setLevel(logging.WARNING)

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

    root_path = os.path.dirname(config_path)
    wio_env = WioEnvironment(root_path, ConfigDict(config_dict))

    logger.info('read config and created environment')
    return wio_env


@timeit(logger, 'init auth service')
def init_auth_service(wio_env: WioEnvironment):
    if len(wio_env.config) == 0 or wio_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    auth_engine = wio_env.config.get(ConfigKeys.AUTH_SERVICE, None)

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
        wio_env.auth = AuthRedis(host=auth_host, port=auth_port, db=auth_db)
    elif auth_type == 'allowall':
        from dino.auth.simple import AllowAllAuth
        wio_env.auth = AllowAllAuth()
    elif auth_type == 'denyall':
        from dino.auth.simple import DenyAllAuth
        wio_env.auth = DenyAllAuth()
    else:
        raise RuntimeError('unknown auth type, use one of [redis, allowall, denyall]')


@timeit(logger, 'init cache service')
def init_cache_service(wio_env: WioEnvironment):
    if len(wio_env.config) == 0 or wio_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    cache_engine = wio_env.config.get(ConfigKeys.CACHE_SERVICE, None)

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
        wio_env.cache = CacheRedis(wio_env, host=cache_host, port=cache_port, db=cache_db)
    elif cache_type == 'memory':
        from dino.cache.redis import CacheRedis
        wio_env.cache = CacheRedis(wio_env, host='mock')
    elif cache_type == 'missall':
        from dino.cache.miss import CacheAllMiss
        wio_env.cache = CacheAllMiss()
    else:
        raise RuntimeError('unknown cache type %s, use one of [redis, mock, missall]' % cache_type)


@timeit(logger, 'init pub/sub service')
def init_pub_sub(wio_env: WioEnvironment) -> None:
    from dino.wio.endpoint.pubsub import PubSub
    wio_env.pub_sub = PubSub(wio_env)


@timeit(logger, 'init stats service')
def init_stats_service(wio_env: WioEnvironment) -> None:
    if len(wio_env.config) == 0 or wio_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    stats_engine = wio_env.config.get(ConfigKeys.STATS_SERVICE, None)

    if stats_engine is None:
        raise RuntimeError('no stats service specified')

    stats_type = stats_engine.get(ConfigKeys.TYPE, None)
    if stats_type is None:
        raise RuntimeError('no stats type specified, use one of [statsd] (set host to mock if no stats service wanted)')

    if stats_type == 'statsd':
        from dino.stats.statsd import StatsdService
        wio_env.stats = StatsdService(wio_env)
        wio_env.stats.set('connections', 0)


@timeit(logger, 'init response formatter')
def init_response_formatter(wio_env: WioEnvironment):
    if len(wio_env.config) == 0 or wio_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    def get_format_keys() -> list:
        _def_keys = ['status_code', 'data', 'error']

        res_format = wio_env.config.get(ConfigKeys.RESPONSE_FORMAT, None)
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
    wio_env.response_formatter = SimpleResponseFormatter(code_key, data_key, error_key)
    logger.info('configured response formatting as %s' % str(wio_env.response_formatter))


@timeit(logger, 'init logging service')
def init_logging(wio_env: WioEnvironment) -> None:
    if len(wio_env.config) == 0 or wio_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    logging_type = wio_env.config.get(ConfigKeys.TYPE, domain=ConfigKeys.LOGGING, default='logger')
    if logging_type is None or len(logging_type.strip()) == 0 or logging_type in ['logger', 'default', 'mock']:
        return
    if logging_type != 'sentry':
        raise RuntimeError('unknown logging type %s' % logging_type)

    dsn = wio_env.config.get(ConfigKeys.DSN, domain=ConfigKeys.LOGGING, default='')
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

    wio_env.sentry = raven.Client(
        dsn=dsn,
        environment=os.getenv(ENV_KEY_ENVIRONMENT),
        name=socket.gethostname(),
        release=tag_name
    )

    def capture_exception(e_info) -> None:
        try:
            wio_env.sentry.captureException(e_info)
        except Exception as e2:
            logger.exception(e_info)
            logger.error('could not capture exception with sentry: %s' % str(e2))

    wio_env.capture_exception = capture_exception


@timeit(logger, 'init enrichment service')
def init_enrichment_service(wio_env: WioEnvironment):
    if len(wio_env.config) == 0 or wio_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    from dino.enrich.manager import EnrichmentManager
    from dino.enrich.title import TitleEnrichment

    wio_env.enrichment_manager = EnrichmentManager(wio_env)
    wio_env.enrichers = [
        ('title', TitleEnrichment(wio_env)),
    ]
    wio_env.enrich = lambda d: wio_env.enrichment_manager.handle(d)


def initialize_env(dino_env):
    init_logging(dino_env)
    init_auth_service(dino_env)
    init_cache_service(dino_env)
    init_pub_sub(dino_env)
    init_stats_service(dino_env)
    init_response_formatter(dino_env)
    init_enrichment_service(dino_env)


_config_paths = None
if 'DINO_CONFIG' in os.environ:
    _config_paths = [os.environ['DINO_CONFIG']]

env = create_env(_config_paths)
initialize_env(env)
