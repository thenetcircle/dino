import yaml
import json
import os
import sys
import pkg_resources
import logging
from logging import RootLogger
from redis import Redis

ENV_KEY_ENVIRONMENT = 'ENVIRONMENT'


class ConfigKeys:
    LOG_LEVEL = 'log_level'
    REDIS_HOST = 'redis_host'
    LOG_FORMAT = 'log_format'
    DEBUG = 'debug'
    TESTING = 'testing'

    # will be overwritten even if specified in config file
    ENVIRONMENT = 'environment'
    VERSION = 'version'
    LOGGER = 'logger'
    REDIS = 'redis'
    SESSION = 'session'

    DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)-18s - %(levelname)-7s - %(message)s"
    DEFAULT_LOG_LEVEL = 'INFO'
    DEFAULT_REDIS_HOST = 'localhost'


class GNEnvironment(object):
    def __init__(self, root_path, config):
        """
        Initialize the environment
        """
        self.root_path = root_path
        self.config = config
        self.commands = dict()

    def redis(self):
        return self.config.get(ConfigKeys.REDIS, None)

    def session(self):
        return self.config.get(ConfigKeys.SESSION, None)

    def logger(self):
        return self.config.get(ConfigKeys.LOGGER, None)

    def merge(self, config):
        self.config = self.config.sub(**config)

    def setup(self):
        pass

    def shutdown(self):
        pass


def create_env() -> GNEnvironment:
    def error(text: str, args=None) -> None:
        if args is None:
            print(text, file=sys.stderr)
        else:
            print(text, args, file=sys.stderr)

    def create_logger(_config_dict: dict) -> RootLogger:
        logging.basicConfig(
                level=getattr(logging, _config_dict.get(ConfigKeys.LOG_LEVEL, 'INFO')),
                format=_config_dict.get(ConfigKeys.LOG_FORMAT, ConfigKeys.DEFAULT_LOG_FORMAT))
        return logging.getLogger(__name__)

    config_paths = ["grid.yaml", "grid.json"]
    config_dict = None
    config_path = None

    gn_environment = os.getenv(ENV_KEY_ENVIRONMENT)

    # assuming tests are running
    if gn_environment is None:
        return GNEnvironment(None, config_dict)

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
                error("Unsupported file extension: {0}".format(conf))
                sys.exit(1)
        except Exception as e:
            error("Failed to open configuration {0}: {1}".format(conf, str(e)))
            sys.exit(1)

        config_path = path
        break

    if not config_dict:
        error("No configuration found: {0}\n".format(", ".join(config_paths)))
        sys.exit(1)

    if gn_environment not in config_dict:
        raise RuntimeError('no configuration found for environment "%s"' % gn_environment)

    config_dict = config_dict[gn_environment]
    config_dict[ConfigKeys.ENVIRONMENT] = gn_environment
    config_dict[ConfigKeys.VERSION] = pkg_resources.require('gridnotify')[0].version
    config_dict[ConfigKeys.REDIS] = Redis(config_dict[ConfigKeys.REDIS_HOST])
    config_dict[ConfigKeys.LOGGER] = create_logger(config_dict)

    if ConfigKeys.LOG_FORMAT not in config_dict:
        log_format = ConfigKeys.DEFAULT_LOG_FORMAT
        config_dict[ConfigKeys.LOG_FORMAT] = log_format

    if ConfigKeys.LOG_LEVEL not in config_dict:
        config_dict[ConfigKeys.LOG_LEVEL] = ConfigKeys.DEFAULT_LOG_LEVEL

    root_path = os.path.dirname(config_path)
    gn_env = GNEnvironment(root_path, config_dict)
    gn_env.config.get(ConfigKeys.LOGGER).info('read config and created environment')
    gn_env.config.get(ConfigKeys.LOGGER).debug(str(config_dict))
    return gn_env


env = create_env()
