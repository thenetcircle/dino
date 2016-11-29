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

from datetime import datetime, timedelta

from dino.db.manager.rooms import RoomManager
from dino.exceptions import NoSuchChannelException
from dino.exceptions import NoSuchRoomException
from dino.exceptions import UnknownBanTypeException
from dino.exceptions import NoSuchUserException
from dino.exceptions import EmptyUserNameException
from dino.exceptions import EmptyUserIdException
from dino.utils import b64d

from test.db import BaseDatabaseTest

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class RoomManagerTest(BaseDatabaseTest):
    _act = None

    @staticmethod
    def _publish(activity: dict) -> None:
        RoomManagerTest._act = activity

    def setUp(self):
        self.set_up_env('redis')
        self.env.publish = RoomManagerTest._publish
        self._act = None
        self.env.db = self.db
        self.manager = RoomManager(self.env)

    def tearDown(self):
        self.db.redis.flushall()
        self.env.cache._flushall()

    def test_get_rooms_before_channel_creation(self):
        rooms = self.manager.get_rooms(BaseDatabaseTest.CHANNEL_ID)
        self.assertEqual(0, len(rooms))

    def test_get_rooms_before_room_creation(self):
        self._create_channel()
        rooms = self.manager.get_rooms(BaseDatabaseTest.CHANNEL_ID)
        self.assertEqual(0, len(rooms))

    def test_get_rooms_after_create(self):
        self._create_channel()
        self._create_room()
        rooms = self.manager.get_rooms(BaseDatabaseTest.CHANNEL_ID)
        self.assertEqual(1, len(rooms))
        self.assertEqual(BaseDatabaseTest.ROOM_ID, rooms[0]['uuid'])
        self.assertEqual(BaseDatabaseTest.ROOM_NAME, b64d(rooms[0]['name']))

    def test_create_room(self):
        self._create_channel()
        self.db.create_user(BaseDatabaseTest.USER_ID, BaseDatabaseTest.USER_NAME)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
        value = self.manager.create_room(
                BaseDatabaseTest.ROOM_NAME, BaseDatabaseTest.ROOM_ID,
                BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)
        self.assertIsNone(value)
        self.assertTrue(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

    def test_create_room_empty_room_name(self):
        self._create_channel()
        self.db.create_user(BaseDatabaseTest.USER_ID, BaseDatabaseTest.USER_NAME)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
        value = self.manager.create_room(
                '', BaseDatabaseTest.ROOM_ID,
                BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)
        self.assertIsNotNone(value)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

    def test_create_room_empty_room_id(self):
        self._create_channel()
        self.db.create_user(BaseDatabaseTest.USER_ID, BaseDatabaseTest.USER_NAME)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
        value = self.manager.create_room(
                BaseDatabaseTest.ROOM_NAME, '',
                BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)
        self.assertIsNotNone(value)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

    def test_create_room_empty_channel_id(self):
        self._create_channel()
        self.db.create_user(BaseDatabaseTest.USER_ID, BaseDatabaseTest.USER_NAME)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
        value = self.manager.create_room(
                BaseDatabaseTest.ROOM_NAME, BaseDatabaseTest.ROOM_ID,
                '', BaseDatabaseTest.USER_ID)
        self.assertIsNotNone(value)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

    def test_create_room_empty_user_id(self):
        self._create_channel()
        self.db.create_user(BaseDatabaseTest.USER_ID, BaseDatabaseTest.USER_NAME)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
        value = self.manager.create_room(
                BaseDatabaseTest.ROOM_NAME, BaseDatabaseTest.ROOM_ID,
                BaseDatabaseTest.CHANNEL_ID, '')
        self.assertIsNotNone(value)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
