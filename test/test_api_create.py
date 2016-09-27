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


class ApiCreateTest(unittest.TestCase):
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

    users_in_room = set()

    @staticmethod
    def _emit(event, *args, **kwargs):
        pass

    @staticmethod
    def _join_room(room):
        ApiCreateTest.users_in_room.add(ApiCreateTest.USER_ID)

    @staticmethod
    def _leave_room(room):
        ApiCreateTest.users_in_room.remove(ApiCreateTest.USER_ID)

    @staticmethod
    def _send(message, **kwargs):
        pass

    def setUp(self):
        redis.flushall()
        redis.set(rkeys.room_name_for_id(ApiCreateTest.ROOM_ID), ApiCreateTest.ROOM_NAME)
        env.logger = logger
        env.emit = ApiCreateTest._emit
        env.join_room = ApiCreateTest._join_room
        env.send = ApiCreateTest._send
        env.leave_room = ApiCreateTest._leave_room
        env.session = {
            'user_id': ApiCreateTest.USER_ID,
            'user_name': ApiCreateTest.USER_NAME,
            'age': ApiCreateTest.AGE,
            'gender': ApiCreateTest.GENDER,
            'membership': ApiCreateTest.MEMBERSHIP,
            'image': ApiCreateTest.IMAGE,
            'fake_checked': ApiCreateTest.FAKE_CHECKED,
            'has_webcam': ApiCreateTest.HAS_WEBCAM,
            'city': ApiCreateTest.CITY,
            'country': ApiCreateTest.COUNTRY
        }
        env.redis = redis

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

    def create_room(self, room_id: str=None, room_name: str=None):
        if room_id is None:
            room_id = ApiCreateTest.ROOM_ID
        if room_name is None:
            room_name = ApiCreateTest.ROOM_NAME

        redis.hset(rkeys.rooms(), room_id, room_name)

    def activity_for_create(self):
        return {
            'actor': {
                'id': ApiCreateTest.USER_ID
            },
            'verb': 'create',
            'target': {
                'displayName': ApiCreateTest.ROOM_NAME
            }
        }
    
    def activity_for_message(self, msg: str='test message'):
        return {
            'actor': {
                'id': ApiCreateTest.USER_ID
            },
            'verb': 'send',
            'target': {
                'id': ApiCreateTest.ROOM_ID
            },
            'object': {
                'content': msg
            }
        }

    def activity_for_join(self):
        return {
            'actor': {
                'id': ApiCreateTest.USER_ID
            },
            'verb': 'join',
            'target': {
                'id': ApiCreateTest.ROOM_ID
            }
        }