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

from dino.db.manager.users import UserManager
from dino.exceptions import NoSuchChannelException
from dino.exceptions import NoSuchRoomException
from dino.exceptions import UnknownBanTypeException
from dino.utils import b64d

from test.db import BaseDatabaseTest

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class UserManagerTest(BaseDatabaseTest):
    _act = None

    @staticmethod
    def _publish(activity: dict, external=False) -> None:
        UserManagerTest._act = activity

    def setUp(self):
        self.set_up_env('redis')
        self.env.publish = UserManagerTest._publish
        self._act = None
        self.env.db = self.db
        self.manager = UserManager(self.env)

    def tearDown(self):
        self.db.redis.flushall()
        self.env.cache._flushall()

    def test_get_users_for_room(self):
        self._create_channel()
        self._create_room()
        users = self.manager.get_users_for_room(UserManagerTest.ROOM_ID)
        self.assertEqual(0, len(users))

    def test_get_users_for_room_after_join(self):
        self._create_channel()
        self._create_room()
        self._join()
        users = self.manager.get_users_for_room(UserManagerTest.ROOM_ID)
        self.assertEqual(1, len(users))
        self.assertEqual(UserManagerTest.USER_ID, users[0]['uuid'])
        self.assertEqual(UserManagerTest.USER_NAME, users[0]['name'])

    def test_kick_user(self):
        self._create_channel()
        self._create_room()
        self.manager.kick_user(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID)
        self.assertIsNotNone(UserManagerTest._act)
        self.assertEqual(UserManagerTest._act['target']['objectType'], 'room')
        self.assertEqual(UserManagerTest._act['object']['id'], BaseDatabaseTest.USER_ID)
        self.assertEqual(UserManagerTest._act['target']['id'], BaseDatabaseTest.ROOM_ID)

    def test_kick_user_is_base64(self):
        self._create_channel()
        self._create_room()
        self.manager.kick_user(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID)
        self.assertIsNotNone(UserManagerTest._act)
        self.assertEqual(UserManagerTest._act['target']['objectType'], 'room')
        self.assertEqual(b64d(UserManagerTest._act['object']['displayName']), BaseDatabaseTest.USER_NAME)
        self.assertEqual(b64d(UserManagerTest._act['target']['displayName']), BaseDatabaseTest.ROOM_NAME)

    def test_ban_user_globally(self):
        self._create_channel()
        self._create_room()
        self.manager.ban_user(BaseDatabaseTest.USER_ID, BaseDatabaseTest.ROOM_ID, '5m', 'global')
        self.assertIsNotNone(UserManagerTest._act)
        self.assertEqual(UserManagerTest._act['object']['id'], BaseDatabaseTest.USER_ID)
        self.assertEqual(UserManagerTest._act['target']['objectType'], 'global')
        self.assertNotIn('id', UserManagerTest._act['target'])
        self.assertEqual(b64d(UserManagerTest._act['object']['displayName']), BaseDatabaseTest.USER_NAME)

    def test_ban_user_channel(self):
        self._create_channel()
        self._create_room()
        self.manager.ban_user(BaseDatabaseTest.USER_ID, BaseDatabaseTest.CHANNEL_ID, '5m', 'channel')
        self.assertIsNotNone(UserManagerTest._act)
        self.assertEqual(UserManagerTest._act['object']['id'], BaseDatabaseTest.USER_ID)
        self.assertEqual(UserManagerTest._act['target']['id'], BaseDatabaseTest.CHANNEL_ID)
        self.assertEqual(UserManagerTest._act['target']['objectType'], 'channel')
        self.assertEqual(b64d(UserManagerTest._act['object']['displayName']), BaseDatabaseTest.USER_NAME)

    def test_ban_user_room(self):
        self._create_channel()
        self._create_room()
        self.manager.ban_user(BaseDatabaseTest.USER_ID, BaseDatabaseTest.ROOM_ID, '5m', 'room')
        self.assertIsNotNone(UserManagerTest._act)
        self.assertEqual(UserManagerTest._act['object']['id'], BaseDatabaseTest.USER_ID)
        self.assertEqual(UserManagerTest._act['target']['id'], BaseDatabaseTest.ROOM_ID)
        self.assertEqual(UserManagerTest._act['target']['objectType'], 'room')
        self.assertEqual(b64d(UserManagerTest._act['object']['displayName']), BaseDatabaseTest.USER_NAME)

    def test_ban_user_no_room(self):
        self._create_channel()
        self.assertRaises(NoSuchRoomException, self.manager.ban_user, BaseDatabaseTest.USER_ID, BaseDatabaseTest.ROOM_ID, '5m', 'room')

    def test_ban_user_no_channel(self):
        self.assertRaises(NoSuchChannelException, self.manager.ban_user, BaseDatabaseTest.USER_ID, BaseDatabaseTest.CHANNEL_ID, '5m', 'channel')

    def test_ban_use_unknown_type(self):
        self.assertRaises(UnknownBanTypeException, self.manager.ban_user, BaseDatabaseTest.USER_ID, BaseDatabaseTest.CHANNEL_ID, '5m', 'something-unknown')

    def test_remove_ban_unknown_type(self):
        self._create_channel()
        self._create_room()
        self.assertRaises(UnknownBanTypeException, self.manager.remove_ban, BaseDatabaseTest.USER_ID, BaseDatabaseTest.CHANNEL_ID, 'something-unknown')

    def test_remove_ban_channel(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self.db.is_banned_from_channel(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)[0])

        timestamp = str(int((datetime.utcnow() + timedelta(minutes=5)).timestamp()))
        self.db.ban_user_channel(BaseDatabaseTest.USER_ID, timestamp, '5m',  BaseDatabaseTest.CHANNEL_ID)
        self.assertTrue(self.db.is_banned_from_channel(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)[0])

        self.manager.remove_ban(BaseDatabaseTest.USER_ID, BaseDatabaseTest.CHANNEL_ID, 'channel')
        self.assertFalse(self.db.is_banned_from_channel(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)[0])

    def test_remove_ban_room(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self.db.is_banned_from_room(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID)[0])

        timestamp = str(int((datetime.utcnow() + timedelta(minutes=5)).timestamp()))
        self.db.ban_user_room(BaseDatabaseTest.USER_ID, timestamp, '5m',  BaseDatabaseTest.ROOM_ID)
        self.assertTrue(self.db.is_banned_from_room(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID)[0])

        self.manager.remove_ban(BaseDatabaseTest.USER_ID, BaseDatabaseTest.ROOM_ID, 'room')
        self.assertFalse(self.db.is_banned_from_room(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID)[0])

    def test_remove_ban_globally(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self.db.is_banned_globally(BaseDatabaseTest.USER_ID)[0])

        timestamp = str(int((datetime.utcnow() + timedelta(minutes=5)).timestamp()))
        self.db.ban_user_global(BaseDatabaseTest.USER_ID, timestamp, '5m')
        self.assertTrue(self.db.is_banned_globally(BaseDatabaseTest.USER_ID)[0])

        self.manager.remove_ban(BaseDatabaseTest.USER_ID, BaseDatabaseTest.CHANNEL_ID, 'global')
        self.assertFalse(self.db.is_banned_globally(BaseDatabaseTest.USER_ID)[0])

    def test_get_banned_users_is_empty(self):
        self._create_channel()
        self._create_room()
        banned = self.manager.get_banned_users()
        self.assertEqual({'channels', 'rooms', 'global'}, set(banned.keys()))
        self.assertEqual(0, len(banned['channels']))
        self.assertEqual(0, len(banned['rooms']))
        self.assertEqual(0, len(banned['global']))

    def test_get_banned_users_channel(self):
        self._create_channel()
        self._create_room()

        timestamp = str(int((datetime.utcnow() + timedelta(minutes=5)).timestamp()))
        self.db.ban_user_channel(BaseDatabaseTest.USER_ID, timestamp, '5m',  BaseDatabaseTest.CHANNEL_ID)

        banned = self.manager.get_banned_users()
        self.assertEqual({'channels', 'rooms', 'global'}, set(banned.keys()))
        self.assertEqual(1, len(banned['channels']))
        self.assertEqual(0, len(banned['rooms']))
        self.assertEqual(0, len(banned['global']))
        self.assertEqual(BaseDatabaseTest.USER_NAME,
                         b64d(banned['channels'][BaseDatabaseTest.CHANNEL_ID]['users'][BaseDatabaseTest.USER_ID]['name']))

    def test_get_banned_users_room(self):
        self._create_channel()
        self._create_room()

        timestamp = str(int((datetime.utcnow() + timedelta(minutes=5)).timestamp()))
        self.db.ban_user_room(BaseDatabaseTest.USER_ID, timestamp, '5m',  BaseDatabaseTest.ROOM_ID)

        banned = self.manager.get_banned_users()
        self.assertEqual({'channels', 'rooms', 'global'}, set(banned.keys()))
        self.assertEqual(0, len(banned['channels']))
        self.assertEqual(1, len(banned['rooms']))
        self.assertEqual(0, len(banned['global']))
        self.assertEqual(BaseDatabaseTest.USER_NAME,
                         b64d(banned['rooms'][BaseDatabaseTest.ROOM_ID]['users'][BaseDatabaseTest.USER_ID]['name']))

    def test_get_banned_users_globally(self):
        self._create_channel()
        self._create_room()

        timestamp = str(int((datetime.utcnow() + timedelta(minutes=5)).timestamp()))
        self.db.ban_user_global(BaseDatabaseTest.USER_ID, timestamp, '5m')

        banned = self.manager.get_banned_users()
        self.assertEqual({'channels', 'rooms', 'global'}, set(banned.keys()))
        self.assertEqual(0, len(banned['channels']))
        self.assertEqual(0, len(banned['rooms']))
        self.assertEqual(1, len(banned['global']))
        self.assertEqual(BaseDatabaseTest.USER_NAME,
                         b64d(banned['global'][BaseDatabaseTest.USER_ID]['name']))

    def test_get_super_users(self):
        self.assertEqual(0, len(self.manager.get_super_users()))

    def test_get_super_users_after_create(self):
        self.manager.create_super_user(BaseDatabaseTest.OTHER_USER_NAME, BaseDatabaseTest.OTHER_USER_ID)
        super_users = self.manager.get_super_users()
        self.assertEqual(1, len(super_users))
        self.assertEqual(BaseDatabaseTest.OTHER_USER_ID, super_users[0]['uuid'])
        self.assertEqual(BaseDatabaseTest.OTHER_USER_NAME, super_users[0]['name'])

    def test_create_super_user_empty_id(self):
        self.manager.create_super_user(BaseDatabaseTest.USER_NAME, '')
        self.assertEqual(0, len(self.manager.get_super_users()))

    def test_create_super_user_empty_name(self):
        self.manager.create_super_user('', BaseDatabaseTest.USER_ID)
        self.assertEqual(0, len(self.manager.get_super_users()))

    def test_add_channel_admin(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self.db.is_admin(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID))
        self.manager.add_channel_admin(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)
        self.assertTrue(self.db.is_admin(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID))

    def test_add_channel_owner(self):
        self._create_channel()
        self._create_room()
        self.db.remove_owner_channel(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)
        self.assertFalse(self.db.is_owner_channel(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID))
        self.manager.add_channel_owner(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)
        self.assertTrue(self.db.is_owner_channel(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID))

    def test_add_room_owner(self):
        self._create_channel()
        self._create_room()
        self.db.remove_owner(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID)
        self.assertFalse(self.db.is_owner(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID))
        self.manager.add_room_owner(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID)
        self.assertTrue(self.db.is_owner(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID))

    def test_add_room_moderator(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self.db.is_moderator(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID))
        self.manager.add_room_moderator(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID)
        self.assertTrue(self.db.is_moderator(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID))

    def test_remove_channel_admin(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self.db.is_admin(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID))

        self.manager.add_channel_admin(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)
        self.assertTrue(self.db.is_admin(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID))

        self.manager.remove_channel_admin(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)
        self.assertFalse(self.db.is_admin(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID))

    def test_remove_channel_owner(self):
        self._create_channel()
        self._create_room()
        self.assertTrue(self.db.is_owner_channel(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID))

        self.manager.remove_channel_owner(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID)
        self.assertFalse(self.db.is_owner_channel(BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.USER_ID))

    def test_remove_room_owner(self):
        self._create_channel()
        self._create_room()
        self.assertTrue(self.db.is_owner(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID))

        self.manager.remove_room_owner(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID)
        self.assertFalse(self.db.is_owner(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID))

    def test_remove_room_moderator(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self.db.is_moderator(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID))

        self.manager.add_room_moderator(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID)
        self.assertTrue(self.db.is_moderator(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID))

        self.manager.remove_room_moderator(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID)
        self.assertFalse(self.db.is_moderator(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID))
