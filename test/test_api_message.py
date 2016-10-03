from uuid import uuid4 as uuid

from gridchat import rkeys
from gridchat import api
from test.utils import BaseTest


class ApiMessageTest(BaseTest):
    def test_send_message(self):
        self.create_and_join_room()
        response_data = api.on_message(self.activity_for_message())
        self.assertEqual(200, response_data[0])

    def test_send_message_without_actor_id(self):
        self.create_and_join_room()
        activity = self.activity_for_message()
        del activity['actor']['id']
        response_data = api.on_message(activity)
        self.assertEqual(400, response_data[0])

    def test_send_message_without_target_id(self):
        self.create_and_join_room()
        activity = self.activity_for_message()
        del activity['target']['id']
        response_data = api.on_message(activity)
        self.assertEqual(400, response_data[0])

    def test_send_message_without_being_in_room(self):
        new_room_id = str(uuid())
        self.create_room(room_id=new_room_id)

        activity = self.activity_for_message()
        activity['target']['id'] = new_room_id
        response_data = api.on_message(activity)
        self.assertEqual(400, response_data[0])

    def test_send_message_non_existing_room(self):
        new_room_id = str(uuid())
        activity = self.activity_for_message()
        activity['target']['id'] = new_room_id
        response_data = api.on_message(activity)
        self.assertEqual(400, response_data[0])
