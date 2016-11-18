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
from dino.validation import RequestValidator
from dino.validation.acl import AclStrInCsvValidator
from dino.validation.acl import AclSameChannelValidator
from dino.validation.acl import AclRangeValidator


class FakeDb(object):
    _channel_exists = dict()
    _room_exists = dict()
    _room_contains = dict()
    _private_rooms = dict()
    _channel_for_room = dict()
    _moderators = dict()
    _owners = dict()
    _admins = dict()
    _super_users = set()
    _channel_owners = dict()

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

    def is_room_private(self, room_id):
        if room_id not in FakeDb._private_rooms:
            return False
        return FakeDb._private_rooms[room_id]

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


class RequestSetAclTest(TestCase):
    OTHER_USER_ID = '9876'
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

    def test_get_acl(self):
        act = self.activity_for_get_acl()
        self.assertTrue(request.on_get_acl(as_parser(act))[0])

    def test_set_room_acls_channel_owner_no_object_type(self):
        self.set_channel_owner()
        acl_type = 'gender'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value,
            'summary': ApiActions.JOIN
        }])
        del activity['target']['objectType']
        is_valid, code, msg = request.on_set_acl(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.INVALID_TARGET_TYPE)

    def test_set_room_acls_channel_owner_empty_summary(self):
        self.set_channel_owner()
        acl_type = 'gender'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value,
            'summary': ''
        }])
        is_valid, code, msg = request.on_set_acl(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.INVALID_ACL_ACTION)

    def test_set_room_acls_channel_owner_wrong_object_type(self):
        self.set_channel_owner()
        acl_type = 'gender'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value,
            'summary': ApiActions.JOIN
        }])
        activity['target']['objectType'] = 'something-invalid'
        is_valid, code, msg = request.on_set_acl(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.INVALID_TARGET_TYPE)

    def test_set_room_acls_channel_owner(self):
        self.set_channel_owner()
        acl_type = 'gender'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value,
            'summary': ApiActions.JOIN
        }])
        is_valid, code, msg = request.on_set_acl(as_parser(activity))
        self.assertTrue(is_valid)

    def test_set_channel_acls_super_user(self):
        self.set_super_user()
        acl_type = 'gender'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value,
            'summary': ApiActions.JOIN
        }])
        activity['target']['id'] = RequestSetAclTest.CHANNEL_ID
        activity['target']['objectType'] = 'channel'
        is_valid, code, msg = request.on_set_acl(as_parser(activity))
        self.assertTrue(is_valid)

    def test_set_room_acls_super_user(self):
        self.set_super_user()
        acl_type = 'gender'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value,
            'summary': ApiActions.JOIN
        }])
        is_valid, code, msg = request.on_set_acl(as_parser(activity))
        self.assertTrue(is_valid)

    def test_set_channel_acls_owner(self):
        self.set_channel_owner()
        acl_type = 'gender'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value,
            'summary': ApiActions.JOIN
        }])
        activity['target']['id'] = RequestSetAclTest.CHANNEL_ID
        activity['target']['objectType'] = 'channel'
        is_valid, code, msg = request.on_set_acl(as_parser(activity))
        self.assertTrue(is_valid)

    def test_set_channel_acls_admin(self):
        self.set_channel_admin()
        acl_type = 'gender'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value,
            'summary': ApiActions.JOIN
        }])
        activity['target']['id'] = RequestSetAclTest.CHANNEL_ID
        activity['target']['objectType'] = 'channel'
        is_valid, code, msg = request.on_set_acl(as_parser(activity))
        self.assertTrue(is_valid)

    def test_set_channel_acls_not_allowed(self):
        acl_type = 'gender'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value,
            'summary': ApiActions.JOIN
        }])
        activity['target']['id'] = RequestSetAclTest.CHANNEL_ID
        activity['target']['objectType'] = 'channel'
        is_valid, code, msg = request.on_set_acl(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.NOT_ALLOWED)

    def test_set_acl_not_owner_returns_code_400(self):
        acl_type = 'gender'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value,
            'summary': ApiActions.JOIN
        }])

        self.remove_owner()
        is_valid, code, msg = request.on_set_acl(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.NOT_ALLOWED)

    def test_set_acl_unknown_type(self):
        acl_type = 'unknown'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value
        }])

        is_valid, code, msg = request.on_set_acl(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.INVALID_ACL_TYPE)

    def test_set_acl_invalid_value(self):
        acl_type = 'gender'
        acl_value = 'm,999'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value,
            'summary': ApiActions.JOIN
        }])

        is_valid, code, msg = request.on_set_acl(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.INVALID_ACL_VALUE)

    def test_set_acl_two_acl(self):
        acl_tuples = [('gender', 'm,f'), ('age', '23:25')]
        attachments = list()
        for acl_type, acl_value in acl_tuples:
            attachments.append({'objectType': acl_type, 'content': acl_value, 'summary': ApiActions.JOIN})

        is_valid, code, msg = request.on_set_acl(as_parser(self.activity_for_set_acl(attachments)))
        self.assertTrue(is_valid)

    def test_set_acl_remove(self):
        activity = self.activity_for_set_acl([{
            'objectType': 'gender',
            'content': '',
            'summary': ApiActions.JOIN
        }])

        is_valid, code, msg = request.on_set_acl(as_parser(activity))
        self.assertTrue(is_valid)

    def remove_owner(self):
        FakeDb._owners[RequestSetAclTest.ROOM_ID] = None

    def set_super_user(self):
        FakeDb._super_users.add(RequestSetAclTest.USER_ID)

    def set_owner(self):
        FakeDb._owners[RequestSetAclTest.ROOM_ID] = RequestSetAclTest.USER_ID

    def set_channel_owner(self):
        FakeDb._channel_owners[RequestSetAclTest.CHANNEL_ID] = {RequestSetAclTest.USER_ID}

    def set_channel_admin(self):
        FakeDb._admins[RequestSetAclTest.CHANNEL_ID] = {RequestSetAclTest.USER_ID}

    def activity_for_get_acl(self):
        return {
            'actor': {
                'id': RequestSetAclTest.USER_ID
            },
            'target': {
                'id': RequestSetAclTest.ROOM_ID,
                'objectType': 'room'
            },
            'verb': 'list'
        }

    def activity_for_set_acl(self, attachments: list=None):
        if attachments is None:
            attachments = [{
                'objectType': 'gender',
                'content': 'm,f',
                'summary': ApiActions.JOIN
            }]

        return {
            'actor': {
                'id': RequestSetAclTest.USER_ID
            },
            'target': {
                'id': RequestSetAclTest.ROOM_ID,
                'objectType': 'room'
            },
            'verb': 'set',
            'object': {
                'objectType': 'acl',
                'attachments': attachments
            }
        }

    def setUp(self):
        environ.env.db = FakeDb()
        FakeDb._channel_exists = {
            RequestSetAclTest.CHANNEL_ID: True,
            RequestSetAclTest.OTHER_CHANNEL_ID: False
        }

        FakeDb._room_exists = {
            RequestSetAclTest.ROOM_ID: True,
            RequestSetAclTest.OTHER_ROOM_ID: False
        }

        FakeDb._room_contains = {
            RequestSetAclTest.ROOM_ID: {
                RequestSetAclTest.USER_ID
            },
            RequestSetAclTest.OTHER_ROOM_ID: set()
        }

        FakeDb._private_rooms = {
            RequestSetAclTest.ROOM_ID: False,
            RequestSetAclTest.OTHER_ROOM_ID: True
        }

        FakeDb._channel_for_room = {
            RequestSetAclTest.ROOM_ID: RequestSetAclTest.CHANNEL_ID,
            RequestSetAclTest.OTHER_ROOM_ID: RequestSetAclTest.OTHER_CHANNEL_ID
        }

        FakeDb._admins = dict()
        FakeDb._super_users = set()
        FakeDb._channel_owners = dict()

        FakeDb._owners = {
            RequestSetAclTest.ROOM_ID: ''
        }

        FakeDb._moderators = {
            RequestSetAclTest.ROOM_ID: {RequestSetAclTest.USER_ID},
            RequestSetAclTest.OTHER_ROOM_ID: {}
        }

        self.auth = AuthRedis(host='mock')
        environ.env.session = {
            SessionKeys.user_id.value: RequestSetAclTest.USER_ID,
            SessionKeys.user_name.value: RequestSetAclTest.USER_NAME,
            SessionKeys.age.value: RequestSetAclTest.AGE,
            SessionKeys.gender.value: RequestSetAclTest.GENDER,
            SessionKeys.membership.value: RequestSetAclTest.MEMBERSHIP,
            SessionKeys.image.value: RequestSetAclTest.IMAGE,
            SessionKeys.has_webcam.value: RequestSetAclTest.HAS_WEBCAM,
            SessionKeys.fake_checked.value: RequestSetAclTest.FAKE_CHECKED,
            SessionKeys.country.value: RequestSetAclTest.COUNTRY,
            SessionKeys.city.value: RequestSetAclTest.CITY,
            SessionKeys.token.value: RequestSetAclTest.TOKEN
        }

        self.set_owner()

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
        self.auth.redis.hmset(RedisKeys.auth_key(RequestSetAclTest.USER_ID), environ.env.session)
        self.validator = RequestValidator()
