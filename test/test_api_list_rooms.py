from dino import api
from test.utils import BaseTest


class ApiListRoomsTest(BaseTest):
    def test_list_rooms_status_code_200(self):
        self.assert_in_room(False)
        self.create_and_join_room()
        self.assert_in_room(True)

        response_data = api.on_list_rooms(self.activity_for_list_rooms())
        self.assertEqual(200, response_data[0])

    """
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
        self.assertEqual(ApiListRoomsTest.ROOM_NAME, response_data[1]['object']['attachments'][0]['content'])

    def test_list_rooms_status_code_200_if_no_rooms(self):
        self.assert_in_room(False)
        response_data = api.on_list_rooms(self.activity_for_list_rooms())
        self.assertEqual(200, response_data[0])

    def test_list_rooms_attachments_empty_if_no_rooms(self):
        self.assert_in_room(False)
        response_data = api.on_list_rooms(self.activity_for_list_rooms())
        self.assertEqual(0, len(response_data[1]['object']['attachments']))
    """
