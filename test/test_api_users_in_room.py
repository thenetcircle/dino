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


class ApiUsersInRoomTest(unittest.TestCase):
    USER_ID = '1234'
    USER_NAME = 'Joe'
    ROOM_ID = USER_ID
    ROOM_NAME = USER_ID
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
        if room not in ApiUsersInRoomTest.users_in_room:
            ApiUsersInRoomTest.users_in_room[room] = list()
        ApiUsersInRoomTest.users_in_room[room].append(ApiUsersInRoomTest.USER_ID)

    @staticmethod
    def leave_room(room):
        if room not in ApiUsersInRoomTest.users_in_room:
            return

        if ApiUsersInRoomTest.USER_ID in ApiUsersInRoomTest.users_in_room[room]:
            ApiUsersInRoomTest.users_in_room[room].remove(ApiUsersInRoomTest.USER_ID)

    def setUp(self):
        redis.flushall()
        redis.set(rkeys.room_name_for_id(ApiUsersInRoomTest.ROOM_ID), ApiUsersInRoomTest.ROOM_NAME)
        ApiUsersInRoomTest.users_in_room.clear()

        env.emit = ApiUsersInRoomTest.emit
        env.join_room = ApiUsersInRoomTest.join_room
        env.leave_room = ApiUsersInRoomTest.leave_room
        env.redis = redis
        env.session = {
            'user_id': ApiUsersInRoomTest.USER_ID,
            'user_name': ApiUsersInRoomTest.USER_NAME,
            'age': ApiUsersInRoomTest.AGE,
            'gender': ApiUsersInRoomTest.GENDER,
            'membership': ApiUsersInRoomTest.MEMBERSHIP,
            'image': ApiUsersInRoomTest.IMAGE,
            'fake_checked': ApiUsersInRoomTest.FAKE_CHECKED,
            'has_webcam': ApiUsersInRoomTest.HAS_WEBCAM,
            'city': ApiUsersInRoomTest.CITY,
            'country': ApiUsersInRoomTest.COUNTRY
        }

    def test_users_in_room_status_code_200(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        response_data = api.on_users_in_room(self.activity_for_users_in_room())
        self.assertEqual(200, response_data[0])

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

    def assert_in_room(self, is_in_room):
        self.assertEqual(is_in_room, ApiUsersInRoomTest.ROOM_ID in ApiUsersInRoomTest.users_in_room and
                         ApiUsersInRoomTest.USER_ID in ApiUsersInRoomTest.users_in_room[ApiUsersInRoomTest.ROOM_ID])

    def assert_leave_succeeds(self):
        self.assertEqual(200, self.response_code_for_leave())

    def response_code_for_leave(self, data=None):
        return self.leave(data)[0]

    def leave(self, data=None):
        if data is None:
            data = self.activity_for_leave()
        return api.on_leave(data)

    def activity_for_users_in_room(self):
        return {
            'actor': {
                'id': ApiUsersInRoomTest.USER_ID
            },
            'verb': 'list',
            'target': {
                'id': ApiUsersInRoomTest.ROOM_ID
            }
        }

    def activity_for_leave(self, skip: set=None):
        data = {
            'actor': {
                'id': ApiUsersInRoomTest.USER_ID
            },
            'target': {
                'id': ApiUsersInRoomTest.ROOM_ID
            },
            'verb': 'leave'
        }

        if skip is not None:
            for s in list(skip):
                del data[s]

        return data

    def activity_for_join(self):
        return {
            'actor': {
                'id': ApiUsersInRoomTest.USER_ID,
                'summary': ApiUsersInRoomTest.USER_NAME
            },
            'verb': 'join',
            'target': {
                'id': ApiUsersInRoomTest.ROOM_ID
            }
        }
