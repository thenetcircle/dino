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

import time
from unittest import TestCase
from uuid import uuid4 as uuid
from activitystreams import parse

import os
os.environ['ENVIRONMENT'] = 'test'

from dino import environ
from dino import api
from dino import rkeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class ApiKickTest(TestCase):
    OTHER_USER_ID = '8888'
    OTHER_USER_NAME = 'pleb'
    
    USER_ID = '5000'
    USER_NAME = 'TheBoss'
    
    ROOM_ID = str(uuid())
    ROOM_NAME = 'Best Room'

    def test_kick(self):
        api._kick_user(parse(self.activity_for_kick()))
        time.sleep(1)

    def create_room(self, room_id: str=None, room_name: str=None):
        if room_id is None:
            room_id = ApiKickTest.ROOM_ID
        if room_name is None:
            room_name = ApiKickTest.ROOM_NAME

        environ.env.storage.redis.hset(rkeys.rooms(), room_id, room_name)

    def activity_for_join(self):
        return {
            'actor': {
                'id': ApiKickTest.USER_ID
            },
            'verb': 'join',
            'target': {
                'id': ApiKickTest.ROOM_ID
            }
        }

    def activity_for_kick(self):
        return {
            'actor': {
                'id': ApiKickTest.USER_ID,
                'content': ApiKickTest.USER_NAME
            },
            'verb': 'join',
            'object': {
                'id': ApiKickTest.OTHER_USER_ID,
                'content': ApiKickTest.OTHER_USER_NAME
            },
            'target': {
                'id': ApiKickTest.ROOM_ID,
                'displayName': ApiKickTest.ROOM_NAME
            }
        }
