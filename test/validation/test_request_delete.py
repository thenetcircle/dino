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
from dino.utils import b64e
from dino.auth.redis import AuthRedis
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.config import RedisKeys
from dino.config import ErrorCodes
from dino.validation import RequestValidator
from dino.validation.acl import AclStrInCsvValidator
from dino.validation.acl import AclSameChannelValidator
from dino.validation.acl import AclRangeValidator

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class FakeDb(object):
    _channel_exists = dict()
    _room_exists = dict()
    _room_contains = dict()
    _channel_for_room = dict()
    _moderators = dict()
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

    def is_admin(self, *args):
        return False

    def is_owner(self, *args):
        return False

    def is_owner_channel(self, *args):
        return False

    def is_super_user(self, *args):
        return False

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
        return FakeDb._room_exists[room_id]

    def room_contains(self, room_id, user_id):
        return user_id in FakeDb._room_contains[room_id]


class RequestDeleteTest(TestCase):
    CHANNEL_ID = '8765'
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

    def test_on_delete_is_moderator(self):
        act = self.json_act()
        act['target']['id'] = RequestDeleteTest.ROOM_ID
        is_valid, code, msg = self.validator.on_delete(as_parser(act))
        self.assertTrue(is_valid)

    def test_on_delete_not_moderator(self):
        act = self.json_act()
        act['target']['id'] = RequestDeleteTest.OTHER_ROOM_ID
        is_valid, code, msg = self.validator.on_delete(as_parser(act))
        self.assertEqual(code, ErrorCodes.NOT_ALLOWED)
        self.assertFalse(is_valid)

    def act(self):
        return as_parser(self.json_act())

    def json_act(self):
        return {
            'actor': {
                'id': RequestDeleteTest.USER_ID
            },
            'verb': 'delete',
            'target': {
                'id': RequestDeleteTest.ROOM_ID,
                'objectType': 'room'
            }
        }

    def setUp(self):
        environ.env.db = FakeDb()
        FakeDb._channel_exists = {
            RequestDeleteTest.CHANNEL_ID: True,
            RequestDeleteTest.OTHER_CHANNEL_ID: False
        }

        FakeDb._room_exists = {
            RequestDeleteTest.ROOM_ID: True,
            RequestDeleteTest.OTHER_ROOM_ID: False
        }

        FakeDb._room_contains = {
            RequestDeleteTest.ROOM_ID: {
                RequestDeleteTest.USER_ID
            },
            RequestDeleteTest.OTHER_ROOM_ID: set()
        }

        FakeDb._channel_for_room = {
            RequestDeleteTest.ROOM_ID: RequestDeleteTest.CHANNEL_ID,
            RequestDeleteTest.OTHER_ROOM_ID: RequestDeleteTest.OTHER_CHANNEL_ID
        }

        FakeDb._moderators = {
            RequestDeleteTest.ROOM_ID: {RequestDeleteTest.USER_ID},
            RequestDeleteTest.OTHER_ROOM_ID: {}
        }

        self.auth = AuthRedis(host='mock')
        environ.env.session = {
            SessionKeys.user_id.value: RequestDeleteTest.USER_ID,
            SessionKeys.user_name.value: RequestDeleteTest.USER_NAME,
            SessionKeys.age.value: RequestDeleteTest.AGE,
            SessionKeys.gender.value: RequestDeleteTest.GENDER,
            SessionKeys.membership.value: RequestDeleteTest.MEMBERSHIP,
            SessionKeys.image.value: RequestDeleteTest.IMAGE,
            SessionKeys.has_webcam.value: RequestDeleteTest.HAS_WEBCAM,
            SessionKeys.fake_checked.value: RequestDeleteTest.FAKE_CHECKED,
            SessionKeys.country.value: RequestDeleteTest.COUNTRY,
            SessionKeys.city.value: RequestDeleteTest.CITY,
            SessionKeys.token.value: RequestDeleteTest.TOKEN
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
        self.auth.redis.hmset(RedisKeys.auth_key(RequestDeleteTest.USER_ID), environ.env.session)
        self.validator = RequestValidator()
