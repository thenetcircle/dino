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


from test.utils import BaseTest
from activitystreams import parse as as_parser
from strict_rfc3339 import validate_rfc3339 as validate_timestamp

from dino import api
from dino.utils import b64d


class ApiHistoryTest(BaseTest):
    def setUp(self):
        super(ApiHistoryTest, self).setUp()
        self.create_channel_and_room()

    def test_history(self):
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(200, response_data[0])

    def test_history_no_actor_id(self):
        response_data = api.on_history(self.activity_for_history(skip={'user_id'}))
        self.assertEqual(400, response_data[0])

    def test_history_no_target_id(self):
        response_data = api.on_history(self.activity_for_history(skip={'target_id'}))
        self.assertEqual(400, response_data[0])

    def test_history_not_allowed_not_owner_not_in_room_age(self):
        self.leave_room()
        self.remove_owner()
        self.remove_owner_channel()
        self.set_acl_single('history|age', str(int(BaseTest.AGE) + 10) + ':')
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(400, response_data[0])

    def test_history_not_allowed_not_owner_in_room(self):
        self.join_room()
        self.remove_owner()
        self.remove_owner_channel()
        self.set_acl_single('history|age', str(int(BaseTest.AGE) + 10) + ':')
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(400, response_data[0])

    def test_history_allowed_owner_not_in_room(self):
        self.leave_room()
        self.set_owner()
        self.set_acl_single('history|sameroom', '')
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(200, response_data[0])

    def test_history_not_allowed_not_owner_not_in_room_sameroom(self):
        self.leave_room()
        self.remove_owner()
        self.remove_owner_channel()
        self.set_acl_single('history|sameroom', '')
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(400, response_data[0])

    def test_history_not_allowed_owner_in_room(self):
        self.join_room()
        self.set_owner()
        self.set_acl_single('history|age', str(int(BaseTest.AGE) + 10) + ':')
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(200, response_data[0])

    def test_history_allowed_not_owner_not_in_room(self):
        self.leave_room()
        self.remove_owner()
        self.remove_owner_channel()
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(200, response_data[0])

    def test_history_allowed_not_owner_in_room(self):
        self.join_room()
        self.remove_owner()
        self.remove_owner_channel()
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(200, response_data[0])

    def test_history_allowed_owner_in_room(self):
        self.join_room()
        self.set_owner()
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(200, response_data[0])

    def test_history_contains_one_sent_message(self):
        self.join_room()
        self.remove_owner()
        self.remove_owner_channel()

        message = 'my message'
        self.send_message(message)

        response_data = api.on_history(self.activity_for_history())
        activity = as_parser(response_data[1])
        self.assertEqual(1, len(activity.object.attachments))

    def test_history_contains_two_sent_message(self):
        self.join_room()
        self.remove_owner()
        self.remove_owner_channel()

        message = 'my message'
        self.send_message(message)
        self.send_message(message)

        response_data = api.on_history(self.activity_for_history())
        activity = as_parser(response_data[1])
        self.assertEqual(2, len(activity.object.attachments))

    def test_history_contains_correct_sent_message(self):
        self.join_room()
        self.remove_owner()
        self.remove_owner_channel()

        message = 'my message'
        self.send_message(message)

        response_data = api.on_history(self.activity_for_history())
        activity = as_parser(response_data[1])
        self.assertEqual(message, b64d(activity.object.attachments[0].content))

    def test_history_contains_timestamp(self):
        self.join_room()
        self.remove_owner()
        self.remove_owner_channel()
        self.send_message('my message')

        response_data = api.on_history(self.activity_for_history())
        activity = as_parser(response_data[1])
        self.assertIsNotNone(activity.object.attachments[0].published)

    def test_history_contains_id(self):
        self.join_room()
        self.remove_owner()
        self.remove_owner_channel()
        self.send_message('my message')

        response_data = api.on_history(self.activity_for_history())
        activity = as_parser(response_data[1])
        self.assertIsNotNone(activity.object.attachments[0].id)

    def test_history_contains_correct_user_name(self):
        self.join_room()
        self.remove_owner()
        self.remove_owner_channel()
        self.send_message('my message')

        response_data = api.on_history(self.activity_for_history())
        activity = as_parser(response_data[1])
        self.assertEqual(BaseTest.USER_NAME, b64d(activity.object.attachments[0].summary))

    def test_history_contains_valid_timestamp(self):
        self.join_room()
        self.remove_owner()
        self.remove_owner_channel()
        self.send_message('my message')

        response_data = api.on_history(self.activity_for_history())
        activity = as_parser(response_data[1])
        self.assertTrue(validate_timestamp(activity.object.attachments[0].published))

    def test_history_since_last_time_stamp(self):
        self.join_room()
        self.send_message('a message')
        # TODO: modify timestamp of message so we can check for messages after this one
        self.send_message('a message')
