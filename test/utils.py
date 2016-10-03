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


class BaseTest(unittest.TestCase):
    OTHER_USER_ID = '8888'
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

    users_in_room = dict()

    @staticmethod
    def _emit(event, *args, **kwargs):
        pass

    @staticmethod
    def _join_room(room):
        if room not in BaseTest.users_in_room:
            BaseTest.users_in_room[room] = list()
        BaseTest.users_in_room[room].append(BaseTest.USER_ID)

    @staticmethod
    def _leave_room(room):
        if room not in BaseTest.users_in_room:
            return

        if BaseTest.USER_ID in BaseTest.users_in_room[room]:
            BaseTest.users_in_room[room].remove(BaseTest.USER_ID)

    @staticmethod
    def _send(message, **kwargs):
        pass

    def setUp(self):
        redis.flushall()
        redis.set(rkeys.room_name_for_id(BaseTest.ROOM_ID), BaseTest.ROOM_NAME)
        env.logger = logger
        env.emit = BaseTest._emit
        env.join_room = BaseTest._join_room
        env.send = BaseTest._send
        env.leave_room = BaseTest._leave_room
        env.session = {
            'user_id': BaseTest.USER_ID,
            'user_name': BaseTest.USER_NAME,
            'age': BaseTest.AGE,
            'gender': BaseTest.GENDER,
            'membership': BaseTest.MEMBERSHIP,
            'image': BaseTest.IMAGE,
            'fake_checked': BaseTest.FAKE_CHECKED,
            'has_webcam': BaseTest.HAS_WEBCAM,
            'city': BaseTest.CITY,
            'country': BaseTest.COUNTRY
        }
        env.redis = redis
        self.users_in_room.clear()

    def clear_session(self):
        env.session.clear()

    def assert_add_fails(self):
        self.assertEqual(400, self.get_response_code_for_add())

    def assert_add_succeeds(self):
        self.assertEqual(200, self.get_response_code_for_add())

    def get_response_code_for_add(self):
        return api.on_add_owner(self.activity_for_add_owner())[0]

    def create_and_join_room(self):
        self.create_room()
        self.join_room()

    def set_owner(self):
        redis.hset(rkeys.room_owners(BaseTest.ROOM_ID), BaseTest.USER_ID, BaseTest.USER_NAME)

    def remove_owner(self):
        redis.hdel(rkeys.room_owners(BaseTest.ROOM_ID), BaseTest.USER_ID)

    def set_room_name(self, room_id: str=None, room_name: str=None):
        if room_id is None:
            room_id = BaseTest.ROOM_ID
        if room_name is None:
            room_name = BaseTest.ROOM_NAME

        env.redis.set(rkeys.room_name_for_id(room_id), room_name)

    def join_room(self):
        api.on_join(self.activity_for_join())

    def assert_in_session(self, key, expected):
        self.assertTrue(key in env.session)
        self.assertEqual(expected, env.session[key])

    def assert_not_in_session(self, key, expected):
        self.assertFalse(key in env.session)

    def leave_room(self, data=None):
        if data is None:
            data = self.activity_for_leave()
        return api.on_leave(data)

    def create_room(self, room_id: str=None, room_name: str=None):
        if room_id is None:
            room_id = BaseTest.ROOM_ID
        if room_name is None:
            room_name = BaseTest.ROOM_NAME

        redis.hset(rkeys.rooms(), room_id, room_name)

    def assert_join_fails(self):
        self.assertEqual(400, self.response_code_for_joining())
        self.assert_in_room(False)

    def assert_join_succeeds(self):
        self.assertEqual(200, self.response_code_for_joining())
        self.assert_in_room(True)

    def response_code_for_joining(self):
        return api.on_join(self.activity_for_join())[0]

    def send_message(self, message: str) -> dict:
        return api.on_message(self.activity_for_message(message))

    def set_session(self, key: str, value: str=None):
        env.session[key] = value

    def get_acls(self):
        return redis.hgetall(rkeys.room_acl(BaseTest.ROOM_ID))

    def set_acl(self, acls: dict):
        redis.hmset(rkeys.room_acl(BaseTest.ROOM_ID), acls)

    def set_acl_single(self, key: str, acls: str):
        redis.hset(rkeys.room_acl(BaseTest.ROOM_ID), key, acls)

    def assert_in_room(self, is_in_room):
        self.assertEqual(is_in_room, BaseTest.ROOM_ID in BaseTest.users_in_room and
                         BaseTest.USER_ID in BaseTest.users_in_room[BaseTest.ROOM_ID])

    def assert_in_own_room(self, is_in_room):
        self.assertEqual(is_in_room, BaseTest.USER_ID in BaseTest.users_in_room and
                         BaseTest.USER_ID in BaseTest.users_in_room[BaseTest.USER_ID])

    def activity_for_create(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'verb': 'create',
            'target': {
                'displayName': BaseTest.ROOM_NAME
            }
        }

    def activity_for_users_in_room(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'verb': 'list',
            'target': {
                'id': BaseTest.ROOM_ID
            }
        }

    def activity_for_login(self, skip: set=None):
        data = {
            'actor': {
                'id': BaseTest.USER_ID,
                'summary': BaseTest.USER_NAME,
                'image': {
                    'url': 'http://some-url.com/image.jpg',
                    'width': '120',
                    'height': '120'
                },
                'attachments': list()
            },
            'verb': 'login'
        }

        if skip is not None:
            if 'user_id' in skip:
                del data['actor']['id']
            if 'user_name' in skip:
                del data['actor']['summary']
            if 'image' in skip:
                del data['actor']['image']

        infos = {
            'gender': BaseTest.GENDER,
            'age': BaseTest.AGE,
            'membership': BaseTest.MEMBERSHIP,
            'fake_checked': BaseTest.FAKE_CHECKED,
            'has_webcam': BaseTest.HAS_WEBCAM,
            'country': BaseTest.COUNTRY,
            'city': BaseTest.CITY,
            'token': '66968fad-2336-40c9-bc6d-0ecbcd91f4da'
        }

        for key, val in infos.items():
            if skip is None or key not in skip:
                data['actor']['attachments'].append({'objectType': key, 'content': val})

        return data

    def activity_for_list_rooms(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'verb': 'list'
        }

    def activity_for_message(self, msg: str='test message'):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'verb': 'send',
            'target': {
                'id': BaseTest.ROOM_ID
            },
            'object': {
                'content': msg
            }
        }

    def activity_for_leave(self, skip: set=None):
        data = {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'target': {
                'id': BaseTest.ROOM_ID
            },
            'verb': 'leave'
        }

        if skip is not None:
            for s in list(skip):
                del data[s]

        return data

    def activity_for_add_owner(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'verb': 'add',
            'object': {
                'objectType': 'user',
                'content': BaseTest.OTHER_USER_ID
            },
            'target': {
                'id': BaseTest.ROOM_ID
            }
        }

    def activity_for_join(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'verb': 'join',
            'target': {
                'id': BaseTest.ROOM_ID
            }
        }