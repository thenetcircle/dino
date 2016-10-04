from dino import api
from test.utils import BaseTest


class ApiUsersInRoomTest(BaseTest):
    def test_users_in_room_status_code_200(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        response_data = api.on_users_in_room(self.activity_for_users_in_room())
        self.assertEqual(200, response_data[0])

    def test_users_in_room_missing_actor_id_status_code_400(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        activity = self.activity_for_users_in_room()
        del activity['actor']['id']
        response_data = api.on_users_in_room(activity)
        self.assertEqual(400, response_data[0])

    def test_users_in_room_is_only_one(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        response_data = api.on_users_in_room(self.activity_for_users_in_room())
        self.assertEqual(1, len(response_data[1]['object']['attachments']))

    def test_users_in_room_is_correct_id(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        response_data = api.on_users_in_room(self.activity_for_users_in_room())
        self.assertEqual(ApiUsersInRoomTest.USER_ID, response_data[1]['object']['attachments'][0]['id'])

    def test_users_in_room_is_correct_name(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        response_data = api.on_users_in_room(self.activity_for_users_in_room())
        self.assertEqual(ApiUsersInRoomTest.USER_NAME, response_data[1]['object']['attachments'][0]['content'])

    def test_users_in_room_status_code_200_when_empty(self):
        self.assert_in_room(False)
        response_data = api.on_users_in_room(self.activity_for_users_in_room())
        self.assertEqual(200, response_data[0])

    def test_users_in_room_attachments_empty_when_no_user_in_room(self):
        self.assert_in_room(False)
        response_data = api.on_users_in_room(self.activity_for_users_in_room())
        self.assertEqual(0, len(response_data[1]['object']['attachments']))

    def assert_leave_succeeds(self):
        self.assertEqual(200, self.response_code_for_leave())

    def response_code_for_leave(self, data=None):
        return self.leave_room(data)[0]
