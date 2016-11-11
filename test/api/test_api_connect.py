from dino import api
from test.utils import BaseTest


class ApiConnectTest(BaseTest):
    def test_connect(self):
        response_data = api.on_connect()
        self.assertEqual(200, response_data[0])
