from gridchat import api
from test.utils import BaseTest
from gridchat.env import SessionKeys


class ApiDisconnectTest(BaseTest):
    def test_disconnect(self):
        response_data = api.on_disconnect()
        self.assertEqual(200, response_data[0])

    def test_not_connected(self):
        self.clear_session()
        response_data = api.on_disconnect()
        self.assertEqual(400, response_data[0])

    def test_disconnect_leaved_own_room(self):
        api.on_login(self.activity_for_login())
        self.assert_in_own_room(True)

        api.on_disconnect()
        self.assert_in_own_room(False)

    def test_disconnect_leaves_joined_room(self):
        self.join_room()
        self.assert_in_room(True)

        api.on_disconnect()
        self.assert_in_room(False)

    def test_disconnect_needs_user_id_in_session(self):
        self.set_session(SessionKeys.user_id.value, None)
        response_data = api.on_disconnect()
        self.assertEqual(400, response_data[0])
