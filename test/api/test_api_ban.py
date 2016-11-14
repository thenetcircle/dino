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

import os
from uuid import uuid4 as uuid
os.environ['ENVIRONMENT'] = 'test'

from activitystreams import parse as as_parser
from test.utils import BaseTest

from dino import environ
from dino import api
from dino.config import RedisKeys
from dino.config import ErrorCodes

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class ApiBanTest(BaseTest):
    def test_ban_no_such_user(self):
        self.create_and_join_room()
        self.set_owner()

        json = self.activity_for_ban()
        json['object']['id'] = str(uuid())
        response_code, _ = api.on_ban(json, as_parser(json))

        self.assertEqual(ErrorCodes.NO_SUCH_USER, response_code)

    def test_ban_user_exists(self):
        self.create_and_join_room()
        self.set_owner()
        self.create_user(BaseTest.OTHER_USER_ID, BaseTest.OTHER_USER_NAME)

        json = self.activity_for_ban()
        json['object']['id'] = str(self.env.db.redis.hget(
                RedisKeys.private_rooms(), ApiBanTest.OTHER_USER_ID), 'utf-8')

        response_code, _ = api.on_ban(json, as_parser(json))
        self.assertEqual(ErrorCodes.OK, response_code)

    def create_room(self, room_id: str=None, room_name: str=None):
        if room_id is None:
            room_id = ApiBanTest.ROOM_ID
        if room_name is None:
            room_name = ApiBanTest.ROOM_NAME

        environ.env.storage.redis.hset(RedisKeys.rooms(BaseTest.CHANNEL_ID), room_id, room_name)

    def activity_for_ban(self):
        return {
            'actor': {
                'id': ApiBanTest.USER_ID,
                'content': ApiBanTest.USER_NAME
            },
            'verb': 'ban',
            'object': {
                'content': ApiBanTest.OTHER_USER_NAME,
                'objectType': 'user',
                'summary': '30m',
                'url': BaseTest.CHANNEL_ID
            },
            'target': {
                'id': ApiBanTest.ROOM_ID,
                'displayName': ApiBanTest.ROOM_NAME
            }
        }
