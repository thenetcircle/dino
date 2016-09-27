import unittest
import fakeredis
from uuid import uuid4 as uuid
import logging

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

logging.basicConfig(level='DEBUG')
logger = logging.getLogger(__name__)


class ApiMessageTest(unittest.TestCase):
    USER_ID = '1234'
    USER_NAME = 'Joe'
    ROOM_ID = str(uuid())
    ROOM_NAME = 'Shanghai'
    AGE = '30'
    GENDER = 'f'
    MEMBERSHIP = '0'
    IMAGE = 'y'
    HAS_WEBCAM = 'y'
    FAKE_CHECKED = 'n'
    COUNTRY = 'cn'
    CITY = 'Shanghai'

    def setUp(self):
        redis.flushall()
        redis.set(rkeys.room_name_for_id(ApiMessageTest.ROOM_ID), ApiMessageTest.ROOM_NAME)
        env.logger = logger
        env.session = {
            'user_id': ApiMessageTest.USER_ID,
            'user_name': ApiMessageTest.USER_NAME,
            'age': ApiMessageTest.AGE,
            'gender': ApiMessageTest.GENDER,
            'membership': ApiMessageTest.MEMBERSHIP,
            'image': ApiMessageTest.IMAGE,
            'fake_checked': ApiMessageTest.FAKE_CHECKED,
            'has_webcam': ApiMessageTest.HAS_WEBCAM,
            'city': ApiMessageTest.CITY,
            'country': ApiMessageTest.COUNTRY
        }
        env.redis = redis

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

    def create_room(self, room_id: str=None, room_name: str=None):
        if room_id is None:
            room_id = ApiMessageTest.ROOM_ID
        if room_name is None:
            room_name = ApiMessageTest.ROOM_NAME

        redis.hset(rkeys.rooms(), room_id, room_name)

    def create_and_join_room(self):
        self.create_room()
        api.on_join(self.activity_for_join())
    
    def activity_for_message(self, msg: str='test message'):
        return {
            'actor': {
                'id': ApiMessageTest.USER_ID
            },
            'verb': 'send',
            'target': {
                'id': ApiMessageTest.ROOM_ID
            },
            'object': {
                'content': msg
            }
        }

    def activity_for_join(self):
        return {
            'actor': {
                'id': ApiMessageTest.USER_ID
            },
            'verb': 'join',
            'target': {
                'id': ApiMessageTest.ROOM_ID
            }
        }
