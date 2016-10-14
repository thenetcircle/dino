#!/usr/bin/env python

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
os.environ['ENVIRONMENT'] = 'test'

from dino import environ
from dino import api
from dino import rkeys
from test.utils import BaseTest

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class ApiBanTest(BaseTest):
    def test_kick(self):
        self.create_and_join_room()
        self.set_owner()
        self.assertEqual(200, api.on_ban(self.activity_for_ban())[0])

    def create_room(self, room_id: str=None, room_name: str=None):
        if room_id is None:
            room_id = ApiBanTest.ROOM_ID
        if room_name is None:
            room_name = ApiBanTest.ROOM_NAME

        environ.env.storage.redis.hset(rkeys.rooms(), room_id, room_name)

    def activity_for_ban(self):
        return {
            'actor': {
                'id': ApiBanTest.USER_ID,
                'content': ApiBanTest.USER_NAME
            },
            'verb': 'ban',
            'object': {
                'id': ApiBanTest.OTHER_USER_ID,
                'content': ApiBanTest.OTHER_USER_NAME,
                'summary': '30m'
            },
            'target': {
                'id': ApiBanTest.ROOM_ID,
                'displayName': ApiBanTest.ROOM_NAME
            }
        }
