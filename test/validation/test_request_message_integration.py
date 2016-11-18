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

from uuid import uuid4 as uuid
from activitystreams import parse as as_parser

from dino.config import ApiActions
from dino.validation import request
from test.base import BaseTest


class RequestMessageIntegrationTest(BaseTest):
    def test_send_message(self):
        self.create_and_join_room()
        response_data = request.on_message(as_parser(self.activity_for_message()))
        self.assertEqual(True, response_data[0])

    def test_send_message_without_actor_id(self):
        self.create_and_join_room()
        activity = self.activity_for_message()
        del activity['actor']['id']
        response_data = request.on_message(as_parser(activity))
        self.assertEqual(False, response_data[0])

    def test_send_message_without_target_id(self):
        self.create_and_join_room()
        activity = self.activity_for_message()
        del activity['target']['id']
        response_data = request.on_message(as_parser(activity))
        self.assertEqual(False, response_data[0])

    def test_send_message_without_being_in_room(self):
        new_room_id = str(uuid())
        self.create_room(room_id=new_room_id)

        activity = self.activity_for_message()
        activity['target']['objectType'] = 'room'
        activity['target']['id'] = new_room_id
        response_data = request.on_message(as_parser(activity))
        self.assertEqual(False, response_data[0])

    def test_send_message_non_existing_room(self):
        new_room_id = str(uuid())
        activity = self.activity_for_message()
        activity['target']['objectType'] = 'room'
        activity['target']['id'] = new_room_id
        response_data = request.on_message(as_parser(activity))
        self.assertEqual(False, response_data[0])

    def test_send_cross_group(self):
        new_room_id = str(uuid())
        self.create_and_join_room()
        self.create_channel_and_room(room_id=new_room_id, room_name='asdf')
        self.remove_owner()
        self.remove_owner_channel()

        self.set_acl({ApiActions.CROSSROOM: {'samechannel': ''}}, room_id=new_room_id)
        activity = self.activity_for_message()
        activity['target']['objectType'] = 'room'
        activity['target']['id'] = new_room_id

        response_data = request.on_message(as_parser(activity))
        self.assertEqual(True, response_data[0])

    def test_send_cross_group_not_allowed(self):
        new_room_id = str(uuid())
        self.create_and_join_room()
        self.create_channel_and_room(room_id=new_room_id, room_name='asdf')
        self.remove_owner()
        self.remove_owner_channel()

        self.set_acl({ApiActions.CROSSROOM: {'disallow': ''}}, room_id=new_room_id)

        activity = self.activity_for_message()
        activity['target']['objectType'] = 'room'
        activity['target']['id'] = new_room_id
        activity['actor']['url'] = BaseTest.ROOM_ID

        response_data = request.on_message(as_parser(activity))
        self.assertEqual(False, response_data[0])
