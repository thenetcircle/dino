from dino import api
from test.utils import BaseTest
from dino.config import RedisKeys


class ApiCreateTest(BaseTest):
    def test_create(self):
        response_data = api.on_create(self.activity_for_create())
        self.assertEqual(200, response_data[0])

    def test_create_already_existing(self):
        api.on_create(self.activity_for_create())
        response_data = api.on_create(self.activity_for_create())
        self.assertEqual(400, response_data[0])

    def test_create_missing_target_display_name(self):
        activity = self.activity_for_create()
        del activity['target']['displayName']
        response_data = api.on_create(activity)
        self.assertEqual(400, response_data[0])

    def test_create_missing_actor_id(self):
        activity = self.activity_for_create()
        del activity['actor']['id']
        response_data = api.on_create(activity)
        self.assertEqual(400, response_data[0])
