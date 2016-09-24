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


class ApiLeaveTest(unittest.TestCase):
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
        if room not in ApiLeaveTest.users_in_room:
            ApiLeaveTest.users_in_room[room] = list()
        ApiLeaveTest.users_in_room[room].append(ApiLeaveTest.USER_ID)

    @staticmethod
    def leave_room(room):
        if room not in ApiLeaveTest.users_in_room:
            return

        if ApiLeaveTest.USER_ID in ApiLeaveTest.users_in_room[room]:
            ApiLeaveTest.users_in_room[room].remove(ApiLeaveTest.USER_ID)

    def setUp(self):
        redis.flushall()
        redis.set(rkeys.room_name_for_id(ApiLeaveTest.ROOM_ID), ApiLeaveTest.ROOM_NAME)
        ApiLeaveTest.users_in_room.clear()

        env.emit = ApiLeaveTest.emit
        env.join_room = ApiLeaveTest.join_room
        env.leave_room = ApiLeaveTest.leave_room
        env.redis = redis
        env.session = {
            'user_id': ApiLeaveTest.USER_ID,
            'user_name': ApiLeaveTest.USER_NAME,
            'age': ApiLeaveTest.AGE,
            'gender': ApiLeaveTest.GENDER,
            'membership': ApiLeaveTest.MEMBERSHIP,
            'image': ApiLeaveTest.IMAGE,
            'fake_checked': ApiLeaveTest.FAKE_CHECKED,
            'has_webcam': ApiLeaveTest.HAS_WEBCAM,
            'city': ApiLeaveTest.CITY,
            'country': ApiLeaveTest.COUNTRY
        }

    def test_leave_when_not_in_room_is_okay(self):
        self.assert_in_room(False)
        self.assert_leave_succeeds()
        self.assert_in_room(False)

    def test_leave_when_in_room_is_okay(self):
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)
        self.assert_leave_succeeds()
        self.assert_in_room(False)

    def test_leave_without_target_id(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        data = self.activity_for_leave(skip={'target'})
        response_data = api.on_leave(data)

        self.assertEqual(400, response_data[0])
        self.assert_in_room(True)

    def test_leave_different_room_stays_in_current(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        tmp_room_id = str(uuid())
        redis.set(rkeys.room_name_for_id(tmp_room_id), tmp_room_id)
        data = self.activity_for_leave()
        data['target']['id'] = tmp_room_id
        response_data = api.on_leave(data)

        self.assertEqual(200, response_data[0])
        self.assert_in_room(True)

    def assert_in_room(self, is_in_room):
        self.assertEqual(is_in_room, ApiLeaveTest.ROOM_ID in ApiLeaveTest.users_in_room and
                         ApiLeaveTest.USER_ID in ApiLeaveTest.users_in_room[ApiLeaveTest.ROOM_ID])

    def assert_leave_succeeds(self):
        self.assertEqual(200, self.response_code_for_leave())

    def response_code_for_leave(self, data=None):
        return self.leave(data)[0]

    def leave(self, data=None):
        if data is None:
            data = self.activity_for_leave()
        return api.on_leave(data)

    def activity_for_leave(self, skip: set=None):
        data = {
            'actor': {
                'id': ApiLeaveTest.USER_ID
            },
            'target': {
                'id': ApiLeaveTest.ROOM_ID
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
                'id': ApiLeaveTest.USER_ID,
                'summary': ApiLeaveTest.USER_NAME
            },
            'verb': 'join',
            'target': {
                'id': ApiLeaveTest.ROOM_ID
            }
        }
