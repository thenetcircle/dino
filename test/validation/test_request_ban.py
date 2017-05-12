# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from activitystreams import parse as as_parser

from unittest import TestCase
from uuid import uuid4 as uuid

from dino import environ
from dino.auth.redis import AuthRedis
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.config import RedisKeys
from dino.config import ErrorCodes
from dino.validation import RequestValidator
from dino.validation.acl import AclStrInCsvValidator
from dino.validation.acl import AclSameChannelValidator
from dino.validation.acl import AclRangeValidator
from dino.exceptions import NoSuchRoomException
from dino.exceptions import NoSuchUserException

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class FakeDb(object):
    _channel_exists = dict()
    _room_exists = dict()
    _room_contains = dict()
    _channel_for_room = dict()
    _moderators = dict()
    _owners = dict()
    _admins = dict()
    _super_users = set()
    _room_name = dict()
    _user_names = dict()
    _global_moderators = dict()

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

    def is_admin(self, channel_id, user_id):
        if channel_id not in FakeDb._admins:
            return False

        return user_id in FakeDb._admins[channel_id]

    def is_owner(self, room_id, user_id):
        if room_id not in self._owners:
            return False
        return user_id in self._owners[room_id]

    def is_owner_channel(self, *args):
        return False

    def is_super_user(self, user_id):
        return user_id in FakeDb._super_users

    def is_moderator(self, room_id, user_id):
        return room_id in FakeDb._moderators and user_id in FakeDb._moderators[room_id]

    def is_global_moderator(self, user_id):
        return user_id in FakeDb._global_moderators

    def channel_for_room(self, room_id):
        if room_id not in FakeDb._channel_for_room:
            return None
        return FakeDb._channel_for_room[room_id]

    def get_acls_in_channel_for_action(self, channel_id, action):
        return FakeDb._channel_acls[action]

    def get_acls_in_room_for_action(self, room_id: str, action: str):
        return FakeDb._room_acls[action]

    def get_user_ban_status(self, room_id: str, user_id: str):
        return FakeDb._ban_status

    def channel_exists(self, channel_id):
        return FakeDb._channel_exists[channel_id]

    def room_exists(self, channel_id, room_id):
        return room_id in FakeDb._room_exists

    def room_contains(self, room_id, user_id):
        return user_id in FakeDb._room_contains[room_id]

    def get_room_name(self, room_id):
        if room_id in FakeDb._room_name:
            return FakeDb._room_name[room_id]
        raise NoSuchRoomException(room_id)

    def get_user_name(self, user_id):
        if user_id not in FakeDb._user_names:
            raise NoSuchUserException(user_id)
        return FakeDb._user_names[user_id]


class RequestBanTest(TestCase):
    OTHER_USER_ID = '9876'
    CHANNEL_ID = '8765'
    ROOM_ID = '4567'
    ROOM_NAME = 'cool guys'
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

    def test_ban_not_owner(self):
        is_valid, code, msg = self.validator.on_ban(as_parser(self.json_act()))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.NOT_ALLOWED)

    def test_ban_owner(self):
        self.set_owner()
        is_valid, code, msg = self.validator.on_ban(as_parser(self.json_act()))
        self.assertTrue(is_valid)

    def test_ban_owner_no_id_of_user_to_kick(self):
        self.set_owner()
        act = self.json_act()
        del act['object']['id']
        is_valid, code, msg = self.validator.on_ban(as_parser(act))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.MISSING_OBJECT_ID)

    def test_ban_owner_no_such_room(self):
        self.set_owner()
        act = self.json_act()
        act['target']['id'] = str(uuid())
        is_valid, code, msg = self.validator.on_ban(as_parser(act))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.NO_SUCH_ROOM)

    def test_global_ban_owner_not_admin(self):
        self.set_owner()
        act = self.json_act()
        del act['target']['id']
        is_valid, code, msg = self.validator.on_ban(as_parser(act))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.NOT_ALLOWED)

    def test_global_ban_is_admin(self):
        self.set_admin()
        act = self.json_act()
        del act['target']['id']
        is_valid, code, msg = self.validator.on_ban(as_parser(act))
        self.assertTrue(is_valid)

    def test_global_ban_is_super_user(self):
        self.set_super_user()
        act = self.json_act()
        del act['target']['id']
        is_valid, code, msg = self.validator.on_ban(as_parser(act))
        self.assertTrue(is_valid)

    def set_super_user(self):
        FakeDb._super_users.add(RequestBanTest.USER_ID)

    def set_admin(self):
        FakeDb._admins[RequestBanTest.CHANNEL_ID] = RequestBanTest.USER_ID

    def set_owner(self):
        FakeDb._owners[RequestBanTest.ROOM_ID] = RequestBanTest.USER_ID

    def act(self):
        return as_parser(self.json_act())

    def json_act(self):
        return {
            'actor': {
                'id': RequestBanTest.USER_ID
            },
            'object': {
                'url': RequestBanTest.CHANNEL_ID,
                'id': RequestBanTest.OTHER_USER_ID,
                'summary': '1h'
            },
            'verb': 'ban',
            'target': {
                'id': RequestBanTest.ROOM_ID,
                'objectType': 'room'
            }
        }

    def setUp(self):
        environ.env.db = FakeDb()
        FakeDb._channel_exists = {
            RequestBanTest.CHANNEL_ID: True,
            RequestBanTest.OTHER_CHANNEL_ID: False
        }

        FakeDb._room_exists = {
            RequestBanTest.ROOM_ID: True,
            RequestBanTest.OTHER_ROOM_ID: False
        }

        FakeDb._room_contains = {
            RequestBanTest.ROOM_ID: {
                RequestBanTest.USER_ID
            },
            RequestBanTest.OTHER_ROOM_ID: set()
        }

        FakeDb._channel_for_room = {
            RequestBanTest.ROOM_ID: RequestBanTest.CHANNEL_ID,
            RequestBanTest.OTHER_ROOM_ID: RequestBanTest.OTHER_CHANNEL_ID
        }

        FakeDb._admins = dict()
        FakeDb._super_users = set()

        FakeDb._owners = {
            RequestBanTest.ROOM_ID: ''
        }

        FakeDb._room_name = {
            RequestBanTest.ROOM_ID: RequestBanTest.ROOM_NAME
        }

        FakeDb._user_names = {
            RequestBanTest.USER_ID: RequestBanTest.USER_NAME
        }

        FakeDb._moderators = {
            RequestBanTest.ROOM_ID: {RequestBanTest.USER_ID},
            RequestBanTest.OTHER_ROOM_ID: {}
        }

        self.auth = AuthRedis(host='mock')
        environ.env.session = {
            SessionKeys.user_id.value: RequestBanTest.USER_ID,
            SessionKeys.user_name.value: RequestBanTest.USER_NAME,
            SessionKeys.age.value: RequestBanTest.AGE,
            SessionKeys.gender.value: RequestBanTest.GENDER,
            SessionKeys.membership.value: RequestBanTest.MEMBERSHIP,
            SessionKeys.image.value: RequestBanTest.IMAGE,
            SessionKeys.has_webcam.value: RequestBanTest.HAS_WEBCAM,
            SessionKeys.fake_checked.value: RequestBanTest.FAKE_CHECKED,
            SessionKeys.country.value: RequestBanTest.COUNTRY,
            SessionKeys.city.value: RequestBanTest.CITY,
            SessionKeys.token.value: RequestBanTest.TOKEN
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
        self.auth.redis.hmset(RedisKeys.auth_key(RequestBanTest.USER_ID), environ.env.session)
        self.validator = RequestValidator()
