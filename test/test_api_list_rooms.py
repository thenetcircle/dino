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

from dino import api
from dino.utils import b64d


class ApiListRoomsTest(BaseTest):
    def test_list_rooms_status_code_200(self):
        self.assert_in_room(False)
        self.create_and_join_room()
        self.assert_in_room(True)

        response_data = api.on_list_rooms(self.activity_for_list_rooms())
        self.assertEqual(200, response_data[0])

    def test_list_rooms_no_actor_id_status_code_400(self):
        self.assert_in_room(False)
        self.create_and_join_room()
        self.assert_in_room(True)

        activity = self.activity_for_list_rooms()
        del activity['actor']['id']
        response_data = api.on_list_rooms(activity)
        self.assertEqual(400, response_data[0])

    def test_list_rooms_only_one(self):
        self.assert_in_room(False)
        self.create_and_join_room()
        self.assert_in_room(True)

        response_data = api.on_list_rooms(self.activity_for_list_rooms())
        self.assertEqual(1, len(response_data[1]['object']['attachments']))

    def test_list_rooms_correct_id(self):
        self.assert_in_room(False)
        self.create_and_join_room()
        self.assert_in_room(True)

        response_data = api.on_list_rooms(self.activity_for_list_rooms())
        self.assertEqual(ApiListRoomsTest.ROOM_ID, response_data[1]['object']['attachments'][0]['id'])

    def test_list_rooms_correct_name(self):
        self.assert_in_room(False)
        self.create_and_join_room()
        self.assert_in_room(True)

        response_data = api.on_list_rooms(self.activity_for_list_rooms())
        self.assertEqual(
                ApiListRoomsTest.ROOM_NAME,
                b64d(response_data[1]['object']['attachments'][0]['content']))

    def test_list_rooms_status_code_200_if_no_rooms(self):
        self.assert_in_room(False)
        response_data = api.on_list_rooms(self.activity_for_list_rooms())
        self.assertEqual(200, response_data[0])

    def test_list_rooms_attachments_empty_if_no_rooms(self):
        self.assert_in_room(False)
        response_data = api.on_list_rooms(self.activity_for_list_rooms())
        self.assertEqual(0, len(response_data[1]['object']['attachments']))
