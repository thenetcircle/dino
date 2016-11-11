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

from dino import api
from dino.validation import request


class RequestUsersInRoomTest(BaseTest):
    def test_users_in_room_status_code_true(self):
        self.create_channel_and_room()
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        response_data = request.on_users_in_room(as_parser(self.activity_for_users_in_room()))
        self.assertEqual(True, response_data[0])

    def test_users_in_room_no_room_id(self):
        self.create_channel_and_room()
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        act = self.activity_for_users_in_room()
        del act['actor']['id']
        response_data = request.on_users_in_room(as_parser(act))
        self.assertEqual(True, response_data[0])

    def test_users_in_room_missing_actor_id_status_code_true(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        activity = self.activity_for_users_in_room()
        del activity['actor']['id']
        response_data = request.on_users_in_room(activity)
        self.assertEqual(True, response_data[0])

    def test_users_in_room_status_code_True_when_empty(self):
        self.assert_in_room(False)
        response_data = request.on_users_in_room(as_parser(self.activity_for_users_in_room()))
        self.assertEqual(True, response_data[0])

    def assert_leave_succeeds(self):
        self.assertEqual(True, self.response_code_for_leave())

    def response_code_for_leave(self, data=None):
        return self.leave_room(data)[0]
