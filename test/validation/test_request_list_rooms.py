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

from dino.validation import request
from dino.utils import b64d


class RequestListRoomsTest(BaseTest):
    def test_list_rooms_status_code_true(self):
        self.assert_in_room(False)
        self.create_and_join_room()
        self.assert_in_room(True)

        response_data = request.on_list_rooms(as_parser(self.activity_for_list_rooms()))
        self.assertEqual(True, response_data[0])

    def test_list_rooms_no_actor_id_status_code_false(self):
        self.assert_in_room(False)
        self.create_and_join_room()
        self.assert_in_room(True)

        activity = self.activity_for_list_rooms()
        del activity['actor']['id']
        response_data = request.on_list_rooms(as_parser(activity))
        self.assertEqual(True, response_data[0])

    def test_list_rooms_no_channel_id_status_code_false(self):
        self.assert_in_room(False)
        activity = self.activity_for_list_rooms()
        del activity['object']['url']
        response_data = request.on_list_rooms(as_parser(activity))
        self.assertEqual(False, response_data[0])

    def test_list_rooms_status_code_true_if_no_rooms(self):
        self.assert_in_room(False)
        response_data = request.on_list_rooms(as_parser(self.activity_for_list_rooms()))
        self.assertEqual(True, response_data[0])
