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
from dino.validation import request
from dino.auth.redis import AuthRedis
from dino.config import ApiActions
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.config import RedisKeys
from dino.config import ErrorCodes
from dino.exceptions import NoSuchRoomException
from dino.validation import RequestValidator
from dino.validation.acl import AclStrInCsvValidator
from dino.validation.acl import AclSameRoomValidator
from dino.validation.acl import AclRangeValidator


class FakeDb(object):
    _channel_exists = dict()
    _room_exists = dict()
    _room_contains = dict()
    _channel_for_room = dict()
    _moderators = dict()
    _owners = dict()
    _admins = dict()
    _super_users = set()
    _channel_owners = dict()
    _room_names = dict()

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

    def get_room_name(self, room_id):
        if room_id not in FakeDb._room_names:
            raise NoSuchRoomException(room_id)
        return FakeDb._room_names[room_id]

    def is_admin(self, channel_id, user_id):
        if channel_id not in FakeDb._admins:
            return False

        return user_id in FakeDb._admins[channel_id]

    def is_owner(self, room_id, user_id):
        if room_id not in self._owners:
            return False
        return self._owners[room_id] is not None and user_id in self._owners[room_id]

    def is_owner_channel(self, channel_id, user_id):
        if channel_id not in FakeDb._channel_owners:
            return False
        return FakeDb._channel_owners[channel_id] is not None and user_id in FakeDb._channel_owners[channel_id]

    def is_super_user(self, user_id):
        return user_id in FakeDb._super_users

    def is_moderator(self, room_id, user_id):
        return room_id in FakeDb._moderators and user_id in FakeDb._moderators[room_id]

    def channel_for_room(self, room_id):
        if room_id not in FakeDb._channel_for_room:
            return None
        return FakeDb._channel_for_room[room_id]

    def get_acls_in_channel_for_action(self, channel_id, action):
        if action not in FakeDb._channel_acls:
            return dict()
        return FakeDb._channel_acls[action]

    def get_acls_in_room_for_action(self, room_id: str, action: str):
        if action not in FakeDb._room_acls:
            return dict()
        return FakeDb._room_acls[action]

    def get_user_ban_status(self, room_id: str, user_id: str):
        return FakeDb._ban_status

    def channel_exists(self, channel_id):
        return FakeDb._channel_exists[channel_id]

    def room_exists(self, channel_id, room_id):
        return room_id in FakeDb._room_exists

    def room_contains(self, room_id, user_id):
        if room_id not in FakeDb._room_contains:
            return False
        return user_id in FakeDb._room_contains[room_id]


class RequestKickTest(TestCase):
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

    def test_kick_no_acls_set(self):
        self.remove_owner()
        act = self.json_act()
        is_valid, code, msg = request.on_kick(as_parser(act))
        self.assertTrue(is_valid)

    def test_kick_not_allowed(self):
        self.remove_owner()
        act = self.json_act()
        FakeDb._room_acls[ApiActions.KICK] = {'gender': 'm'}
        is_valid, code, msg = request.on_kick(as_parser(act))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.NOT_ALLOWED)

    def test_kick_not_allowed_in_channel(self):
        self.remove_owner()
        act = self.json_act()
        FakeDb._channel_acls[ApiActions.KICK] = {'gender': 'm'}
        is_valid, code, msg = request.on_kick(as_parser(act))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.NOT_ALLOWED)

    def test_kick_allowed(self):
        self.remove_owner()
        act = self.json_act()
        FakeDb._room_acls[ApiActions.KICK] = {'gender': 'f'}
        is_valid, code, msg = request.on_kick(as_parser(act))
        self.assertTrue(is_valid)

    def test_kick_no_target_id(self):
        self.remove_owner()
        act = self.json_act()
        del act['target']['id']
        is_valid, code, msg = request.on_kick(as_parser(act))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.MISSING_TARGET_ID)

    def test_kick_missing_who_to_kick(self):
        self.remove_owner()
        act = self.json_act()
        del act['object']['id']
        is_valid, code, msg = request.on_kick(as_parser(act))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.MISSING_TARGET_DISPLAY_NAME)

    def test_kick_room_does_not_exist(self):
        self.remove_owner()
        act = self.json_act()
        act['target']['id'] = str(uuid())
        is_valid, code, msg = request.on_kick(as_parser(act))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.NO_SUCH_ROOM)

    def remove_owner(self):
        FakeDb._owners[RequestKickTest.ROOM_ID] = None

    def set_super_user(self):
        FakeDb._super_users.add(RequestKickTest.USER_ID)

    def set_owner(self):
        FakeDb._owners[RequestKickTest.ROOM_ID] = RequestKickTest.USER_ID

    def set_channel_owner(self):
        FakeDb._channel_owners[RequestKickTest.CHANNEL_ID] = {RequestKickTest.USER_ID}

    def set_channel_admin(self):
        FakeDb._admins[RequestKickTest.CHANNEL_ID] = {RequestKickTest.USER_ID}

    def json_act(self):
        return {
            'actor': {
                'id': RequestKickTest.USER_ID,
                'url': RequestKickTest.ROOM_ID
            },
            'object': {
                'id': RequestKickTest.OTHER_USER_ID,
                'url': RequestKickTest.CHANNEL_ID
            },
            'target': {
                'id': RequestKickTest.ROOM_ID,
                'objectType': 'room'
            },
            'verb': 'kick'
        }

    def setUp(self):
        environ.env.db = FakeDb()
        FakeDb._channel_exists = {
            RequestKickTest.CHANNEL_ID: True,
            RequestKickTest.OTHER_CHANNEL_ID: False
        }

        FakeDb._room_exists = {
            RequestKickTest.ROOM_ID: True,
            RequestKickTest.OTHER_ROOM_ID: False
        }

        FakeDb._room_contains = {
            RequestKickTest.ROOM_ID: {
                RequestKickTest.USER_ID
            },
            RequestKickTest.OTHER_ROOM_ID: set()
        }

        FakeDb._channel_for_room = {
            RequestKickTest.ROOM_ID: RequestKickTest.CHANNEL_ID,
            RequestKickTest.OTHER_ROOM_ID: RequestKickTest.OTHER_CHANNEL_ID
        }

        FakeDb._room_names = {
            RequestKickTest.ROOM_ID: RequestKickTest.ROOM_NAME
        }

        FakeDb._admins = dict()
        FakeDb._super_users = set()
        FakeDb._channel_owners = dict()

        FakeDb._room_acls = dict()
        FakeDb._channel_acls = dict()

        FakeDb._owners = {
            RequestKickTest.ROOM_ID: ''
        }

        FakeDb._moderators = {
            RequestKickTest.ROOM_ID: {RequestKickTest.USER_ID},
            RequestKickTest.OTHER_ROOM_ID: {}
        }

        self.auth = AuthRedis(host='mock')
        environ.env.session = {
            SessionKeys.user_id.value: RequestKickTest.USER_ID,
            SessionKeys.user_name.value: RequestKickTest.USER_NAME,
            SessionKeys.age.value: RequestKickTest.AGE,
            SessionKeys.gender.value: RequestKickTest.GENDER,
            SessionKeys.membership.value: RequestKickTest.MEMBERSHIP,
            SessionKeys.image.value: RequestKickTest.IMAGE,
            SessionKeys.has_webcam.value: RequestKickTest.HAS_WEBCAM,
            SessionKeys.fake_checked.value: RequestKickTest.FAKE_CHECKED,
            SessionKeys.country.value: RequestKickTest.COUNTRY,
            SessionKeys.city.value: RequestKickTest.CITY,
            SessionKeys.token.value: RequestKickTest.TOKEN
        }

        self.set_owner()

        environ.env.config = {
            ConfigKeys.ACL: {
                'room': {
                    'kick': {
                        'acls': [
                            'gender',
                            'age',
                            'country',
                        ]
                    }
                },
                'channel': {
                    'kick': {
                        'acls': [
                            'gender',
                            'age',
                            'country',
                            'sameroom'
                        ]
                    }
                },
                'available': {
                    'acls': [
                        'gender',
                        'age',
                        'sameroom'
                    ]
                },
                'validation': {
                    'sameroom': {
                        'type': 'sameroom',
                        'value': AclSameRoomValidator()
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
        self.auth.redis.hmset(RedisKeys.auth_key(RequestKickTest.USER_ID), environ.env.session)
        self.validator = RequestValidator()
