import unittest
import fakeredis
from uuid import uuid4 as uuid
import logging

from gridchat.env import env, ConfigKeys
from gridchat import rkeys

redis = fakeredis.FakeStrictRedis()
env.config = dict()
env.config[ConfigKeys.REDIS] = redis
env.config[ConfigKeys.TESTING] = True
env.config[ConfigKeys.SESSION] = dict()
env.config[ConfigKeys.SESSION]['user_id'] = '1234'

from gridchat import api

logging.basicConfig(level='DEBUG')
logger = logging.getLogger(__name__)


class ApiListRoomsTest(unittest.TestCase):
    USER_ID = '1234'
    USER_NAME = 'Joe'
    ROOM_ID = USER_ID
    ROOM_NAME = 'Shanghai:stuff about this place!'
    AGE = '30'
    GENDER = 'f'
    MEMBERSHIP = '0'
    IMAGE = 'y'
    HAS_WEBCAM = 'y'
    FAKE_CHECKED = 'n'
    COUNTRY = 'cn'
    CITY = 'Shanghai'

    users_in_room = dict()

    @staticmethod
    def emit(event, *args, **kwargs):
        pass

    @staticmethod
    def join_room(room):
        if room not in ApiListRoomsTest.users_in_room:
            ApiListRoomsTest.users_in_room[room] = list()
        ApiListRoomsTest.users_in_room[room].append(ApiListRoomsTest.USER_ID)

    @staticmethod
    def leave_room(room):
        if room not in ApiListRoomsTest.users_in_room:
            return

        if ApiListRoomsTest.USER_ID in ApiListRoomsTest.users_in_room[room]:
            ApiListRoomsTest.users_in_room[room].remove(ApiListRoomsTest.USER_ID)

    def setUp(self):
        redis.flushall()
        redis.set(rkeys.room_name_for_id(ApiListRoomsTest.ROOM_ID), ApiListRoomsTest.ROOM_NAME)
        ApiListRoomsTest.users_in_room.clear()

        env.emit = ApiListRoomsTest.emit
        env.join_room = ApiListRoomsTest.join_room
        env.leave_room = ApiListRoomsTest.leave_room
        env.redis = redis
        env.session = {
            'user_id': ApiListRoomsTest.USER_ID,
            'user_name': ApiListRoomsTest.USER_NAME,
            'age': ApiListRoomsTest.AGE,
            'gender': ApiListRoomsTest.GENDER,
            'membership': ApiListRoomsTest.MEMBERSHIP,
            'image': ApiListRoomsTest.IMAGE,
            'fake_checked': ApiListRoomsTest.FAKE_CHECKED,
            'has_webcam': ApiListRoomsTest.HAS_WEBCAM,
            'city': ApiListRoomsTest.CITY,
            'country': ApiListRoomsTest.COUNTRY
        }

    def test_list_rooms_status_code_200(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        response_data = api.on_list_rooms(self.activity_for_list_rooms())
        self.assertEqual(200, response_data[0])

    def test_list_rooms_no_actor_id_status_code_400(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        activity = self.activity_for_list_rooms()
        del activity['actor']['id']
        response_data = api.on_list_rooms(activity)
        self.assertEqual(400, response_data[0])

    def test_list_rooms_only_one(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        response_data = api.on_list_rooms(self.activity_for_list_rooms())
        self.assertEqual(1, len(response_data[1]['object']['attachments']))

    def test_list_rooms_correct_id(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        response_data = api.on_list_rooms(self.activity_for_list_rooms())
        self.assertEqual(ApiListRoomsTest.ROOM_ID, response_data[1]['object']['attachments'][0]['id'])

    def test_list_rooms_correct_name(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
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

    def assert_in_room(self, is_in_room):
        self.assertEqual(is_in_room, ApiListRoomsTest.ROOM_ID in ApiListRoomsTest.users_in_room and
                         ApiListRoomsTest.USER_ID in ApiListRoomsTest.users_in_room[ApiListRoomsTest.ROOM_ID])

    def activity_for_list_rooms(self):
        return {
            'actor': {
                'id': ApiListRoomsTest.USER_ID
            },
            'verb': 'list'
        }

    def activity_for_join(self):
        return {
            'actor': {
                'id': ApiListRoomsTest.USER_ID,
                'summary': ApiListRoomsTest.USER_NAME
            },
            'verb': 'join',
            'target': {
                'id': ApiListRoomsTest.ROOM_ID
            }
        }
