import unittest
import os
import tempfile

from dino.environ import create_env
from dino.config import ConfigKeys


class TestEnvironment(unittest.TestCase):
    def test_env(self):
        if 'ENVIRONMENT' in os.environ:
            del os.environ['ENVIRONMENT']
        env = create_env()
        self.assertEqual(0, len(env.config))

    def test_create_with_environment(self):
        os.environ['ENVIRONMENT'] = 'dev'
        env = create_env()
        self.assertTrue(ConfigKeys.LOG_FORMAT in env.config.keys())
        self.assertTrue(ConfigKeys.LOG_LEVEL in env.config.keys())
        self.assertTrue(ConfigKeys.LOGGER in env.config.keys())
        self.assertTrue(ConfigKeys.REDIS in env.config.keys())
        self.assertTrue(ConfigKeys.SESSION in env.config.keys())

    def test_create_non_existing_config_file(self):
        os.environ['ENVIRONMENT'] = 'test'
        self.assertRaises(RuntimeError, create_env, ['foo.yaml', 'bar.json'])

    def test_create_existing_yaml_file(self):
        f = tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False)
        f.write('test:\n    log_level:\n        "DEBUG"\n    storage:\n '
                '       type: "mock"\n    queue:\n        type: "mock"')
        f.close()

        try:
            os.environ['ENVIRONMENT'] = 'test'
            create_env([f.name])
        finally:
            os.remove(f.name)

    def test_log_level_has_default_value(self):
        f = tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False)
        f.write('test:\n    storage:\n        type: "mock"\n    queue:\n        type: "mock"')
        f.close()

        try:
            os.environ['ENVIRONMENT'] = 'test'
            env = create_env([f.name])
            self.assertIsNotNone(env.config.get(ConfigKeys.LOG_LEVEL))
        finally:
            os.remove(f.name)

    def test_env_not_found_in_config(self):
        f = tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False)
        f.write('test:\n    log_level:\n        "DEBUG"\n    storage:\n        type: "mock"')
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
        f.write('{"test": {"queue": {"type": "mock"}, "storage": {"type": "mock"}, "log_level": "DEBUG"}}')
        f.close()

        try:
            os.environ['ENVIRONMENT'] = 'test'
            create_env([f.name])
        finally:
            os.remove(f.name)
