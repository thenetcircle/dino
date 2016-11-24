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

from test.base import BaseTest

from activitystreams import parse
from uuid import uuid4 as uuid
from datetime import datetime
from datetime import timedelta
import time

from dino.environ import ConfigDict
from dino import environ

from dino.config import ConfigKeys
from dino.config import ApiActions
from dino.config import SessionKeys
from dino.cache.redis import CacheRedis
from dino.db.rdbms.handler import DatabaseRdbms
from dino.environ import GNEnvironment
from dino.validation.acl import AclStrInCsvValidator
from dino.validation.acl import AclSameChannelValidator
from dino.validation.acl import AclSameRoomValidator
from dino.validation.acl import AclDisallowValidator
from dino.validation.acl import AclRangeValidator
from dino.validation.acl import AclIsAdminValidator
from dino.validation.acl import AclIsSuperUserValidator

from dino.exceptions import ChannelExistsException
from dino.exceptions import NoSuchChannelException
from dino.exceptions import RoomExistsException
from dino.exceptions import NoChannelFoundException
from dino.exceptions import NoSuchRoomException
from dino.exceptions import NoSuchUserException
from dino.exceptions import UserExistsException
from dino.exceptions import RoomNameExistsForChannelException
from dino.exceptions import InvalidApiActionException
from dino.exceptions import InvalidAclTypeException
from dino.exceptions import InvalidAclValueException

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class BaseDatabaseTest(BaseTest):
    class FakeEnv(GNEnvironment):
        def __init__(self):
            super(BaseDatabaseTest.FakeEnv, self).__init__(None, ConfigDict(), skip_init=True)
            self.config = ConfigDict()
            self.cache = CacheRedis('mock')
            self.session = dict()

    MESSAGE_ID = str(uuid())

    def set_up_env(self, db):
        self.env = BaseDatabaseTest.FakeEnv()
        self.env.config.set(ConfigKeys.TESTING, False)
        all_acls = [
            'age',
            'gender',
            'membership',
            'group',
            'country',
            'city',
            'image',
            'has_webcam',
            'fake_checked',
            'owner',
            'admin',
            'moderator',
            'superuser',
            'crossroom',
            'samechannel',
            'sameroom',
            'disallow'
        ]
        self.env.config.set(ConfigKeys.ACL, {
                'room': {
                    'join': {
                        'acls': all_acls
                    },
                    'message': {
                        'acls': all_acls
                    },
                    'history': {
                        'acls': all_acls
                    },
                    'crossroom': {
                        'acls': all_acls
                    }
                },
                'channel': {
                    'message': {
                        'acls': all_acls
                    },
                    'list': {
                        'acls': all_acls
                    },
                    'crossroom': {
                        'acls': all_acls
                    }
                },
                'available': {
                    'acls': all_acls
                },
                'validation': {
                    'samechannel': {
                        'type': 'samechannel',
                        'value': AclSameChannelValidator()
                    },
                    'sameroom': {
                        'type': 'sameroom',
                        'value': AclSameRoomValidator()
                    },
                    'country': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator()
                    },
                    'disallow': {
                        'type': 'disallow',
                        'value': AclDisallowValidator()
                    },
                    'gender': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('m,f')
                    },
                    'membership': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator()
                    },
                    'city': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator()
                    },
                    'has_webcam': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('y,n')
                    },
                    'fake_checked': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('y,n')
                    },
                    'image': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('y,n')
                    },
                    'group': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('')
                    },
                    'age': {
                        'type': 'range',
                        'value': AclRangeValidator()
                    },
                    'admin': {
                        'type': 'is_admin',
                        'value': AclIsAdminValidator()
                    },
                    'superuser': {
                        'type': 'is_super_user',
                        'value': AclIsSuperUserValidator()
                    }
                }
            }
        )

        self.env.session[SessionKeys.user_name.value] = BaseTest.USER_NAME

        if db == 'postgres':
            self.env.config.set(ConfigKeys.DRIVER, 'postgres+psycopg2', domain=ConfigKeys.DATABASE)
            self.env.config.set(ConfigKeys.HOST, 'localhost', domain=ConfigKeys.DATABASE)
            self.env.config.set(ConfigKeys.PORT, 5432, domain=ConfigKeys.DATABASE)
            self.env.config.set(ConfigKeys.DB, 'dinotest', domain=ConfigKeys.DATABASE)
            self.env.config.set(ConfigKeys.USER, 'dinouser', domain=ConfigKeys.DATABASE)
            self.env.config.set(ConfigKeys.PASSWORD, 'dinopass', domain=ConfigKeys.DATABASE)
            self.db = DatabaseRdbms(self.env)
        elif db == 'sqlite':
            self.env.config.set(ConfigKeys.DRIVER, 'sqlite', domain=ConfigKeys.DATABASE)
            self.db = DatabaseRdbms(self.env)
        elif db == 'redis':
            from dino.db.redis import DatabaseRedis
            self.db = DatabaseRedis(self.env, 'mock', db=99)
            self.db.redis.flushall()
        else:
            raise ValueError('unknown type %s' % db)

        environ.env.config = self.env.config

    def act_message(self):
        data = self.activity_for_message()
        data['id'] = BaseDatabaseTest.MESSAGE_ID
        data['target']['objectType'] = 'room'
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

    def _test_leave_room_not_joined(self):
        self._create_channel()
        self._create_room()

        rooms = self._rooms_for_user()
        self.assertEqual(0, len(rooms))
        self._leave()
        rooms = self._rooms_for_user()
        self.assertEqual(0, len(rooms))

    def _test_leave_room_joined(self):
        self._create_channel()
        self._create_room()

        rooms = self._rooms_for_user()
        self.assertEqual(0, len(rooms))

        self._join()
        rooms = self._rooms_for_user()
        self.assertEqual(1, len(rooms))

        self._leave()
        rooms = self._rooms_for_user()
        self.assertEqual(0, len(rooms))

    def _test_set_moderator_no_room(self):
        self.assertRaises(NoChannelFoundException, self._set_moderator)
        self.assertFalse(self._is_moderator())

    def _test_set_moderator_with_room(self):
        self._create_channel()
        self._create_room()
        self._set_moderator()
        self.assertTrue(self._is_moderator())

    def _test_set_room_owner_no_room(self):
        self.assertRaises(NoChannelFoundException, self._set_owner_room)
        self.assertFalse(self._is_owner_room())

    def _test_set_room_owner_with_room(self):
        self._create_channel()
        self._create_room()
        self._set_owner_room()
        self.assertTrue(self._is_owner_room())

    def _test_set_channel_owner_no_channel(self):
        self.assertRaises(NoSuchChannelException, self._set_owner_channel)
        self.assertFalse(self._is_owner_channel())

    def _test_set_channel_owner_with_channel(self):
        self._create_channel()
        self._set_owner_channel()
        self.assertTrue(self._is_owner_channel())

    def _test_create_room(self):
        self.assertFalse(self._room_exists())
        self._create_channel()
        self._create_room()
        self.assertTrue(self._room_exists())

    def _test_create_existing_room(self):
        self._create_channel()
        self._create_room()
        self.assertRaises(RoomExistsException, self._create_room)

    def _test_create_existing_room_name(self):
        self._create_channel()
        self._create_room()
        self.assertRaises(RoomNameExistsForChannelException, self._create_room, str(uuid()))

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

    def _test_channel_for_room_no_channel(self):
        self.assertRaises(NoChannelFoundException, self._channel_for_room)

    def _test_channel_for_room_with_channel_without_room(self):
        self._create_channel()
        self.assertRaises(NoChannelFoundException, self._channel_for_room)

    def _test_channel_for_room_with_channel_with_room(self):
        self._create_channel()
        self._create_room()
        self._channel_for_room()

    def _channel_for_room(self):
        return self.db.channel_for_room(BaseTest.ROOM_ID)

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

    def _set_owner_room(self):
        self.db.set_owner(BaseTest.ROOM_ID, BaseTest.USER_ID)

    def _set_owner_channel(self):
        self.db.set_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID)

    def _is_owner_room(self):
        return self.db.is_owner(BaseTest.ROOM_ID, BaseTest.USER_ID)

    def _is_owner_channel(self):
        return self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID)

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

    def _leave(self):
        self.db.leave_room(BaseTest.USER_ID, BaseTest.ROOM_ID)

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

    def _create_room(self, room_id=BaseTest.ROOM_ID):
        self.db.create_room(
                BaseTest.ROOM_NAME, room_id, BaseTest.CHANNEL_ID, BaseTest.USER_ID, BaseTest.USER_NAME)

    def _room_name_exists(self):
        return self.db.room_name_exists(BaseTest.CHANNEL_ID, BaseTest.ROOM_NAME)

    def _test_delete_one_non_existing_acl(self):
        self._create_channel()
        self._create_room()
        acls = {
            'gender': 'm,f',
            'membership': '0,1,2'
        }
        self.db.add_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.JOIN, acls)
        fetched = self.db.get_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.JOIN)
        self.assertEqual(fetched.items(), acls.items())

        self.db.delete_acl_in_room_for_action(BaseTest.ROOM_ID, 'image', ApiActions.JOIN)
        fetched = self.db.get_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.JOIN)

        self.assertEqual(fetched.items(), acls.items())

    def _test_add_one_extra_acl(self):
        self._create_channel()
        self._create_room()
        acls = {
            'gender': 'm,f',
            'membership': '0,1,2'
        }
        self.db.add_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.JOIN, acls)
        fetched = self.db.get_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.JOIN)
        self.assertEqual(fetched.items(), acls.items())

        self.db.add_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.JOIN, {'image': 'y'})
        acls['image'] = 'y'
        fetched = self.db.get_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.JOIN)

        self.assertEqual(fetched.items(), acls.items())

    def _test_get_acl(self):
        self._create_channel()
        self._create_room()
        self.assertEqual(0, len(self.db.get_all_acls_room(BaseTest.ROOM_ID)))

    def _test_set_acl(self):
        self._create_channel()
        self._create_room()
        acls = {
            'gender': 'm,f',
            'membership': '0,1,2'
        }
        self.db.add_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.JOIN, acls)
        fetched = self.db.get_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.JOIN)
        self.assertEqual(fetched.items(), acls.items())

    def _test_delete_one_acl(self):
        self._create_channel()
        self._create_room()
        acls = {
            'gender': 'm,f',
            'membership': '0,1,2'
        }
        self.db.add_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.JOIN, acls)
        fetched = self.db.get_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.JOIN)
        self.assertEqual(fetched.items(), acls.items())
        del acls['gender']

        self.db.delete_acl_in_room_for_action(BaseTest.ROOM_ID, 'gender', ApiActions.JOIN)
        fetched = self.db.get_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.JOIN)

        self.assertEqual(fetched.items(), acls.items())

    def _test_set_room_allows_cross_group_messaging(self):
        self._create_channel()
        self._create_room()
        self._set_allow_cross_group()

    def _test_get_room_allows_cross_group_messaging_no_room(self):
        self._create_channel()
        self.assertRaises(NoSuchRoomException, self._room_allows_cross_group_messaging)

    def _test_get_room_allows_cross_group_messaging(self):
        self._create_channel()
        self._create_room()
        self._set_allow_cross_group()
        self.assertTrue(self._room_allows_cross_group_messaging())

    def _test_get_room_does_not_allow_cross_group_messaging(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self._room_allows_cross_group_messaging())

    def _test_room_allows_cross_group_messaging_no_channel(self):
        self.assertRaises(NoSuchChannelException, self._room_allows_cross_group_messaging)

    def _test_room_allows_cross_group_messaging_no_room(self):
        self._create_channel()
        self.assertRaises(NoSuchRoomException, self._room_allows_cross_group_messaging)

    def _test_room_allows_cross_group_messaging(self):
        self._create_channel()
        self._create_room()
        self._set_allow_cross_group()
        self.assertTrue(self._room_allows_cross_group_messaging())

    def _test_room_does_not_allow_cross_group_messaging_no_room(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self._room_allows_cross_group_messaging())

    def _set_allow_cross_group(self):
        self.db.add_acls_in_channel_for_action(
                BaseTest.CHANNEL_ID, ApiActions.CROSSROOM, {'samechannel': ''})
        self.db.add_acls_in_room_for_action(
                BaseTest.ROOM_ID, ApiActions.CROSSROOM, {'samechannel': ''})

    def _room_allows_cross_group_messaging(self):
        channel_acls = self.db.get_acls_in_channel_for_action(BaseTest.CHANNEL_ID, ApiActions.CROSSROOM)
        if 'disallow' in channel_acls.keys():
            return False

        room_acls = self.db.get_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.CROSSROOM)
        if 'disallow' in room_acls.keys():
            return False

        return 'samechannel' in channel_acls or 'samechannel' in room_acls

    def _test_create_admin_room(self):
        self._create_channel()
        self.db.create_admin_room_for(BaseTest.CHANNEL_ID)
        room_id = self.db.admin_room_for_channel(BaseTest.CHANNEL_ID)
        self.assertIsNotNone(room_id)

    def _test_get_private_room(self):
        room_id, channel_id = self.db.get_private_room(BaseTest.USER_ID)
        self.assertIsNotNone(room_id)

    def _test_is_room_private(self):
        room_id, _ = self.db.get_private_room(BaseTest.USER_ID)
        self.assertTrue(self.db.is_room_private(room_id))

    def _test_get_private_channel_for_room(self):
        room_id, channel_id = self.db.get_private_room(BaseTest.USER_ID)
        self.assertEqual(self.db.get_private_channel_for_room(room_id), channel_id)

    def _test_get_private_channel_for_prefix(self):
        room_id, channel_id = self.db.get_private_room(BaseTest.USER_ID)
        private_channel_id = self.db.get_private_channel_for_prefix(room_id[:2])
        self.assertEqual(private_channel_id, channel_id)

    def _test_create_private_channel_for_room(self):
        room_id = str(uuid())
        channel_id = self.db.create_private_channel_for_room(room_id)
        private_channel_id = self.db.get_private_channel_for_room(room_id)
        self.assertEqual(private_channel_id, channel_id)

    def _test_is_super_user(self):
        self.assertFalse(self.db.is_super_user(BaseTest.USER_ID))
        self.db.set_super_user(BaseTest.USER_ID)
        self.assertTrue(self.db.is_super_user(BaseTest.USER_ID))

    def _test_get_admin_room_for_channel(self):
        self._create_channel()
        room_id = self.db.create_admin_room_for(BaseTest.CHANNEL_ID)
        self.assertIsNotNone(room_id)

    def _test_set_owner_and_moderator(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self.db.is_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID))
        self.assertTrue(self.db.is_owner(BaseTest.ROOM_ID, BaseTest.USER_ID))

        self.db.remove_owner(BaseTest.ROOM_ID, BaseTest.USER_ID)
        self.assertFalse(self.db.is_owner(BaseTest.ROOM_ID, BaseTest.USER_ID))

        self.db.set_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID)
        self.db.set_owner(BaseTest.ROOM_ID, BaseTest.USER_ID)

        self.assertTrue(self.db.is_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID))
        self.assertTrue(self.db.is_owner(BaseTest.ROOM_ID, BaseTest.USER_ID))

    def _test_remove_channel_role(self):
        self._create_channel()
        self._create_room()
        self.assertTrue(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

        self.db.remove_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.assertFalse(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

    def _test_remove_room_role(self):
        self._create_channel()
        self._create_room()
        self.assertTrue(self.db.is_owner(BaseTest.ROOM_ID, BaseTest.USER_ID))

        self.db.remove_owner(BaseTest.ROOM_ID, BaseTest.USER_ID)
        self.assertFalse(self.db.is_owner(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

    def _test_get_super_users(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self.db.is_super_user(BaseTest.USER_ID))
        self.db.set_super_user(BaseTest.USER_ID)
        self.assertTrue(self.db.is_super_user(BaseTest.USER_ID))

        super_users = self.db.get_super_users()
        self.assertEqual(1, len(super_users))
        self.assertIn(BaseTest.USER_ID, super_users.keys())
        self.assertIn(BaseTest.USER_NAME, super_users.values())

    def _test_remove_super_user(self):
        self.assertFalse(self.db.is_super_user(BaseTest.USER_ID))

        self.db.set_super_user(BaseTest.USER_ID)
        self.assertTrue(self.db.is_super_user(BaseTest.USER_ID))

        self.db.remove_super_user(BaseTest.USER_ID)
        self.assertFalse(self.db.is_super_user(BaseTest.USER_ID))

    def _test_remove_owner(self):
        self._create_channel()
        self._create_room()
        self.assertTrue(self.db.is_owner(BaseTest.ROOM_ID, BaseTest.USER_ID))

        self.db.remove_owner(BaseTest.ROOM_ID, BaseTest.USER_ID)
        self.assertFalse(self.db.is_owner(BaseTest.ROOM_ID, BaseTest.USER_ID))

    def _test_remove_channel_owner(self):
        self._create_channel()
        self._create_room()
        self.assertTrue(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

        self.db.remove_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.assertFalse(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

    def _test_remove_admin(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self.db.is_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

        self.db.set_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.assertTrue(self.db.is_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

        self.db.remove_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.assertFalse(self.db.is_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

    def _test_remove_moderator(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self.db.is_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID))

        self.db.set_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID)
        self.assertTrue(self.db.is_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID))

        self.db.remove_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID)
        self.assertFalse(self.db.is_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID))

    def _test_set_owner_is_unique(self):
        self._create_channel()
        self._create_room()
        self.assertTrue(self.db.is_owner(BaseTest.ROOM_ID, BaseTest.USER_ID))

        self.db.set_owner(BaseTest.ROOM_ID, BaseTest.USER_ID)
        self.assertTrue(self.db.is_owner(BaseTest.ROOM_ID, BaseTest.USER_ID))

        users = self.db.get_owners_room(BaseTest.ROOM_ID)
        self.assertEqual(1, len(users))
        self.assertIn(BaseTest.USER_ID, users.keys())
        self.assertIn(BaseTest.USER_NAME, users.values())

    def _test_set_owner_channel_is_unique(self):
        self._create_channel()
        self._create_room()
        self.assertTrue(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

        self.db.set_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.assertTrue(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

        users = self.db.get_owners_channel(BaseTest.CHANNEL_ID)
        self.assertEqual(1, len(users))
        self.assertIn(BaseTest.USER_ID, users.keys())
        self.assertIn(BaseTest.USER_NAME, users.values())

    def _test_set_moderator_is_unique(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self.db.is_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID))

        self.db.set_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID)
        self.assertTrue(self.db.is_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID))

        self.db.set_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID)
        self.assertTrue(self.db.is_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID))

        users = self.db.get_moderators_room(BaseTest.ROOM_ID)
        self.assertEqual(1, len(users))
        self.assertIn(BaseTest.USER_ID, users.keys())
        self.assertIn(BaseTest.USER_NAME, users.values())

    def _test_set_admin_is_unique(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self.db.is_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

        self.db.set_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.assertTrue(self.db.is_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

        self.db.set_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.assertTrue(self.db.is_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

        users = self.db.get_admins_channel(BaseTest.CHANNEL_ID)
        self.assertEqual(1, len(users))
        self.assertIn(BaseTest.USER_ID, users.keys())
        self.assertIn(BaseTest.USER_NAME, users.values())

    def _test_set_super_user_is_unique(self):
        self._create_channel()
        self._create_room()
        self.assertFalse(self.db.is_super_user(BaseTest.USER_ID))

        self.db.set_super_user(BaseTest.USER_ID)
        self.assertTrue(self.db.is_super_user(BaseTest.USER_ID))

        self.db.set_super_user(BaseTest.USER_ID)
        self.assertTrue(self.db.is_super_user(BaseTest.USER_ID))

        users = self.db.get_super_users()
        self.assertEqual(1, len(users))
        self.assertIn(BaseTest.USER_ID, users.keys())
        self.assertIn(BaseTest.USER_NAME, users.values())

    def _test_remove_super_user_without_setting(self):
        self._create_channel()
        self._create_room()

        self.assertFalse(self.db.is_super_user(BaseTest.OTHER_USER_ID))
        self.db.remove_super_user(BaseTest.OTHER_USER_ID)
        self.assertFalse(self.db.is_super_user(BaseTest.OTHER_USER_ID))

    def _test_remove_owner_without_setting(self):
        self._create_channel()
        self._create_room()

        self.assertFalse(self.db.is_owner(BaseTest.ROOM_ID, BaseTest.OTHER_USER_ID))
        self.db.remove_owner(BaseTest.ROOM_ID, BaseTest.OTHER_USER_ID)
        self.assertFalse(self.db.is_owner(BaseTest.ROOM_ID, BaseTest.OTHER_USER_ID))

    def _test_remove_channel_owner_without_setting(self):
        self._create_channel()
        self._create_room()

        self.assertFalse(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.OTHER_USER_ID))
        self.db.remove_owner_channel(BaseTest.CHANNEL_ID, BaseTest.OTHER_USER_ID)
        self.assertFalse(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.OTHER_USER_ID))

    def _test_remove_admin_without_setting(self):
        self._create_channel()
        self._create_room()

        self.assertFalse(self.db.is_admin(BaseTest.CHANNEL_ID, BaseTest.OTHER_USER_ID))
        self.db.remove_admin(BaseTest.CHANNEL_ID, BaseTest.OTHER_USER_ID)
        self.assertFalse(self.db.is_admin(BaseTest.CHANNEL_ID, BaseTest.OTHER_USER_ID))

    def _test_remove_moderator_without_setting(self):
        self._create_channel()
        self._create_room()

        self.assertFalse(self.db.is_moderator(BaseTest.ROOM_ID, BaseTest.OTHER_USER_ID))
        self.db.remove_moderator(BaseTest.ROOM_ID, BaseTest.OTHER_USER_ID)
        self.assertFalse(self.db.is_moderator(BaseTest.ROOM_ID, BaseTest.OTHER_USER_ID))

    def _test_remove_other_role_channel(self):
        self._create_channel()
        self._create_room()
        self.assertTrue(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID))
        self.assertFalse(self.db.is_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

        self.db.set_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.assertTrue(self.db.is_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

        self.db.remove_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.assertFalse(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID))
        self.assertTrue(self.db.is_admin(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

    def _test_remove_other_role_room(self):
        self._create_channel()
        self._create_room()
        self.assertTrue(self.db.is_owner(BaseTest.ROOM_ID, BaseTest.USER_ID))
        self.assertFalse(self.db.is_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID))

        self.db.set_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID)
        self.assertTrue(self.db.is_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID))

        self.db.remove_owner(BaseTest.ROOM_ID, BaseTest.USER_ID)
        self.assertFalse(self.db.is_owner(BaseTest.ROOM_ID, BaseTest.USER_ID))
        self.assertTrue(self.db.is_moderator(BaseTest.ROOM_ID, BaseTest.USER_ID))

    def _test_set_admin_no_such_channel(self):
        self.assertRaises(NoSuchChannelException, self.db.set_admin, BaseTest.CHANNEL_ID, BaseTest.USER_ID)

    def _test_remove_admin_no_such_room(self):
        self.assertRaises(NoSuchChannelException, self.db.remove_admin, BaseTest.CHANNEL_ID, BaseTest.USER_ID)

    def _test_remove_moderator_no_such_room(self):
        self.assertRaises(NoSuchRoomException, self.db.remove_moderator, BaseTest.ROOM_ID, BaseTest.USER_ID)

    def _test_channel_name_exists(self):
        self.assertFalse(self.db.channel_name_exists(BaseTest.CHANNEL_NAME))
        self._create_channel()
        self.assertTrue(self.db.channel_name_exists(BaseTest.CHANNEL_NAME))

    def _test_channel_exists(self):
        self.assertFalse(self.db.channel_exists(''))
        self.assertFalse(self.db.channel_exists(None))
        self.assertFalse(self.db.channel_exists(BaseTest.CHANNEL_ID))
        self._create_channel()
        self.assertTrue(self.db.channel_exists(BaseTest.CHANNEL_ID))

    def _test_create_user(self):
        self.assertRaises(NoSuchUserException, self.db.get_user_name, BaseTest.USER_ID)
        self.db.create_user(BaseTest.USER_ID, BaseTest.USER_NAME)
        self.assertEqual(BaseTest.USER_NAME, self.db.get_user_name(BaseTest.USER_ID))

    def _test_users_in_room(self):
        self.assertRaises(NoChannelFoundException, self.db.users_in_room, BaseTest.ROOM_ID)
        self._create_channel()
        self.assertRaises(NoChannelFoundException, self.db.users_in_room, BaseTest.ROOM_ID)

        self._create_room()
        self.assertEqual(0, len(self.db.users_in_room(BaseTest.ROOM_ID)))

    def _test_delete_acl_in_room_for_action(self):
        self.assertRaises(NoSuchRoomException, self.db.delete_acl_in_room_for_action, BaseTest.ROOM_ID, 'gender', ApiActions.JOIN)
        self._create_channel()
        self.assertRaises(NoSuchRoomException, self.db.delete_acl_in_room_for_action, BaseTest.ROOM_ID, 'gender', ApiActions.JOIN)
        self._create_room()
        self.db.delete_acl_in_room_for_action(BaseTest.ROOM_ID, 'gender', ApiActions.JOIN)

    def _test_delete_acl_in_channel_for_action(self):
        self.assertRaises(NoSuchChannelException, self.db.delete_acl_in_channel_for_action, BaseTest.CHANNEL_ID, 'gender', ApiActions.JOIN)
        self._create_channel()
        self.db.delete_acl_in_channel_for_action(BaseTest.CHANNEL_ID, 'gender', ApiActions.LIST)

    def _test_remove_owner_channel_no_channel(self):
        self.assertRaises(NoSuchChannelException, self.db.remove_owner_channel, BaseTest.CHANNEL_ID, BaseTest.USER_ID)

    def _test_remove_owner_channel_not_owner(self):
        self._create_channel()
        self._create_room()
        self.assertTrue(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID))
        self.db.remove_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.assertFalse(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID))
        self.db.remove_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.assertFalse(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

    def _test_remove_owner_channel_is_owner(self):
        self._create_channel()
        self._create_room()
        self._set_owner_channel()
        self.assertTrue(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID))
        self.db.remove_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.assertFalse(self.db.is_owner_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID))

    def _test_create_user_exists(self):
        self.db.create_user(BaseTest.USER_ID, BaseTest.USER_NAME)
        self.assertRaises(UserExistsException, self.db.create_user, BaseTest.USER_ID, BaseTest.USER_NAME)

    def _test_update_acl_in_room_for_action_no_channel(self):
        self.assertRaises(NoSuchChannelException, self.db.update_acl_in_room_for_action,
                          BaseTest.CHANNEL_ID, BaseTest.ROOM_ID, ApiActions.JOIN, 'age', '25:40')

    def _test_update_acl_in_room_for_action_no_room(self):
        self._create_channel()
        self.assertRaises(NoSuchRoomException, self.db.update_acl_in_room_for_action,
                          BaseTest.CHANNEL_ID, BaseTest.ROOM_ID, ApiActions.JOIN, 'age', '25:40')

    def _test_update_acl_in_room_for_action_invalid_action(self):
        self._create_channel()
        self._create_room()
        self.assertRaises(InvalidApiActionException, self.db.update_acl_in_room_for_action,
                          BaseTest.CHANNEL_ID, BaseTest.ROOM_ID, 'some-invalid-action', 'age', '25:40')

    def _test_update_acl_in_room_for_action_invalid_type(self):
        self._create_channel()
        self._create_room()
        self.assertRaises(InvalidAclTypeException, self.db.update_acl_in_room_for_action,
                          BaseTest.CHANNEL_ID, BaseTest.ROOM_ID, ApiActions.JOIN, 'something-invalid', '25:40')

    def _test_update_acl_in_room_for_action_invalid_value(self):
        self._create_channel()
        self._create_room()
        self.assertRaises(InvalidAclValueException, self.db.update_acl_in_room_for_action,
                          BaseTest.CHANNEL_ID, BaseTest.ROOM_ID, ApiActions.JOIN, 'age', 'something-invalid')

    def _test_update_acl_in_room_for_action(self):
        self._create_channel()
        self._create_room()
        self.assertEqual(0, len(self.db.get_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.JOIN)))

        self.db.update_acl_in_room_for_action(BaseTest.CHANNEL_ID, BaseTest.ROOM_ID, ApiActions.JOIN, 'age', '25:40')
        self.assertIn('age', self.db.get_acls_in_room_for_action(BaseTest.ROOM_ID, ApiActions.JOIN))

    def _test_update_acl_in_channel_for_action(self):
        self._create_channel()
        self.assertEqual(0, len(self.db.get_acls_in_channel_for_action(BaseTest.CHANNEL_ID, ApiActions.LIST)))

        self.db.update_acl_in_channel_for_action(BaseTest.CHANNEL_ID, ApiActions.LIST, 'age', '25:40')
        self.assertIn('age', self.db.get_acls_in_channel_for_action(BaseTest.CHANNEL_ID, ApiActions.LIST))

    def _test_update_acl_in_channel_for_action_invalid_action(self):
        self._create_channel()
        self.assertRaises(InvalidApiActionException, self.db.update_acl_in_channel_for_action,
                          BaseTest.CHANNEL_ID, 'some-invalid-action', 'age', '25:40')

    def _test_update_acl_in_channel_for_action_invalid_type(self):
        self._create_channel()
        self.assertRaises(InvalidAclTypeException, self.db.update_acl_in_channel_for_action,
                          BaseTest.CHANNEL_ID, ApiActions.LIST, 'something-invalid', '25:40')

    def _test_update_acl_in_channel_for_action_invalid_value(self):
        self._create_channel()
        self.assertRaises(InvalidAclValueException, self.db.update_acl_in_channel_for_action,
                          BaseTest.CHANNEL_ID, ApiActions.LIST, 'age', 'something-invalid')

    def _test_update_acl_in_channel_for_action_no_channel(self):
        self.assertRaises(NoSuchChannelException, self.db.update_acl_in_channel_for_action,
                          BaseTest.CHANNEL_ID, ApiActions.LIST, 'age', '25:40')

    def _test_is_banned_from_channel(self):
        self._create_channel()
        is_banned, time_left = self.db.is_banned_from_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.assertFalse(is_banned)

        timestamp = str(int((datetime.now() + timedelta(minutes=5)).timestamp()))
        duration = '5m'

        self.db.ban_user_channel(BaseTest.USER_ID, timestamp, duration, BaseTest.CHANNEL_ID)
        is_banned, time_left = self.db.is_banned_from_channel(BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.assertTrue(is_banned)
