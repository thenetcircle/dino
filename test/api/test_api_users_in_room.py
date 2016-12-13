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
from dino.utils import b64d


class ApiUsersInRoomTest(BaseTest):
    def test_users_in_room_status_code_200(self):
        self.create_channel_and_room()
        self.assert_in_room(False)
        act = self.activity_for_join()
        api.on_join(act, as_parser(act))
        self.assert_in_room(True)

        act = self.activity_for_users_in_room()
        response_data = api.on_users_in_room(act, as_parser(act))
        self.assertEqual(200, response_data[0])

    def test_users_in_room_is_only_one(self):
        self.assert_in_room(False)
        act = self.activity_for_join()
        api.on_join(act, as_parser(act))
        self.assert_in_room(True)

        act = self.activity_for_users_in_room()
        response_data = api.on_users_in_room(act, as_parser(act))
        self.assertEqual(1, len(response_data[1]['object']['attachments']))

    def test_users_in_room_is_correct_id(self):
        self.assert_in_room(False)
        act = self.activity_for_join()
        api.on_join(act, as_parser(act))
        self.assert_in_room(True)

        act = self.activity_for_users_in_room()
        response_data = api.on_users_in_room(act, as_parser(act))
        self.assertEqual(
                self.env.db.get_private_room(BaseTest.USER_ID)[0],
                response_data[1]['object']['attachments'][0]['id'])

    def test_users_in_room_is_correct_name(self):
        self.assert_in_room(False)
        act = self.activity_for_join()
        api.on_join(act, as_parser(act))
        self.assert_in_room(True)

        act = self.activity_for_users_in_room()
        response_data = api.on_users_in_room(act, as_parser(act))
        self.assertEqual(
                ApiUsersInRoomTest.USER_NAME,
                b64d(response_data[1]['object']['attachments'][0]['displayName']))

    def test_users_in_room_status_code_200_when_empty(self):
        self.assert_in_room(False)
        act = self.activity_for_users_in_room()
        response_data = api.on_users_in_room(act, as_parser(act))
        self.assertEqual(200, response_data[0])

    def test_users_in_room_attachments_empty_when_no_user_in_room(self):
        self.assert_in_room(False)
        act = self.activity_for_users_in_room()
        response_data = api.on_users_in_room(act, as_parser(act))
        self.assertEqual(0, len(response_data[1]['object']['attachments']))

    def assert_leave_succeeds(self):
        self.assertEqual(200, self.response_code_for_leave())

    def response_code_for_leave(self, data=None):
        return self.leave_room(data)[0]
