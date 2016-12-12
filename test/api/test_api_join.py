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
from activitystreams import parse as as_parser

from dino import api
from dino.config import RedisKeys
from dino.config import ApiActions
from dino.utils import b64d


class ApiJoinTest(BaseTest):
    def setUp(self):
        super(ApiJoinTest, self).setUp()
        self.create_channel_and_room()

    def test_join_non_owner_no_acl(self):
        self.assert_join_succeeds()

    def test_join_owner_no_acl(self):
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_non_owner_correct_country(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk'}})
        self.assert_join_succeeds()

    def test_join_non_owner_with_all_acls(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {
            'country': 'de,cn,dk',
            'city': 'Beijing,Shanghai,Berlin,Copenhagen',
            'age': '18:45',
            'gender': 'm,f',
            'membership': '0,1',
            'has_webcam': 'y',
            'fake_checked': 'y,n',
            'image': 'y'
        }})
        self.assert_join_succeeds()

    def test_join_owner_with_all_acls(self):
        self.set_owner()
        self.set_acl({ApiActions.JOIN: {
            'country': 'de,cn,dk',
            'city': 'Beijing,Shanghai,Berlin,Copenhagen',
            'age': '18:45',
            'gender': 'm,f',
            'membership': '0,1',
            'has_webcam': 'y',
            'fake_checked': 'y,n',
            'image': 'n'
        }})
        self.assert_join_succeeds()

    def test_join_returns_activity_with_4_attachments(self):
        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        self.assertEqual(4, len(response[1]['object']['attachments']))

    def test_join_returns_activity_with_acl_attachment(self):
        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        acls = self.get_attachment_for_key(attachments, 'acl')
        self.assertIsNotNone(acls)

    def test_join_returns_activity_with_history_attachment(self):
        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        history = self.get_attachment_for_key(attachments, 'history')
        self.assertIsNotNone(history)

    def test_join_returns_activity_with_owner_attachment(self):
        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        owners = self.get_attachment_for_key(attachments, 'owner')
        self.assertIsNotNone(owners)

    def test_join_returns_activity_with_users_attachment(self):
        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        users = self.get_attachment_for_key(attachments, 'user')
        self.assertIsNotNone(users)

    def test_join_returns_activity_with_empty_acl_attachment(self):
        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        self.assert_attachment_equals(attachments, 'acl', [])

    def test_join_returns_activity_with_empty_history_attachment(self):
        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        self.assert_attachment_equals(attachments, 'history', [])

    def test_join_returns_activity_with_empty_owner_attachment(self):
        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        self.assert_attachment_equals(attachments, 'owner', [])

    def test_join_returns_activity_with_one_user_as_attachment(self):
        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        users = self.get_attachment_for_key(attachments, 'user')
        self.assertEqual(0, len(users))

        act = self.activity_for_join()
        act['actor']['id'] = '9876'
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        users = self.get_attachment_for_key(attachments, 'user')
        self.assertEqual(1, len(users))

    def test_join_returns_activity_with_one_owner(self):
        self.set_owner()
        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        owners = self.get_attachment_for_key(attachments, 'owner')
        self.assertEqual(1, len(owners))

    def test_join_returns_activity_with_correct_owner(self):
        self.set_owner()
        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        owners = self.get_attachment_for_key(attachments, 'owner')
        user_id, user_name = owners[0]['id'], owners[0]['content']
        self.assertEqual(ApiJoinTest.USER_ID, user_id)
        self.assertEqual(ApiJoinTest.USER_NAME, b64d(user_name))

    def test_join_returns_correct_nr_of_acls(self):
        correct_acls = {ApiActions.JOIN: {'country': 'de,cn,dk', 'city': 'Shanghai,Berlin,Copenhagen'}}
        self.set_acl(correct_acls)
        self.set_owner()
        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        returned_acls = self.get_attachment_for_key(attachments, 'acl')
        self.assertEqual(len(correct_acls.get(ApiActions.JOIN)), len(returned_acls))

    def test_join_returns_correct_acls(self):
        correct_acls = {ApiActions.JOIN: {'country': 'de,cn,dk', 'city': 'Shanghai,Berlin,Copenhagen'}}
        self.set_acl(correct_acls)
        self.set_owner()
        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        returned_acls = self.get_attachment_for_key(attachments, 'acl')
        for acl in returned_acls:
            acl_key = acl['objectType']
            acl_value = acl['content']
            self.assertTrue(acl_key in correct_acls.get(ApiActions.JOIN))
            self.assertEqual(correct_acls.get(ApiActions.JOIN)[acl_key], acl_value)

    def test_join_returns_history(self):
        msg = 'this is a test message'
        self.set_owner()
        self.assert_join_succeeds()
        self.send_message(msg)
        self.assert_in_room(True)
        self.leave_room()
        self.assert_in_room(False)

        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        returned_history = self.get_attachment_for_key(attachments, 'history')
        self.assertEqual(1, len(returned_history))

    def test_join_returns_correct_history(self):
        msg = 'this is a test message'
        self.set_owner()
        self.assert_join_succeeds()
        msg_response = self.send_message(msg)[1]
        self.leave_room()

        act = self.activity_for_join()
        response = api.on_join(act, as_parser(act))
        attachments = response[1]['object']['attachments']
        history_obj = self.get_attachment_for_key(attachments, 'history')[0]

        self.assertEqual(msg_response['id'], history_obj['id'])
        self.assertEqual(msg, b64d(history_obj['content']))
        self.assertEqual(msg_response['published'], history_obj['published'])
        self.assertEqual(ApiJoinTest.USER_NAME, b64d(history_obj['summary']))

    def assert_attachment_equals(self, attachments, key, value):
        found = self.get_attachment_for_key(attachments, key)
        self.assertEqual(value, found)

    def get_attachment_for_key(self, attachments, key):
        for attachment in attachments:
            if attachment['objectType'] == key:
                return attachment['attachments']
        return None
