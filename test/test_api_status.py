from dino import api
from test.utils import BaseTest
from dino import environ


class ApiStatusTest(BaseTest):
    def test_status_online(self):
        response_data = api.on_status(self.activity_for_status('online'))
        self.assertEqual(200, response_data[0])

    def test_status_invisible(self):
        response_data = api.on_status(self.activity_for_status('invisible'))
        self.assertEqual(200, response_data[0])

    def test_status_offline(self):
        response_data = api.on_status(self.activity_for_status('offline'))
        self.assertEqual(200, response_data[0])

    def test_status_invalid(self):
        response_data = api.on_status(self.activity_for_status('invalid'))
        self.assertEqual(400, response_data[0])

    def test_status_no_user_name_in_session(self):
        self.set_session(environ.SessionKeys.user_name.value, None)
        response_data = api.on_status(self.activity_for_status('online'))
        self.assertEqual(400, response_data[0])

    def test_status_change_user_id(self):
        self.set_session(environ.SessionKeys.user_id.value, BaseTest.USER_ID + '123')
        response_data = api.on_status(self.activity_for_status('online'))
        self.assertEqual(400, response_data[0])
