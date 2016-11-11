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
from dino.validation import RequestValidator
from dino.validation.acl import AclStrInCsvValidator
from dino.validation.acl import AclSameChannelValidator
from dino.validation.acl import AclRangeValidator

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class FakeDb(object):
    _channel_exists = dict()
    _room_exists = dict()
    _room_contains = dict()

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


class TestRequestValidator(TestCase):
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

    def test_on_message(self):
        is_valid, code, msg = self.validator.on_message(self.act())
        self.assertTrue(is_valid)

    def test_wrong_object_type(self):
        json_act = self.json_act()
        json_act['target']['objectType'] = 'foo'
        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def test_no_room_id(self):
        json_act = self.json_act()
        json_act['target']['id'] = ''
        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def test_no_channel_id(self):
        json_act = self.json_act()
        json_act['object']['url'] = ''
        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def test_channel_does_not_exist(self):
        FakeDb._channel_exists[TestRequestValidator.CHANNEL_ID] = False
        json_act = self.json_act()
        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def test_room_does_not_exist(self):
        FakeDb._room_exists[TestRequestValidator.ROOM_ID] = False
        json_act = self.json_act()
        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def test_origin_room_does_not_exist(self):
        json_act = self.json_act()
        json_act['actor']['url'] = TestRequestValidator.OTHER_ROOM_ID
        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def test_not_in_target_room(self):
        json_act = self.json_act()
        FakeDb._room_contains[TestRequestValidator.ROOM_ID].remove(TestRequestValidator.USER_ID)
        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def test_cross_room_not_same_channel(self):
        json_act = self.json_act()
        json_act['actor']['url'] = TestRequestValidator.ROOM_ID
        json_act['provider'] = dict()
        json_act['provider']['url'] = TestRequestValidator.OTHER_CHANNEL_ID
        json_act['target']['id'] = TestRequestValidator.OTHER_ROOM_ID

        FakeDb._room_exists[TestRequestValidator.OTHER_ROOM_ID] = True
        FakeDb._channel_exists[TestRequestValidator.OTHER_CHANNEL_ID] = True

        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def test_cross_room_same_channel(self):
        json_act = self.json_act()
        json_act['actor']['url'] = TestRequestValidator.ROOM_ID
        json_act['provider'] = dict()
        json_act['provider']['url'] = TestRequestValidator.CHANNEL_ID

        FakeDb._room_exists[TestRequestValidator.OTHER_ROOM_ID] = True
        FakeDb._room_contains[TestRequestValidator.OTHER_ROOM_ID].add(TestRequestValidator.USER_ID)

        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertTrue(is_valid)

    def test_cross_room_same_channel_not_in_origin_room(self):
        json_act = self.json_act()
        json_act['actor']['url'] = TestRequestValidator.ROOM_ID
        json_act['provider'] = dict()
        json_act['provider']['url'] = TestRequestValidator.CHANNEL_ID

        FakeDb._room_exists[TestRequestValidator.OTHER_ROOM_ID] = True
        FakeDb._room_contains[TestRequestValidator.ROOM_ID].remove(TestRequestValidator.USER_ID)

        is_valid, code, msg = self.validator.on_message(as_parser(json_act))
        self.assertFalse(is_valid)

    def act(self):
        return as_parser(self.json_act())

    def json_act(self):
        return {
            'actor': {
                'id': TestRequestValidator.USER_ID
            },
            'verb': 'join',
            'object': {
                'url': TestRequestValidator.CHANNEL_ID,
                'content': b64e('this is the message')
            },
            'target': {
                'id': TestRequestValidator.ROOM_ID,
                'objectType': 'room'
            }
        }

    def setUp(self):
        environ.env.db = FakeDb()
        FakeDb._channel_exists = {
            TestRequestValidator.CHANNEL_ID: True,
            TestRequestValidator.OTHER_CHANNEL_ID: False
        }

        FakeDb._room_exists = {
            TestRequestValidator.ROOM_ID: True,
            TestRequestValidator.OTHER_ROOM_ID: False
        }

        FakeDb._room_contains = {
            TestRequestValidator.ROOM_ID: {
                TestRequestValidator.USER_ID
            },
            TestRequestValidator.OTHER_ROOM_ID: set()
        }

        self.auth = AuthRedis(host='mock')
        environ.env.session = {
            SessionKeys.user_id.value: TestRequestValidator.USER_ID,
            SessionKeys.user_name.value: TestRequestValidator.USER_NAME,
            SessionKeys.age.value: TestRequestValidator.AGE,
            SessionKeys.gender.value: TestRequestValidator.GENDER,
            SessionKeys.membership.value: TestRequestValidator.MEMBERSHIP,
            SessionKeys.image.value: TestRequestValidator.IMAGE,
            SessionKeys.has_webcam.value: TestRequestValidator.HAS_WEBCAM,
            SessionKeys.fake_checked.value: TestRequestValidator.FAKE_CHECKED,
            SessionKeys.country.value: TestRequestValidator.COUNTRY,
            SessionKeys.city.value: TestRequestValidator.CITY,
            SessionKeys.token.value: TestRequestValidator.TOKEN
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
        self.auth.redis.hmset(RedisKeys.auth_key(TestRequestValidator.USER_ID), environ.env.session)
        self.validator = RequestValidator()
