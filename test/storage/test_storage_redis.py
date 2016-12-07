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

from unittest import TestCase
from uuid import uuid4 as uuid
from activitystreams import parse as as_parser
from datetime import datetime

from dino import environ
from dino.utils import b64e
from dino.config import ConfigKeys
from dino.storage.redis import StorageRedis

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class RedisStorageTest(TestCase):
    USER_ID = '1234'
    ROOM_ID = '4321'
    USER_NAME = 'Batman'
    MESSAGE = str(uuid())
    MESSAGE_ID = str(uuid())

    def setUp(self):
        self.db = StorageRedis('mock')
        self.db.redis.flushall()
        environ.env.session = {
            'user_id': RedisStorageTest.USER_ID,
            'user_name': RedisStorageTest.USER_NAME
        }

    def test_get_empty_history(self):
        history = self.db.get_history(RedisStorageTest.ROOM_ID)
        self.assertEqual(0, len(history))

    def test_store_message(self):
        self.db.store_message(as_parser(self.act()))
        history = self.db.get_history(RedisStorageTest.ROOM_ID)
        self.assertEqual(1, len(history))
        msg_id, published, user_id, user_name, msg = history[0]
        self.assertIsNotNone(msg_id)
        self.assertEqual(RedisStorageTest.USER_ID, user_id)
        self.assertEqual(RedisStorageTest.USER_NAME, user_name)
        self.assertEqual(RedisStorageTest.MESSAGE, msg)

    def test_delete_message(self):
        self.db.store_message(as_parser(self.act()))
        history = self.db.get_history(RedisStorageTest.ROOM_ID)
        self.assertEqual(1, len(history))
        self.db.delete_message(RedisStorageTest.ROOM_ID, RedisStorageTest.MESSAGE_ID)
        history = self.db.get_history(RedisStorageTest.ROOM_ID)
        self.assertEqual(0, len(history))

    def act(self):
        return {
            'actor': {
                'id': RedisStorageTest.USER_ID,
                'summary': RedisStorageTest.USER_NAME
            },
            'verb': 'send',
            'object': {
                'content': b64e(RedisStorageTest.MESSAGE)
            },
            'target': {
                'id': RedisStorageTest.ROOM_ID
            },
            'id': RedisStorageTest.MESSAGE_ID,
            'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
        }
