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
from nose_parameterized import parameterized
from activitystreams import parse as as_parser
from fakeredis import FakeRedis
from uuid import uuid4 as uuid

from dino.config import ConfigKeys
from dino.config import RedisKeys
from dino import environ
environ.env.config.set(ConfigKeys.TESTING, True)

import dino.api
from dino.endpoint import sockets


class SocketsHasApiMethodsTest(unittest.TestCase):
    api_methods = [name for name in dino.api.__dict__.keys() if name.startswith('on_')]

    def setUp(self):
        self.socket_methods = set(
                [key for key in sockets.__dict__.keys() if key.startswith('on_')]
        )

    @parameterized.expand(api_methods)
    def test_api_method_is_in_endpoint(self, method):
        self.assertIn(method, self.socket_methods)


class SocketsHasOnlyApiMethodsTest(unittest.TestCase):
    socket_methods = set(
            [key for key in sockets.__dict__.keys() if key.startswith('on_')]
    )

    def setUp(self):
        self.api_methods = [name for name in dino.api.__dict__.keys() if name.startswith('on_')]

    @parameterized.expand(socket_methods)
    def test_endpoint_method_is_in_api(self, method):
        self.assertIn(method, self.api_methods)


class MockManager(object):
    def __init__(self):
        self.rooms = {
            '/chat': {
                '8888': ['1111']
            }
        }


class MockServer(object):
    def __init__(self):
        self.manager = MockManager()

    def leave_room(self, *args):
        pass


class FakeDb(object):
    def get_user_for_private_room(self, *args):
        return '1234'

    def rooms_for_user(self, *args):
        return {'8888': 'some name'}

    def get_sid_for_user(self, user_id: str):
        return str(uuid())


class FakeLogger(object):
    def error(*args, **kwargs):
        pass

    def info(*args, **kwargs):
        pass


class SocketsTest(unittest.TestCase):
    @staticmethod
    def out_of_scope_emit(*args, **kwargs):
        pass

    def setUp(self):
        environ.env.db = FakeDb()
        environ.env.redis = FakeRedis()
        environ.env.redis.hset(RedisKeys.sid_for_user_id(), '1234', '1111')
        environ.env.out_of_scope_emit = self.out_of_scope_emit
        environ.env.logger = FakeLogger()

    def test_handle_activity_kick(self):
        activity = {
            'actor': {
                'id': '1234',
                'summary': 'good-guy'
            },
            'verb': 'kick',
            'object': {
                'id': '4321',
                'summary': 'bad-guy'
            },
            'target': {
                'url': '/chat'
            }
        }
        sockets.socketio.server = MockServer()
        sockets.handle_server_activity(as_parser(activity))

    def test_handle_activity_ban(self):
        activity = {
            'actor': {
                'id': '1234',
                'summary': 'good-guy'
            },
            'verb': 'ban',
            'object': {
                'id': '4321',
                'summary': 'bad-guy'
            },
            'target': {
                'url': '/chat'
            }
        }
        sockets.socketio.server = MockServer()
        sockets.handle_server_activity(as_parser(activity))
