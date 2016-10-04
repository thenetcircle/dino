import unittest
import os
from uuid import uuid4 as uuid
import tempfile

from dino.env import create_env
from dino.env import ConfigKeys
from dino.env import error


class TestEnvironment(unittest.TestCase):
    def test_env(self):
        del os.environ['ENVIRONMENT']
        env = create_env()
        self.assertEqual(dict(), env.config)

    def test_create_with_environment(self):
        os.environ['ENVIRONMENT'] = 'dev'
        env = create_env()
        self.assertTrue(ConfigKeys.LOG_FORMAT in env.config.keys())
        self.assertTrue(ConfigKeys.LOG_LEVEL in env.config.keys())
        self.assertTrue(ConfigKeys.LOGGER in env.config.keys())
        self.assertTrue(ConfigKeys.REDIS in env.config.keys())
        self.assertTrue(ConfigKeys.REDIS_HOST in env.config.keys())
        self.assertTrue(ConfigKeys.SESSION in env.config.keys())
        self.assertTrue(ConfigKeys.VERSION in env.config.keys())

    def test_error(self):
        error('test')

    def test_create_non_existing_config_file(self):
        os.environ['ENVIRONMENT'] = 'test'
        self.assertRaises(RuntimeError, create_env, ['foo.yaml', 'bar.json'])

    def test_create_existing_yaml_file(self):
        f = tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False)
        f.write('test:\n    redis_host: "mock"\n    log_level: "DEBUG"')
        f.close()

        try:
            os.environ['ENVIRONMENT'] = 'test'
            create_env([f.name])
        finally:
            os.remove(f.name)

    def test_log_level_has_default_value(self):
        f = tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False)
        f.write('test:\n    redis_host: "mock"')
        f.close()

        try:
            os.environ['ENVIRONMENT'] = 'test'
            env = create_env([f.name])
            self.assertIsNotNone(env.config.get(ConfigKeys.LOG_LEVEL))
        finally:
            os.remove(f.name)

    def test_env_not_found_in_config(self):
        f = tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False)
        f.write('test:\n    redis_host: "mock"\n    log_level: "DEBUG"')
        f.close()

        try:
            os.environ['ENVIRONMENT'] = 'should_not_find'
            self.assertRaises(RuntimeError, create_env, [f.name])
        finally:
            os.remove(f.name)

    def test_create_unknown_ext(self):
        f = tempfile.NamedTemporaryFile(mode='w+', suffix='.foo', delete=False)
        f.write('blablabla"')
        f.close()

        try:
            os.environ['ENVIRONMENT'] = 'test'
            self.assertRaises(RuntimeError, create_env, [f.name])
        finally:
            os.remove(f.name)

    def test_create_existing_json_file(self):
        f = tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False)
        f.write('{"test": {"redis_host": "mock", "log_level": "DEBUG"}}')
        f.close()

        try:
            os.environ['ENVIRONMENT'] = 'test'
            create_env([f.name])
        finally:
            os.remove(f.name)
