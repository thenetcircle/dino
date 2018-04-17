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

from dino.db.manager.rooms import RoomManager
from dino.exceptions import NoSuchChannelException
from dino.exceptions import NoSuchRoomException

from uuid import uuid4 as uuid
from test.db import BaseDatabaseTest

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class RoomManagerTest(BaseDatabaseTest):
    _act = None

    @staticmethod
    def _publish(activity: dict, external: bool=False) -> None:
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
        self.assertEqual(BaseDatabaseTest.ROOM_NAME, rooms[0]['name'])

    def test_create_room(self):
        self._create_channel()
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
        value = self.manager.create_room(
                BaseDatabaseTest.ROOM_NAME, BaseDatabaseTest.ROOM_ID,
                BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)
        self.assertIsNone(value)
        self.assertTrue(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

    def test_create_room_empty_room_name(self):
        self._create_channel()
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
        value = self.manager.create_room(
                '', BaseDatabaseTest.ROOM_ID,
                BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)
        self.assertIsNotNone(value)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

    def test_create_room_empty_room_id(self):
        self._create_channel()
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
        value = self.manager.create_room(
                BaseDatabaseTest.ROOM_NAME, '',
                BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)
        self.assertIsNotNone(value)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

    def test_create_room_empty_channel_id(self):
        self._create_channel()
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
        value = self.manager.create_room(
                BaseDatabaseTest.ROOM_NAME, BaseDatabaseTest.ROOM_ID,
                '', BaseDatabaseTest.USER_ID)
        self.assertIsNotNone(value)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

    def test_create_room_empty_user_id(self):
        self._create_channel()
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
        value = self.manager.create_room(
                BaseDatabaseTest.ROOM_NAME, BaseDatabaseTest.ROOM_ID,
                BaseDatabaseTest.CHANNEL_ID, '')
        self.assertIsNotNone(value)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

    def test_remove_room(self):
        self._create_channel()
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
        self.manager.create_room(
                BaseDatabaseTest.ROOM_NAME, BaseDatabaseTest.ROOM_ID,
                BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)
        self.assertTrue(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
        self.manager.remove_room(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

    def test_remove_room_twice(self):
        self._create_channel()
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
        self.manager.create_room(
                BaseDatabaseTest.ROOM_NAME, BaseDatabaseTest.ROOM_ID,
                BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)
        self.assertTrue(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

        self.manager.remove_room(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID)
        self.assertRaises(
                NoSuchRoomException, self.manager.remove_room, BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

    def test_remove_room_before_create_room(self):
        self._create_channel()
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

        self.assertRaises(
                NoSuchRoomException, self.manager.remove_room, BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

    def test_remove_room_before_create_channel(self):
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))
        self.assertRaises(
                NoSuchRoomException, self.manager.remove_room, BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID)
        self.assertFalse(self.db.room_exists(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID))

    def test_remove_room_empty_room_id(self):
        self._create_channel()
        self.assertRaises(NoSuchRoomException, self.manager.remove_room, BaseDatabaseTest.CHANNEL_ID, '')

    def test_rename_room(self):
        self._create_channel()
        self._create_room()
        self.assertEqual(BaseDatabaseTest.ROOM_NAME, self.db.get_room_name(BaseDatabaseTest.ROOM_ID))
        value = self.manager.rename(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID, 'new-name')
        self.assertIsNone(value)
        self.assertEqual('new-name', self.db.get_room_name(BaseDatabaseTest.ROOM_ID))

    def test_rename_room_already_exists(self):
        self._create_channel()
        self._create_room()
        self.assertEqual(BaseDatabaseTest.ROOM_NAME, self.db.get_room_name(BaseDatabaseTest.ROOM_ID))
        value = self.manager.rename(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.ROOM_NAME)
        self.assertIsNotNone(value)
        self.assertEqual(BaseDatabaseTest.ROOM_NAME, self.db.get_room_name(BaseDatabaseTest.ROOM_ID))

    def test_rename_room_no_such_room(self):
        self._create_channel()
        self._create_room()
        value = self.manager.rename(BaseDatabaseTest.CHANNEL_ID, str(uuid()), BaseDatabaseTest.ROOM_NAME)
        self.assertIsNotNone(value)
        self.assertEqual(BaseDatabaseTest.ROOM_NAME, self.db.get_room_name(BaseDatabaseTest.ROOM_ID))

    def test_rename_room_blank_name(self):
        self._create_channel()
        self._create_room()
        self.assertEqual(BaseDatabaseTest.ROOM_NAME, self.db.get_room_name(BaseDatabaseTest.ROOM_ID))
        value = self.manager.rename(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.ROOM_NAME)
        self.assertIsNotNone(value)
        self.assertEqual(BaseDatabaseTest.ROOM_NAME, self.db.get_room_name(BaseDatabaseTest.ROOM_ID))

    def test_name_for_uuid(self):
        self._create_channel()
        self._create_room()
        self.assertEqual(BaseDatabaseTest.ROOM_NAME, self.manager.name_for_uuid(BaseDatabaseTest.ROOM_ID))

    def test_name_for_uuid_no_such_room(self):
        self._create_channel()
        self._create_room()
        value = self.manager.name_for_uuid(str(uuid()))
        self.assertIsNone(value)

    def test_get_owners_before_create(self):
        self._create_channel()
        value = self.manager.get_owners(BaseDatabaseTest.ROOM_ID)
        self.assertTrue(type(value) == str)

    def test_get_owners(self):
        self._create_channel()
        self._create_room()
        owners = self.manager.get_owners(BaseDatabaseTest.ROOM_ID)
        self.assertTrue(type(owners) == list)
        self.assertEqual(1, len(owners))
        self.assertEqual(BaseDatabaseTest.USER_ID, owners[0]['uuid'])
        self.assertEqual(BaseDatabaseTest.USER_NAME, owners[0]['name'])

    def test_get_moderators_before_create(self):
        self._create_channel()
        value = self.manager.get_moderators(BaseDatabaseTest.ROOM_ID)
        self.assertTrue(type(value) == str)

    def test_get_moderators(self):
        self._create_channel()
        self._create_room()
        self.db.set_moderator(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID)
        moderators = self.manager.get_moderators(BaseDatabaseTest.ROOM_ID)
        self.assertTrue(type(moderators) == list)
        self.assertEqual(1, len(moderators))
        self.assertEqual(BaseDatabaseTest.USER_ID, moderators[0]['uuid'])
        self.assertEqual(BaseDatabaseTest.USER_NAME, moderators[0]['name'])
