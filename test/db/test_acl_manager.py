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

from dino.db.manager.acls import AclManager
from dino.config import ApiActions
from dino.utils import b64d
from dino import validation

from test.db import BaseDatabaseTest

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class AclManagerTest(BaseDatabaseTest):
    _act = None

    @staticmethod
    def _publish(activity: dict) -> None:
        AclManagerTest._act = activity

    def setUp(self):
        self.set_up_env('redis')
        self.env.publish = AclManagerTest._publish
        self._act = None
        self.env.db = self.db
        self.manager = AclManager(self.env)

    def tearDown(self):
        self.db.redis.flushall()
        self.env.cache._flushall()

    """
    def get_acl_actions(self, channel_or_room):
        acl = self.env.config.get(ConfigKeys.ACL)
        return [action for action in acl.get(channel_or_room, [])]

    def get_acl_types_for_action(self, channel_or_room, action):
        acl = self.env.config.get(ConfigKeys.ACL)
        return [
            acl_type for acl_type in
            acl.get(channel_or_room, dict()).get(action, dict()).get('acls', [])
        ]
    """

    def test_get_acl_actions_room(self):
        actual = self.manager.get_acl_actions('room')
        expected = ['join', 'message', 'history', 'crossroom']

        actual.sort()
        expected.sort()
        self.assertEqual(actual, expected)

    def test_get_acl_actions_channel(self):
        actual = self.manager.get_acl_actions('channel')
        expected = ['message', 'list', 'crossroom']

        actual.sort()
        expected.sort()
        self.assertEqual(actual, expected)

    def test_get_acl_actions_invalid(self):
        self.assertEqual(len(self.manager.get_acl_actions('invalid')), 0)

    def test_get_acl_types_for_action(self):
        actual = self.manager.get_acl_types_for_action('room', 'join')
        expected = [
            'age', 'gender', 'membership', 'group', 'country',
            'city', 'image', 'has_webcam', 'fake_checked',
            'owner', 'admin', 'moderator', 'superuser', 'crossroom',
            'samechannel', 'sameroom', 'disallow'
        ]

        actual.sort()
        expected.sort()
        self.assertEqual(actual, expected)

    def test_get_acl_validation(self):
        expected = 'str_in_csv'
        self.assertEqual(self.manager.get_validation_for_type('gender'), expected)

    def test_validate_correct_gender(self):
        is_valid, _ = validation.acl.is_acl_valid('gender', 'm')
        self.assertTrue(is_valid)

    def test_validate_incorrect_gender(self):
        is_valid, _ = validation.acl.is_acl_valid('gender', '9')
        self.assertFalse(is_valid)

    def test_get_acl_types_for_invalid_action(self):
        self.assertEqual(len(self.manager.get_acl_types_for_action('room', 'invalid')), 0)

    def test_get_acls_channel_empty(self):
        self._create_channel()
        acls = self.manager.get_acls_channel(BaseDatabaseTest.CHANNEL_ID)
        self.assertEqual(0, len(acls))

    def test_get_acls_channel(self):
        self._create_channel()
        self.manager.add_acl_channel(BaseDatabaseTest.CHANNEL_ID, ApiActions.LIST, 'age', '25:45')
        acls = self.manager.get_acls_channel(BaseDatabaseTest.CHANNEL_ID)
        self.assertEqual(1, len(acls))
        self.assertEqual('age', acls[0]['type'])
        self.assertEqual('25:45', b64d(acls[0]['value']))
        self.assertEqual(ApiActions.LIST, acls[0]['action'])

    def test_update_acls_channel(self):
        self._create_channel()
        self._create_room()
        self.manager.add_acl_channel(BaseDatabaseTest.CHANNEL_ID, ApiActions.LIST, 'age', '25:45')
        acls = self.manager.get_acls_channel(BaseDatabaseTest.CHANNEL_ID)
        self.assertEqual(1, len(acls))
        self.assertEqual('age', acls[0]['type'])
        self.assertEqual('25:45', b64d(acls[0]['value']))
        self.assertEqual(ApiActions.LIST, acls[0]['action'])

        self.manager.update_channel_acl(BaseDatabaseTest.CHANNEL_ID, ApiActions.LIST, 'age', '20:40')

        acls = self.manager.get_acls_channel(BaseDatabaseTest.CHANNEL_ID)
        self.assertEqual(1, len(acls))
        self.assertEqual('age', acls[0]['type'])
        self.assertEqual('20:40', b64d(acls[0]['value']))
        self.assertEqual(ApiActions.LIST, acls[0]['action'])

    def test_delete_acls_channel(self):
        self._create_channel()
        self.manager.add_acl_channel(BaseDatabaseTest.CHANNEL_ID, ApiActions.LIST, 'age', '25:45')
        acls = self.manager.get_acls_channel(BaseDatabaseTest.CHANNEL_ID)
        self.assertEqual(1, len(acls))
        self.manager.delete_acl_channel(BaseDatabaseTest.CHANNEL_ID, ApiActions.LIST, 'age')
        acls = self.manager.get_acls_channel(BaseDatabaseTest.CHANNEL_ID)
        self.assertEqual(0, len(acls))

    def test_get_acls_room_empty(self):
        self._create_channel()
        self._create_room()
        acls = self.manager.get_acls_room(BaseDatabaseTest.ROOM_ID)
        self.assertEqual(0, len(acls))

    def test_get_acls_room(self):
        self._create_channel()
        self._create_room()
        self.manager.add_acl_room(BaseDatabaseTest.ROOM_ID, ApiActions.JOIN, 'age', '25:45')
        acls = self.manager.get_acls_room(BaseDatabaseTest.ROOM_ID)
        self.assertEqual(1, len(acls))
        self.assertEqual('age', acls[0]['type'])
        self.assertEqual('25:45', b64d(acls[0]['value']))
        self.assertEqual(ApiActions.JOIN, acls[0]['action'])

    def test_update_acls_room(self):
        self._create_channel()
        self._create_room()
        self.manager.add_acl_room(BaseDatabaseTest.ROOM_ID, ApiActions.JOIN, 'age', '25:45')
        acls = self.manager.get_acls_room(BaseDatabaseTest.ROOM_ID)
        self.assertEqual(1, len(acls))
        self.assertEqual('age', acls[0]['type'])
        self.assertEqual('25:45', b64d(acls[0]['value']))
        self.assertEqual(ApiActions.JOIN, acls[0]['action'])

        self.manager.update_room_acl(
                BaseDatabaseTest.CHANNEL_ID, BaseDatabaseTest.ROOM_ID, ApiActions.JOIN, 'age', '20:40')

        acls = self.manager.get_acls_room(BaseDatabaseTest.ROOM_ID)
        self.assertEqual(1, len(acls))
        self.assertEqual('age', acls[0]['type'])
        self.assertEqual('20:40', b64d(acls[0]['value']))
        self.assertEqual(ApiActions.JOIN, acls[0]['action'])

    def test_delete_acls_room(self):
        self._create_channel()
        self._create_room()
        self.manager.add_acl_room(BaseDatabaseTest.ROOM_ID, ApiActions.JOIN, 'age', '25:45')
        acls = self.manager.get_acls_room(BaseDatabaseTest.ROOM_ID)
        self.assertEqual(1, len(acls))
        self.manager.delete_acl_room(BaseDatabaseTest.ROOM_ID, ApiActions.JOIN, 'age')
        acls = self.manager.get_acls_room(BaseDatabaseTest.ROOM_ID)
        self.assertEqual(0, len(acls))
