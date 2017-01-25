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

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

from test.base import BaseTest
from activitystreams import parse as as_parser

from dino import api
from dino.utils import b64d


class ApiListRoomsTest(BaseTest):
    def test_list_rooms_status_code_200(self):
        self.assert_in_room(False)
        self.create_and_join_room()
        self.assert_in_room(True)

        act = self.activity_for_list_rooms()
        response_data = api.on_list_rooms(act, as_parser(act))
        self.assertEqual(200, response_data[0])

    def test_list_rooms_only_one(self):
        self.assert_in_room(False)
        self.create_and_join_room()
        self.assert_in_room(True)

        act = self.activity_for_list_rooms()
        response_data = api.on_list_rooms(act, as_parser(act))
        from pprint import pprint
        pprint(response_data)
        self.assertEqual(1, len(response_data[1]['object']['attachments']))

    def test_list_rooms_correct_id(self):
        self.assert_in_room(False)
        self.create_and_join_room()
        self.assert_in_room(True)

        act = self.activity_for_list_rooms()
        response_data = api.on_list_rooms(act, as_parser(act))
        self.assertEqual(ApiListRoomsTest.ROOM_ID, response_data[1]['object']['attachments'][0]['id'])

    def test_list_rooms_correct_name(self):
        self.assert_in_room(False)
        self.create_and_join_room()
        self.assert_in_room(True)

        act = self.activity_for_list_rooms()
        response_data = api.on_list_rooms(act, as_parser(act))
        self.assertEqual(
                ApiListRoomsTest.ROOM_NAME,
                b64d(response_data[1]['object']['attachments'][0]['displayName']))

    def test_list_rooms_status_code_200_if_no_rooms(self):
        self.assert_in_room(False)
        act = self.activity_for_list_rooms()
        response_data = api.on_list_rooms(act, as_parser(act))
        self.assertEqual(200, response_data[0])

    def test_list_rooms_attachments_empty_if_no_rooms(self):
        self.assert_in_room(False)
        act = self.activity_for_list_rooms()
        response_data = api.on_list_rooms(act, as_parser(act))
        self.assertEqual(0, len(response_data[1]['object']['attachments']))
