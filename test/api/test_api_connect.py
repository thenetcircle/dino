from dino import api
from test.base import BaseTest


class ApiConnectTest(BaseTest):
    def test_connect(self):
        response_data = api.connect()
        self.assertEqual(200, response_data[0])
