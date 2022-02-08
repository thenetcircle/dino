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

import unittest
import os
import tempfile

from dino.environ import create_env
from dino.config import ConfigKeys
from dino import environ
from dino.exceptions import AclValueNotFoundException


class FakeDb(object):
    def type_of_rooms_in_channel(self, _):
        return "temporary"

    def get_acl_validation_value(self, *args):
        raise AclValueNotFoundException('asdf', 'asdf')


class TestEnvironment(unittest.TestCase):
    def test_env(self):
        if 'DINO_ENVIRONMENT' in os.environ:
            del os.environ['DINO_ENVIRONMENT']
        env = create_env(['../dino.yaml'])
        self.assertEqual(0, len(env.config))

    def test_create_with_environment(self):
        os.environ['DINO_ACL'] = '../acl.yaml'
        os.environ['DINO_ENVIRONMENT'] = 'integration'
        env = create_env(['../dino.yaml'])
        self.assertTrue(ConfigKeys.LOG_FORMAT in env.config.keys())
        self.assertTrue(ConfigKeys.LOG_LEVEL in env.config.keys())
        self.assertTrue(ConfigKeys.SESSION in env.config.keys())

    def test_init_cache_service(self):
        os.environ['DINO_ACL'] = '../acl.yaml'
        os.environ['DINO_ENVIRONMENT'] = 'integration'
        env = create_env(['../dino.yaml'])
        env.db = FakeDb()
        environ.init_cache_service(env)

    def test_init_auth_service(self):
        os.environ['DINO_ACL'] = '../acl.yaml'
        os.environ['DINO_ENVIRONMENT'] = 'integration'
        env = create_env(['../dino.yaml'])
        env.db = FakeDb()
        environ.init_auth_service(env)

    def test_init_storage_engine(self):
        os.environ['DINO_ACL'] = '../acl.yaml'
        os.environ['DINO_ENVIRONMENT'] = 'integration'
        env = create_env(['../dino.yaml'])
        env.db = FakeDb()
        environ.init_storage_engine(env)

    def test_init_database(self):
        os.environ['DINO_ACL'] = '../acl.yaml'
        os.environ['DINO_ENVIRONMENT'] = 'integration'
        env = create_env(['../dino.yaml'])
        env.db = FakeDb()
        environ.init_database(env)

    def test_init_acl_validators(self):
        os.environ['DINO_ACL'] = '../acl.yaml'
        os.environ['DINO_ENVIRONMENT'] = 'integration'
        env = create_env(['../dino.yaml'])
        env.db = FakeDb()
        environ.init_acl_validators(env)

    def test_create_non_existing_config_file(self):
        os.environ['DINO_ACL'] = '../acl.yaml'
        os.environ['DINO_ENVIRONMENT'] = 'test'
        self.assertRaises(RuntimeError, create_env, ['foo.yaml', 'bar.json'])

    def test_create_existing_yaml_file(self):
        f = tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False)
        f.write('test:\n    log_level:\n        "DEBUG"\n    storage:\n '
                '       type: "mock"\n    queue:\n        type: "mock"')
        f.close()


        try:
            os.environ['DINO_ACL'] = '../acl.yaml'
            os.environ['DINO_ENVIRONMENT'] = 'test'
            create_env([f.name])
        finally:
            os.remove(f.name)

    def test_log_level_has_default_value(self):
        f = tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False)
        f.write('test:\n    storage:\n        type: "mock"\n    queue:\n        type: "mock"')
        f.close()

        try:
            os.environ['DINO_ACL'] = '../acl.yaml'
            os.environ['DINO_ENVIRONMENT'] = 'test'
            env = create_env([f.name])
            self.assertIsNotNone(env.config.get(ConfigKeys.LOG_LEVEL))
        finally:
            os.remove(f.name)

    def test_env_not_found_in_config(self):
        f = tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False)
        f.write('test:\n    log_level:\n        "DEBUG"\n    storage:\n        type: "mock"')
        f.close()

        try:
            os.environ['DINO_ACL'] = '../acl.yaml'
            os.environ['DINO_ENVIRONMENT'] = 'should_not_find'
            self.assertRaises(RuntimeError, create_env, [f.name])
        finally:
            os.remove(f.name)

    def test_create_unknown_ext(self):
        f = tempfile.NamedTemporaryFile(mode='w+', suffix='.foo', delete=False)
        f.write('blablabla"')
        f.close()

        try:
            os.environ['DINO_ACL'] = '../acl.yaml'
            os.environ['DINO_ENVIRONMENT'] = 'test'
            self.assertRaises(RuntimeError, create_env, [f.name])
        finally:
            os.remove(f.name)

    def test_create_existing_json_file(self):
        f = tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False)
        f.write('{"test": {"queue": {"type": "mock"}, "storage": {"type": "mock"}, "log_level": "DEBUG"}}')
        f.close()

        try:
            os.environ['DINO_ACL'] = '../acl.yaml'
            os.environ['DINO_ENVIRONMENT'] = 'test'
            create_env([f.name])
        finally:
            os.remove(f.name)
