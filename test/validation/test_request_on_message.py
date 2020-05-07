from activitystreams import parse as as_parser

from unittest import TestCase
from uuid import uuid4 as uuid

from dino import environ
from dino.remote import IRemoteHandler
from dino.utils import b64e
from dino.auth.redis import AuthRedis
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.config import RedisKeys
from dino.config import ErrorCodes
from dino.exceptions import NoSuchRoomException
from dino.exceptions import NoChannelFoundException
from dino.exceptions import NoSuchChannelException
from dino.validation import RequestValidator
from dino.validation.acl import AclStrInCsvValidator
from dino.validation.acl import AclSameChannelValidator
from dino.validation.acl import AclRangeValidator


class FakeRemote(IRemoteHandler):
    def __init__(self):
        self.blocked = dict()

    def can_send_whisper_to(self, sender_id: str, target_user_name: str) -> bool:
        if target_user_name not in self.blocked.keys():
            return True

        if sender_id in self.blocked.get(target_user_name):
            return False

        return True


class FakeDb(object):
    _channel_exists = dict()
    _room_exists = dict()
    _room_contains = dict()
    _channel_for_room = dict()
    _channel_names = dict()

    _ban_status = {
        'global': '',
        'channel': '',
        'room': ''
    }

    _room_acls = {
        'message': dict(),
        'crossroom': {'samechannel': ''},
    }

    _channel_acls = {
        'message': dict(),
        'crossroom': {'samechannel': ''},
    }

    def channel_for_room(self, room_id: str) -> str:
        if room_id is None or room_id.strip() == '':
            raise NoSuchRoomException(room_id)
        if room_id not in FakeDb._channel_for_room:
            raise NoChannelFoundException(room_id)
        return FakeDb._channel_for_room[room_id]

    def is_admin(self, *args):
        return False

    def is_global_moderator(self, user_id):
        return False

    def is_owner(self, *args):
        return False

    def is_owner_channel(self, *args):
        return False

    def is_super_user(self, *args):
        return False

    def get_acls_in_channel_for_action(self, channel_id, action):
        return FakeDb._channel_acls[action]

    def get_acls_in_room_for_action(self, room_id: str, action: str):
        return FakeDb._room_acls[action]

    def get_user_ban_status(self, room_id: str, user_id: str):
        return FakeDb._ban_status

    def channel_exists(self, channel_id):
        return FakeDb._channel_exists[channel_id]

    def room_exists(self, channel_id, room_id):
        return FakeDb._room_exists[room_id]

    def room_contains(self, room_id, user_id):
        return user_id in FakeDb._room_contains[room_id]

    def get_channel_name(self, channel_id):
        if channel_id not in FakeDb._channel_names:
            raise NoSuchChannelException(channel_id)
        return FakeDb._channel_names[channel_id]


class FakeCache:
    def get_can_whisper_to_user(self, sender_id, target_user_name):
        return None

    def set_can_whisper_to_user(self, sender_id, target_user_name, allowed):
        pass


class RequestMessageTest(TestCase):
    CHANNEL_ID = '8765'
    CHANNEL_NAME = 'Shanghai'
    ROOM_ID = '4567'
    OTHER_ROOM_ID = '9999'
    OTHER_CHANNEL_ID = '8888'
    USER_ID = '1234'
    USER_NAME = 'Joe'
    AGE = '30'
    GENDER = 'f'
    MEMBERSHIP = '0'
    IMAGE = 'y'
    HAS_WEBCAM = 'y'
    FAKE_CHECKED = 'n'
    COUNTRY = 'cn'
    CITY = 'Shanghai'
    TOKEN = str(uuid())

    def setUp(self):
        environ.env.db = FakeDb()
        self.remote = FakeRemote()
        environ.env.remote = self.remote
        environ.env.cache = FakeCache()
        FakeDb._channel_exists = {
            RequestMessageTest.CHANNEL_ID: True,
            RequestMessageTest.OTHER_CHANNEL_ID: False
        }

        FakeDb._room_exists = {
            RequestMessageTest.ROOM_ID: True,
            RequestMessageTest.OTHER_ROOM_ID: False
        }

        FakeDb._room_contains = {
            RequestMessageTest.ROOM_ID: {
                RequestMessageTest.USER_ID
            },
            RequestMessageTest.OTHER_ROOM_ID: set()
        }

        FakeDb._channel_names = {
            RequestMessageTest.CHANNEL_ID: RequestMessageTest.CHANNEL_NAME
        }

        FakeDb._channel_for_room = {
            RequestMessageTest.ROOM_ID: RequestMessageTest.CHANNEL_ID,
            RequestMessageTest.OTHER_ROOM_ID: RequestMessageTest.OTHER_CHANNEL_ID,
        }

        self.auth = AuthRedis(host='mock', env=environ.env)
        environ.env.session = {
            SessionKeys.user_id.value: RequestMessageTest.USER_ID,
            SessionKeys.user_name.value: RequestMessageTest.USER_NAME,
            SessionKeys.age.value: RequestMessageTest.AGE,
            SessionKeys.gender.value: RequestMessageTest.GENDER,
            SessionKeys.membership.value: RequestMessageTest.MEMBERSHIP,
            SessionKeys.image.value: RequestMessageTest.IMAGE,
            SessionKeys.has_webcam.value: RequestMessageTest.HAS_WEBCAM,
            SessionKeys.fake_checked.value: RequestMessageTest.FAKE_CHECKED,
            SessionKeys.country.value: RequestMessageTest.COUNTRY,
            SessionKeys.city.value: RequestMessageTest.CITY,
            SessionKeys.token.value: RequestMessageTest.TOKEN
        }

        environ.env.config = {
            ConfigKeys.ACL: {
                'room': {
                    'join': {
                        'acls': [
                            'gender',
                            'age',
                            'country'
                        ]
                    },
                    'message': {
                        'acls': [
                            'gender',
                            'age'
                        ]
                    },
                    'crossroom': {
                        'acls': [
                            'samechannel'
                        ]
                    }
                },
                'channel': {
                    'crossroom': {
                        'acls': [
                            'samechannel'
                        ]
                    }
                },
                'available': {
                    'acls': [
                        'gender',
                        'age',
                        'samechannel'
                    ]
                },
                'validation': {
                    'samechannel': {
                        'type': 'samechannel',
                        'value': AclSameChannelValidator()
                    },
                    'country': {
                        'type': 'anything',
                        'value': AclStrInCsvValidator()
                    },
                    'gender': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('m,f')
                    },
                    'age': {
                        'type': 'range',
                        'value': AclRangeValidator()
                    }
                }
            }
        }
        self.auth.redis.hmset(RedisKeys.auth_key(RequestMessageTest.USER_ID), environ.env.session)
        self.validator = RequestValidator()

    def test_whisper_ok(self):
        act = self.act()
        act.object.content = b64e(" -kenobi Hello there!")
        is_valid, code, msg = self.validator.on_message(act)
        self.assertTrue(is_valid)

    def test_no_whisper_ok(self):
        act = self.act()
        act.object.content = b64e(" kenobi Hello there!")
        is_valid, code, msg = self.validator.on_message(act)
        self.assertTrue(is_valid)

    def test_multiple_whisper_ok(self):
        act = self.act()
        act.object.content = b64e(" -kenobi -anakin Hello there!")
        is_valid, code, msg = self.validator.on_message(act)
        self.assertTrue(is_valid)

    def test_whisper_not_ok_first_blocked(self):
        act = self.act()

        self.remote.blocked['kenobi'] = {act.actor.id}

        act.object.content = b64e(" -kenobi -anakin Hello there!")
        is_valid, code, msg = self.validator.on_message(act)
        self.assertFalse(is_valid)

    def test_whisper_not_ok_second_blocked(self):
        act = self.act()

        self.remote.blocked['anakin'] = {act.actor.id}

        act.object.content = b64e(" -kenobi -anakin Hello there!")
        is_valid, code, msg = self.validator.on_message(act)
        self.assertFalse(is_valid)

    def test_whisper_not_ok_both_blocked(self):
        act = self.act()

        self.remote.blocked['kenobi'] = {act.actor.id}
        self.remote.blocked['anakin'] = {act.actor.id}

        act.object.content = b64e(" -kenobi -anakin Hello there!")
        is_valid, code, msg = self.validator.on_message(act)
        self.assertFalse(is_valid)

    def test_whisper_ok_none_blocked(self):
        act = self.act()

        self.remote.blocked[act.actor.id] = {'batman'}

        act.object.content = b64e(" -kenobi -anakin Hello there!")
        is_valid, code, msg = self.validator.on_message(act)
        self.assertTrue(is_valid)

    def test_on_message(self):
        is_valid, code, msg = self.validator.on_message(self.act())
        self.assertTrue(is_valid)

    def test_no_object_content(self):
        act = self.json_act()
        del act['object']['content']
        is_valid, code, msg = self.validator.on_message(as_parser(act))
        self.assertFalse(is_valid)

    def test_blank_object_content(self):
        act = self.json_act()
        act['object']['content'] = ''
        is_valid, code, msg = self.validator.on_message(as_parser(act))
        self.assertFalse(is_valid)

    def test_object_content_not_base64(self):
        act = self.json_act()
        act['object']['content'] = 'this is not base64'
        is_valid, code, msg = self.validator.on_message(as_parser(act))
        self.assertFalse(is_valid)

    def test_wrong_object_type(self):
        json_act = self.json_act()
        json_act['target']['objectType'] = 'foo'
        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertEqual(code, ErrorCodes.INVALID_TARGET_TYPE)
        self.assertFalse(is_valid)

    def test_no_room_id(self):
        json_act = self.json_act()
        json_act['target']['id'] = ''
        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def test_channel_does_not_exist(self):
        FakeDb._channel_exists[RequestMessageTest.CHANNEL_ID] = False
        json_act = self.json_act()
        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def test_room_does_not_exist(self):
        FakeDb._room_exists[RequestMessageTest.ROOM_ID] = False
        json_act = self.json_act()
        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def test_origin_room_does_not_exist(self):
        json_act = self.json_act()
        json_act['actor']['url'] = RequestMessageTest.OTHER_ROOM_ID
        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def test_not_in_target_room(self):
        json_act = self.json_act()
        FakeDb._room_contains[RequestMessageTest.ROOM_ID].remove(RequestMessageTest.USER_ID)
        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def test_cross_room_not_same_channel(self):
        json_act = self.json_act()
        json_act['actor']['url'] = RequestMessageTest.ROOM_ID
        json_act['provider'] = dict()
        json_act['provider']['url'] = RequestMessageTest.OTHER_CHANNEL_ID
        json_act['target']['id'] = RequestMessageTest.OTHER_ROOM_ID

        FakeDb._room_exists[RequestMessageTest.OTHER_ROOM_ID] = True
        FakeDb._channel_exists[RequestMessageTest.OTHER_CHANNEL_ID] = True

        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def test_cross_room_same_channel(self):
        json_act = self.json_act()
        json_act['actor']['url'] = RequestMessageTest.ROOM_ID
        json_act['provider'] = dict()
        json_act['provider']['url'] = RequestMessageTest.CHANNEL_ID

        FakeDb._room_exists[RequestMessageTest.OTHER_ROOM_ID] = True
        FakeDb._room_contains[RequestMessageTest.OTHER_ROOM_ID].add(RequestMessageTest.USER_ID)

        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertTrue(is_valid)

    def test_cross_room_same_channel_not_in_origin_room(self):
        json_act = self.json_act()
        json_act['actor']['url'] = RequestMessageTest.ROOM_ID
        json_act['provider'] = dict()
        json_act['provider']['url'] = RequestMessageTest.CHANNEL_ID

        FakeDb._room_exists[RequestMessageTest.OTHER_ROOM_ID] = True
        FakeDb._room_contains[RequestMessageTest.ROOM_ID].remove(RequestMessageTest.USER_ID)

        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def act(self):
        return as_parser(self.json_act())

    def json_act(self):
        return {
            'actor': {
                'id': RequestMessageTest.USER_ID
            },
            'verb': 'join',
            'object': {
                'url': RequestMessageTest.CHANNEL_ID,
                'content': b64e('this is the message')
            },
            'target': {
                'id': RequestMessageTest.ROOM_ID,
                'objectType': 'room'
            }
        }
