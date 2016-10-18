#!/usr/bin/env python

# Copyright 2013-2016 DataStax, Inc.
#
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

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

from activitystreams import parse
from uuid import uuid4 as uuid
from datetime import datetime
import time

from dino.environ import ConfigDict

from dino.config import ConfigKeys
from dino.cache.miss import CacheAllMiss
from dino.cache.redis import CacheRedis
from dino.db.postgres.models import Channels
from dino.db.postgres.models import UserStatus
from dino.db.postgres.models import Rooms
from dino.db.postgres.models import Users
from dino.db.postgres.postgres import DatabasePostgres

from dino.exceptions import ChannelExistsException
from dino.exceptions import NoSuchChannelException
from dino.exceptions import RoomExistsException
from dino.exceptions import NoSuchUserException

from test.utils import BaseTest


class BaseDatabaseTest(BaseTest):
    class FakeEnv(object):
        def __init__(self):
            self.config = ConfigDict()
            self.cache = CacheRedis('mock')

    MESSAGE_ID = str(uuid())

    def set_up_env(self, db):
        self.env = BaseDatabaseTest.FakeEnv()
        self.env.config.set(ConfigKeys.TESTING, False)
        self.env.config.set(ConfigKeys.HOST, 'localhost', domain=ConfigKeys.DATABASE)
        self.env.config.set(ConfigKeys.PORT, 5432, domain=ConfigKeys.DATABASE)
        self.env.config.set(ConfigKeys.DB, 'dinotest', domain=ConfigKeys.DATABASE)
        self.env.config.set(ConfigKeys.USER, 'dinouser', domain=ConfigKeys.DATABASE)
        self.env.config.set(ConfigKeys.PASSWORD, 'dinopass', domain=ConfigKeys.DATABASE)

        if db == 'postgres':
            self.db = DatabasePostgres(self.env)
        elif db == 'redis':
            from dino.db.redis import DatabaseRedis
            self.db = DatabaseRedis('localhost:6379')
        else:
            raise ValueError('unknown type %s' % db)

    def act_message(self):
        data = self.activity_for_message()
        data['id'] = BaseDatabaseTest.MESSAGE_ID
        data['target']['objectType'] = 'group'
        data['published'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%SZ')
        return parse(data)

    def act_create(self):
        data = self.activity_for_create()
        data['target']['id'] = BaseTest.ROOM_ID
        data['published'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%SZ')
        return parse(data)

    def _test_room_exists(self):
        self.assertFalse(self._room_exists())

    def _test_create_room_no_channel(self):
        self.assertRaises(NoSuchChannelException, self._create_room)

    def _test_create_channel(self):
        self._create_channel()

    def _test_create_existing_channel(self):
        self._create_channel()
        self.assertRaises(ChannelExistsException, self._create_channel)

    def _test_create_room(self):
        self.assertFalse(self._room_exists())
        self._create_channel()
        self._create_room()
        self.assertTrue(self._room_exists())

    def _test_create_existing_room(self):
        self._create_channel()
        self._create_room()
        self.assertRaises(RoomExistsException, self._create_room)

    def _test_channel_exists_after_create(self):
        self._create_channel()
        self.assertTrue(self._channel_exists())

    def _test_channel_exists_before_create(self):
        self.assertFalse(self._channel_exists())

    def _test_room_name_exists_before_create(self):
        self.assertFalse(self._room_name_exists())

    def _test_room_name_exists_after_create(self):
        self._create_channel()
        self._create_room()
        self.assertTrue(self._room_name_exists())

    def _test_get_channels_before_create(self):
        self.assertEqual(0, len(self._get_channels()))

    def _test_get_channels_after_create(self):
        self._create_channel()
        channels = self._get_channels()
        self.assertEqual(1, len(channels))
        self.assertTrue(BaseTest.CHANNEL_ID in channels.keys())
        self.assertTrue(BaseTest.CHANNEL_NAME in channels.values())

    def _test_rooms_for_channel_before_create_channel(self):
        self.assertEqual(0, len(self._rooms_for_channel()))

    def _test_rooms_for_channel_after_create_channel_before_create_room(self):
        self._create_channel()
        self.assertEqual(0, len(self._rooms_for_channel()))

    def _test_rooms_for_channel_after_create_channel_after_create_room(self):
        self._create_channel()
        self._create_room()
        rooms = self._rooms_for_channel()
        self.assertEqual(1, len(rooms))
        self.assertTrue(BaseTest.ROOM_ID in rooms.keys())
        self.assertTrue(BaseTest.ROOM_NAME in rooms.values())

    def _test_rooms_for_user_before_joining(self):
        self._create_channel()
        self._create_room()
        self.assertEqual(0, len(self.rooms_for_user()))

    def _test_rooms_for_user_after_joining(self):
        self._create_channel()
        self._create_room()
        self._join()
        rooms = self.rooms_for_user()
        self.assertEqual(1, len(rooms))
        self.assertTrue(BaseTest.ROOM_ID in rooms.keys())
        self.assertTrue(BaseTest.ROOM_NAME in rooms.values())

    def _test_remove_current_rooms_for_user_before_joining(self):
        self.db.remove_current_rooms_for_user(BaseTest.USER_ID)
        self.assertEqual(0, len(self._rooms_for_user()))

    def _test_remove_current_rooms_for_user_after_joining(self):
        self._create_channel()
        self._create_room()
        self._join()

        rooms = self._rooms_for_user()
        self.assertEqual(1, len(rooms))
        self.assertTrue(BaseTest.ROOM_ID in rooms.keys())
        self.assertTrue(BaseTest.ROOM_NAME in rooms.values())

        self.db.remove_current_rooms_for_user(BaseTest.USER_ID)
        self.assertEqual(0, len(self._rooms_for_user()))

    def _test_get_user_status_before_set(self, status):
        self.assertEqual(status, self._user_status())

    def _test_set_user_offline(self, status):
        self._set_offline()
        self.assertEqual(status, self._user_status())

    def _test_set_user_online(self, status):
        self._set_online()
        self.assertEqual(status, self._user_status())

    def _test_set_user_invisible(self, status):
        self._set_invisible()
        self.assertEqual(status, self._user_status())

    def _test_is_admin_before_create(self):
        self.assertFalse(self._is_admin())

    def _test_is_admin_after_create(self):
        self._create_channel()
        self.assertFalse(self._is_admin())

    def _test_is_admin_after_create_set_admin(self):
        self._create_channel()
        self._set_admin()
        self.assertTrue(self._is_admin())

    def _test_is_moderator_before_create(self):
        self.assertFalse(self._is_moderator())

    def _test_is_moderator_after_create(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self._is_moderator())

    def _test_is_moderator_after_create_set_moderator(self):
        self._create_channel()
        self._create_room()
        self._set_moderator()
        self.assertFalse(self._is_moderator())

    def _set_moderator(self):
        self.db.set_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID)

    def _set_admin(self):
        self.db.set_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID)

    def _is_moderator(self):
        return self.db.is_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID)

    def _is_admin(self):
        return self.db.is_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID)

    def _user_status(self):
        return self.db.get_user_status(BaseTest.USER_ID)

    def _set_offline(self):
        self.db.set_user_offline(BaseTest.USER_ID)

    def _set_online(self):
        self.db.set_user_online(BaseTest.USER_ID)

    def _set_invisible(self):
        self.db.set_user_invisible(BaseTest.USER_ID)

    def _rooms_for_user(self):
        return self.db.rooms_for_user(BaseTest.USER_ID)

    def _get_user_name_for(self):
        return self.db.get_user_name_for(BaseTest.USER_ID)

    def _join(self):
        self.db.join_room(BaseTest.USER_ID, BaseTest.USER_NAME, BaseTest.ROOM_ID, BaseTest.ROOM_NAME)

    def rooms_for_user(self):
        return self.db.rooms_for_user(BaseTest.USER_ID)

    def _rooms_for_channel(self):
        return self.db.rooms_for_channel(BaseTest.CHANNEL_ID)

    def _get_channels(self):
        return self.db.get_channels()

    def _channel_exists(self):
        return self.db.channel_exists(BaseTest.CHANNEL_ID)

    def _room_exists(self):
        return self.db.room_exists(BaseTest.CHANNEL_ID, BaseTest.ROOM_ID)

    def _create_channel(self):
        self.db.create_channel(BaseTest.CHANNEL_NAME, BaseTest.CHANNEL_ID, BaseTest.USER_ID)

    def _create_room(self):
        self.db.create_room(
                BaseTest.ROOM_NAME, BaseTest.ROOM_ID, BaseTest.CHANNEL_ID, BaseTest.USER_ID, BaseTest.USER_NAME)

    def _room_name_exists(self):
        return self.db.room_name_exists(BaseTest.CHANNEL_ID, BaseTest.ROOM_NAME)


class DatabasePostgresTest(BaseDatabaseTest):
    """
    def is_admin(self, user_id: str) -> bool
    def get_channels(self) -> dict
    def channel_exists(self, channel_id) -> bool
    def rooms_for_channel(self, channel_id) -> dict
    def room_name_exists(self, channel_id, room_name: str) -> bool
    def room_exists(self, channel_id: str, room_id: str) -> bool
    def rooms_for_user(self, user_id: str = None) -> dict
    def remove_current_rooms_for_user(self, user_id: str) -> None
    def set_user_offline(self, user_id: str) -> None
    def set_user_online(self, user_id: str) -> None
    def set_user_invisible(self, user_id: str) ->

    def delete_acl(self, room_id: str, acl_type: str) -> None
    def add_acls(self, room_id: str, acls: dict) -> None
    def get_acls(self, room_id: str) -> list
    """

    def setUp(self):
        self.set_up_env('postgres')

    def tearDown(self):
        from dino.db.postgres.dbman import Database
        from dino.db.postgres.dbman import DeclarativeBase
        db = Database(self.env)
        con = db.engine.connect()
        trans = con.begin()
        for table in reversed(DeclarativeBase.metadata.sorted_tables):
            con.execute(table.delete())
        trans.commit()
        con.close()

        self.env.cache.flushall()

    def test_is_admin_before_create(self):
        self._test_is_admin_before_create()

    def test_is_admin_after_create(self):
        self._test_is_admin_after_create()

    def test_is_admin_after_create_set_admin(self):
        self._test_is_admin_after_create_set_admin()

    def test_get_user_status_before_set(self):
        self._test_get_user_status_before_set(UserStatus.STATUS_UNAVAILABLE)

    def test_set_user_offline(self):
        self._test_set_user_offline(UserStatus.STATUS_UNAVAILABLE)

    def test_set_user_online(self):
        self._test_set_user_online(UserStatus.STATUS_AVAILABLE)

    def test_set_user_invisible(self):
        self._test_set_user_invisible(UserStatus.STATUS_INVISIBLE)

    def test_remove_current_rooms_for_user_before_joining(self):
        self._test_remove_current_rooms_for_user_before_joining()

    def test_remove_current_rooms_for_user_after_joining(self):
        self._test_remove_current_rooms_for_user_after_joining()

    def test_rooms_for_user_before_joining(self):
        self._test_rooms_for_user_before_joining()

    def test_rooms_for_user_after_joining(self):
        self._test_rooms_for_user_after_joining()

    def test_rooms_for_channel_before_create_channel(self):
        self._test_rooms_for_channel_before_create_channel()

    def test_rooms_for_channel_after_create_channel_before_create_room(self):
        self._test_rooms_for_channel_after_create_channel_before_create_room()

    def test_rooms_for_channel_after_create_channel_after_create_room(self):
        self._test_rooms_for_channel_after_create_channel_after_create_room()

    def test_get_channels_before_create(self):
        self._test_get_channels_before_create()

    def test_get_channels_after_create(self):
        self._test_get_channels_after_create()

    def test_room_exists(self):
        self._test_room_exists()

    def test_create_room_no_channel(self):
        self._test_create_room_no_channel()

    def test_create_existing_channel(self):
        self._test_create_existing_channel()

    def test_create_channel(self):
        self._test_create_channel()
        channels = self.db._session().query(Channels).filter(Channels.uuid == BaseTest.CHANNEL_ID).all()
        self.assertEqual(1, len(channels))

    def test_create_channel_again_to_make_sure_tables_cleared_after_each_test(self):
        self._test_create_channel()
        channels = self.db._session().query(Channels).filter(Channels.uuid == BaseTest.CHANNEL_ID).all()
        self.assertEqual(1, len(channels))

    def test_create_room(self):
        self._test_create_room()
        rooms = self.db._session().query(Rooms).filter(Rooms.uuid == BaseTest.ROOM_ID).all()
        self.assertEqual(1, len(rooms))

    def test_create_existing_room(self):
        self._test_create_existing_room()

    def test_channel_exists_after_create(self):
        self._test_channel_exists_after_create()

    def test_channel_exists_before_create(self):
        self._test_channel_exists_before_create()

    def test_room_name_exists_before_create(self):
        self._test_room_name_exists_before_create()

    def test_room_name_exists_after_create(self):
        self._test_room_name_exists_after_create()
