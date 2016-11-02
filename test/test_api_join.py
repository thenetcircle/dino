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

from dino import api
from dino.config import ApiActions
from test.utils import BaseTest


class ApiJoinTest(BaseTest):
    def setUp(self):
        super(ApiJoinTest, self).setUp()
        self.create_channel_and_room()

    def test_join_non_owner_no_acl(self):
        self.assert_join_succeeds()

    def test_join_missing_actor_id_fails(self):
        activity = self.activity_for_join()
        del activity['actor']['id']
        response = api.on_join(activity)
        self.assertEqual(400, response[0])

    def test_join_owner_no_acl(self):
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_owner_ignores_acl(self):
        self.set_owner()
        self.set_acl({ApiActions.JOIN: {'age': '18:25'}})
        self.assert_join_succeeds()

    def test_join_non_owner_too_young(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'age': '35:40'}})
        self.assert_join_fails()

    def test_join_non_owner_too_old(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'age': '18:25'}})
        self.assert_join_fails()

    def test_join_non_owner_in_age_range(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'age': '18:40'}})
        self.assert_join_succeeds()

    def test_join_non_owner_wrong_gender(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'gender': 'ts,m'}})
        self.assert_join_fails()

    def test_join_non_owner_wrong_membership(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'membership': '1,2'}})
        self.assert_join_fails()

    def test_join_non_owner_correct_membership(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'membership': '0,1,2'}})
        self.assert_join_succeeds()

    def test_join_non_owner_no_image(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'image': 'n'}})
        self.assert_join_fails()

    def test_join_non_owner_has_image(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'image': 'y'}})
        self.assert_join_succeeds()

    def test_join_non_owner_fake_checkede(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'fake_checked': 'y'}})
        self.assert_join_fails()

    def test_join_non_owner_not_fake_checked(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'fake_checked': 'n'}})
        self.assert_join_succeeds()

    def test_join_non_owner_webcam(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'has_webcam': 'y'}})
        self.assertEqual(200, self.response_code_for_joining())
        self.assert_in_room(True)

    def test_join_non_owner_no_webcam(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'has_webcam': 'n'}})
        self.assert_join_fails()

    def test_join_non_owner_invalid_acl(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'unknown_acl': 'asdf'}})
        self.assert_join_succeeds()

    def test_join_owner_invalid_acl(self):
        self.set_acl({ApiActions.JOIN: {'unknown_acl': 'asdf'}})
        self.assert_join_succeeds()

    def test_join_owner_wrong_country(self):
        self.set_acl({ApiActions.JOIN: {'country': 'de,dk'}})
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_non_owner_wrong_country(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'country': 'de,dk'}})
        self.assert_join_fails()

    def test_join_non_owner_correct_country(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk'}})
        self.assert_join_succeeds()

    def test_join_owner_correct_country(self):
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk'}})
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_owner_correct_city(self):
        self.set_acl({ApiActions.JOIN: {'city': 'Shanghai,Berlin,Copenhagen'}})
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_non_owner_correct_city(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'city': 'Shanghai,Berlin,Copenhagen'}})
        self.assert_join_succeeds()

    def test_join_owner_wrong_city(self):
        self.set_acl({ApiActions.JOIN: {'city': 'Berlin,Copenhagen'}})
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_non_owner_wrong_city(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'city': 'Berlin,Copenhagen'}})
        self.assert_join_fails()

    def test_join_owner_correct_country_and_city(self):
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk', 'city': 'Shanghai,Berlin,Copenhagen'}})
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_owner_correct_country_wrong_city(self):
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk', 'city': 'Beijing,Berlin,Copenhagen'}})
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_owner_wrong_country_correct_city(self):
        # stupid test, but what the hell; should not be able to set a city in a country that's not allowed anyway
        self.set_acl({ApiActions.JOIN: {'country': 'de,dk', 'city': 'Beijing,Berlin,Copenhagen'}})
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_non_owner_correct_country_and_city(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk', 'city': 'Shanghai,Berlin,Copenhagen'}})
        self.assert_join_succeeds()

    def test_join_non_owner_correct_country_wrong_city(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk', 'city': 'Beijing,Berlin,Copenhagen'}})
        self.assert_join_fails()

    def test_join_non_owner_wrong_country_correct_city(self):
        self.remove_owner_channel()
        self.remove_owner()
        # stupid test, but what the hell; should not be able to set a city in a country that's not allowed anyway
        self.set_acl({ApiActions.JOIN: {'country': 'de,dk', 'city': 'Beijing,Berlin,Copenhagen'}})
        self.assert_join_fails()

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

    def test_join_non_owner_with_all_acls_one_incorrect(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {
            'country': 'de,cn,dk',
            'city': 'Beijing,Shanghai,Berlin,Copenhagen',
            'age': '18:45',
            'gender': 'm,f',
            'membership': '0,1',
            'has_webcam': 'y',  # the test user has a webcam, everything else checks out
            'fake_checked': 'y,n',
            'image': 'n'
        }})
        self.assert_join_fails()

    def test_join_non_owner_with_all_acls_one_missing(self):
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
            'image': 'n'
        }})
        self.set_session('has_webcam', None)
        self.assert_join_fails()

    def test_join_invalid_acl_in_redis(self):
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk'}})
        invalid_key = 'invalid|stuff'
        self.set_session(invalid_key, 't')
        self.set_acl_single(invalid_key, 't,r,e,w')
        self.assert_join_succeeds()

    def test_join_owner_with_all_acls_one_incorrect(self):
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
        response = api.on_join(self.activity_for_join())
        self.assertEqual(4, len(response[1]['object']['attachments']))

    def test_join_returns_activity_with_acl_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        acls = self.get_attachment_for_key(attachments, 'acl')
        self.assertIsNotNone(acls)

    def test_join_returns_activity_with_history_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        history = self.get_attachment_for_key(attachments, 'history')
        self.assertIsNotNone(history)

    def test_join_returns_activity_with_owner_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        owners = self.get_attachment_for_key(attachments, 'owner')
        self.assertIsNotNone(owners)

    def test_join_returns_activity_with_users_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        users = self.get_attachment_for_key(attachments, 'user')
        self.assertIsNotNone(users)

    def test_join_returns_activity_with_empty_acl_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        self.assert_attachment_equals(attachments, 'acl', [])

    def test_join_returns_activity_with_empty_history_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        self.assert_attachment_equals(attachments, 'history', [])

    def test_join_returns_activity_with_empty_owner_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        self.assert_attachment_equals(attachments, 'owner', [])

    def test_join_returns_activity_with_one_user_as_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        users = self.get_attachment_for_key(attachments, 'user')
        self.assertEqual(1, len(users))

    def test_join_returns_activity_with_this_user_as_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        user = self.get_attachment_for_key(attachments, 'user')[0]
        self.assertEqual(ApiJoinTest.USER_ID, user['id'])
        self.assertEqual(ApiJoinTest.USER_NAME, user['content'])

    def test_join_returns_activity_with_one_owner(self):
        self.set_owner()
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        owners = self.get_attachment_for_key(attachments, 'owner')
        self.assertEqual(1, len(owners))

    def test_join_returns_activity_with_correct_owner(self):
        self.set_owner()
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        owners = self.get_attachment_for_key(attachments, 'owner')
        user_id, user_name = owners[0]['id'], owners[0]['content']
        self.assertEqual(ApiJoinTest.USER_ID, user_id)
        self.assertEqual(ApiJoinTest.USER_NAME, user_name)

    def test_join_returns_correct_nr_of_acls(self):
        correct_acls = {ApiActions.JOIN: {'country': 'de,cn,dk', 'city': 'Shanghai,Berlin,Copenhagen'}}
        self.set_acl(correct_acls)
        self.set_owner()
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        returned_acls = self.get_attachment_for_key(attachments, 'acl')
        self.assertEqual(len(correct_acls), len(returned_acls))

    def test_join_returns_correct_acls(self):
        correct_acls = {ApiActions.JOIN: {'country': 'de,cn,dk', 'city': 'Shanghai,Berlin,Copenhagen'}}
        self.set_acl(correct_acls)
        self.set_owner()
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        returned_acls = self.get_attachment_for_key(attachments, 'acl')
        for acl in returned_acls:
            acl_key = acl['objectType']
            acl_value = acl['content']
            self.assertTrue(acl_key in correct_acls)
            self.assertEqual(correct_acls[acl_key], acl_value)

    def test_join_returns_history(self):
        msg = 'this is a test message'
        self.set_owner()
        self.assert_join_succeeds()
        self.send_message(msg)
        self.assert_in_room(True)
        self.leave_room()
        self.assert_in_room(False)

        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        returned_history = self.get_attachment_for_key(attachments, 'history')
        self.assertEqual(1, len(returned_history))

    def test_join_returns_correct_history(self):
        msg = 'this is a test message'
        self.set_owner()
        self.assert_join_succeeds()
        msg_response = self.send_message(msg)[1]
        self.leave_room()

        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        history_obj = self.get_attachment_for_key(attachments, 'history')[0]

        self.assertEqual(msg_response['id'], history_obj['id'])
        self.assertEqual(msg, history_obj['content'])
        self.assertEqual(msg_response['published'], history_obj['published'])
        self.assertEqual(ApiJoinTest.USER_NAME, history_obj['summary'])

    def assert_attachment_equals(self, attachments, key, value):
        found = self.get_attachment_for_key(attachments, key)
        self.assertEqual(value, found)

    def get_attachment_for_key(self, attachments, key):
        for attachment in attachments:
            if attachment['objectType'] == key:
                return attachment['attachments']
        return None
