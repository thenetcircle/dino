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

from unittest import TestCase

from dino import environ
from dino.db.manager.users import UserManager

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class FakeDb(object):
    _users_in_room = dict()

    def users_in_room(self, room_id):
        if room_id not in FakeDb._users_in_room:
            return dict()
        return FakeDb._users_in_room[room_id]


class UserManagerTest(TestCase):
    ROOM_ID = '8888'
    ROOM_NAME = 'cool guys'

    CHANNEL_ID = '1234'
    CHANNEL_NAME = 'Shanghai'

    OTHER_CHANNEL_ID = '4321'
    OTHER_CHANNEL_NAME = 'Beijing'

    USER_ID = '5555'
    USER_NAME = 'Batman'

    def setUp(self):
        environ.env.db = FakeDb()
        self.manager = UserManager(environ.env)
        FakeDb._users_in_room = dict()

    def test_get_users_for_room(self):
        users = self.manager.get_users_for_room(UserManagerTest.ROOM_ID)
        self.assertEqual(0, len(users))

    def test_get_users_for_room_after_join(self):
        FakeDb._users_in_room[UserManagerTest.ROOM_ID] = {UserManagerTest.USER_ID: UserManagerTest.USER_NAME}
        users = self.manager.get_users_for_room(UserManagerTest.ROOM_ID)
        self.assertEqual(1, len(users))
        self.assertEqual(UserManagerTest.USER_ID, users[0]['uuid'])
        self.assertEqual(UserManagerTest.USER_NAME, users[0]['name'])
