import unittest
import fakeredis
from pprint import pprint
from uuid import uuid4 as uuid

from gridchat.env import env, ConfigKeys
from gridchat import rkeys
from activitystreams import parse as as_parser

redis = fakeredis.FakeStrictRedis()
env.config = dict()
env.config[ConfigKeys.REDIS] = redis
env.config[ConfigKeys.TESTING] = True
env.config[ConfigKeys.SESSION] = dict()
env.config[ConfigKeys.SESSION]['user_id'] = '1234'

from gridchat import api


class ApiTest(unittest.TestCase):
    def test_user_info(self):
        room_id = str(uuid())

        acl_type = 'gender'
        acl_value = 'm,f'

        redis.set(rkeys.room_name_for_id(room_id), 'shanghai')
        redis.hmset(rkeys.room_acl(room_id), {acl_type: acl_value})

        response_data = api.on_get_acl({'actor': {'id': '1234'}, 'target': {'id': room_id}, 'verb': 'list'})
        activity = as_parser(response_data[1])  # 0 is the status_code, 1 is the data (activity stream)

        self.assertEqual(activity.object.attachments[0].object_type, acl_type)
        self.assertEqual(activity.object.attachments[0].content, acl_value)
