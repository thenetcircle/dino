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

from datetime import datetime
from datetime import timedelta
from unittest import TestCase
from uuid import uuid4 as uuid
from activitystreams import parse as as_parser

from dino import environ
from dino import utils
from dino.config import ConfigKeys
from dino.config import ApiActions
from dino.exceptions import NoOriginRoomException
from dino.exceptions import NoTargetRoomException
from dino.exceptions import NoTargetChannelException
from dino.exceptions import NoOriginChannelException
from dino.validation.acl import AclRangeValidator
from dino.validation.acl import AclSameChannelValidator
from dino.validation.acl import AclStrInCsvValidator
from dino.validation.acl import AclDisallowValidator


class FakeDb(object):
    _room_contains = dict()
    _moderators = dict()
    _owners = dict()
    _admins = dict()
    _super_users = set()
    _channel_owners = dict()
    _global_moderators = dict()

    _bans = {
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

    _channel_names = dict()

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

    def is_global_moderator(self, user_id):
        return user_id in FakeDb._global_moderators

    def is_moderator(self, room_id, user_id):
        return room_id in FakeDb._moderators and user_id in FakeDb._moderators[room_id]

    def room_contains(self, room_id, user_id):
        if room_id not in FakeDb._room_contains:
            return False
        return user_id in FakeDb._room_contains[room_id]

    def set_user_name(self, user_id, user_name):
        pass

    def get_user_ban_status(self, room_id, user_id):
        return FakeDb._bans

    def get_channel_name(self, channel_id):
        if channel_id not in FakeDb._channel_names:
            return None
        return FakeDb._channel_names[channel_id]

    def get_acls_in_channel_for_action(self, channel_id, action):
        if action not in FakeDb._channel_acls:
            return dict()
        return FakeDb._channel_acls[action]

    def get_acls_in_room_for_action(self, room_id: str, action: str):
        if action not in FakeDb._room_acls:
            return dict()
        return FakeDb._room_acls[action]

    def get_admin_room(self, *args):
        return BaseWithDb.ROOM_ID

    def channel_for_room(self, *args):
        return BaseWithDb.CHANNEL_ID

    def get_last_read_timestamp(self, *args):
        return datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)


class BaseWithDb(TestCase):
    OTHER_USER_ID = '9876'
    CHANNEL_ID = '8765'
    CHANNEL_NAME = 'Shanghai'
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

    def remove_owner(self):
        FakeDb._owners[BaseWithDb.ROOM_ID] = None

    def set_super_user(self):
        FakeDb._super_users.add(BaseWithDb.USER_ID)

    def set_owner(self):
        FakeDb._owners[BaseWithDb.ROOM_ID] = BaseWithDb.USER_ID

    def set_moderator(self):
        FakeDb._moderators[BaseWithDb.ROOM_ID] = BaseWithDb.USER_ID

    def set_channel_owner(self):
        FakeDb._channel_owners[BaseWithDb.CHANNEL_ID] = {BaseWithDb.USER_ID}

    def set_channel_admin(self):
        FakeDb._admins[BaseWithDb.CHANNEL_ID] = {BaseWithDb.USER_ID}

    def setUp(self):
        environ.env.db = FakeDb()

        FakeDb._room_contains = {
            BaseWithDb.ROOM_ID: {
                BaseWithDb.USER_ID
            },
            BaseWithDb.OTHER_ROOM_ID: set()
        }

        FakeDb._bans = {
            'global': '',
            'channel': '',
            'room': ''
        }

        FakeDb._room_acls = dict()
        FakeDb._channel_acls = dict()

        FakeDb._admins = dict()
        FakeDb._super_users = set()
        FakeDb._channel_owners = dict()
        FakeDb._owners = dict()
        FakeDb._moderators = dict()

        FakeDb._channel_names = {
            BaseWithDb.CHANNEL_ID: BaseWithDb.CHANNEL_NAME
        }

        environ.env.config = {
            ConfigKeys.ACL: {
                'room': {
                    'crossroom': {
                        'acls': [
                            'samechannel',
                            'disallow'
                        ]
                    },
                    'message': {
                        'acls': [
                            'gender',
                            'age',
                            'country',
                        ]
                    }
                },
                'channel': {
                    'crossroom': {
                        'acls': [
                            'samechannel',
                            'disallow'
                        ]
                    },
                    'message': {
                        'acls': [
                            'gender',
                            'age',
                            'country'
                        ]
                    }
                },
                'available': {
                    'acls': [
                        'gender',
                        'age',
                        'samechannel',
                        'disallow'
                    ]
                },
                'validation': {
                    'disallow': {
                        'type': 'disallow',
                        'value': AclDisallowValidator()
                    },
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

    def ban_user(self, past=False, target='channel'):
        if past:
            bantime = datetime.utcnow() - timedelta(0, 240)  # 4 minutes ago
        else:
            bantime = datetime.utcnow() + timedelta(0, 240)  # 4 minutes left

        bantime = str(bantime.timestamp()).split('.')[0]
        FakeDb._bans[target] = bantime


class UtilsBase64Test(TestCase):
    def setUp(self):
        self.b64 = 'YXNkZg=='
        self.plain = 'asdf'

    def test_b64e(self):
        self.assertEqual(self.b64, utils.b64e(self.plain))

    def test_b64e_blank(self):
        self.assertEqual('', utils.b64e(''))

    def test_b64e_none(self):
        self.assertEqual('', utils.b64e(None))

    def test_b64d(self):
        self.assertEqual(self.plain, utils.b64d(self.b64))

    def test_b64d_blank(self):
        self.assertEqual('', utils.b64d(''))

    def test_b64d_none(self):
        self.assertEqual('', utils.b64d(None))

    def test_b64d_invalid(self):
        self.assertEqual('', utils.b64d('åäåö'))


class UtilsActivityForTest(TestCase):
    def test_activity_for_user_banned(self):
        self.assertIsNotNone(utils.activity_for_user_banned('1', '2', '3', '4', '5', '6'))

    def test_activity_for_user_kicked(self):
        self.assertIsNotNone(utils.activity_for_user_kicked('1', '2', '3', '4', '5', '6'))

    def test_activity_for_request_admin(self):
        self.assertIsNotNone(utils.activity_for_request_admin('1', '2', '3', '4', '5', '6'))

    def test_activity_for_list_channels(self):
        channels = {'id': 'namne', 'other-id': 'other-name'}
        self.assertIsNotNone(utils.activity_for_list_channels(None, channels))

    def test_activity_for_invite(self):
        self.assertIsNotNone(utils.activity_for_invite('1', '2', '3', '4', '5', '6'))

    def test_activity_for_whisper(self):
        self.assertIsNotNone(utils.activity_for_whisper('1', '2', '3', '4', '5', '6', '7'))


class UtilsSmallFunctionsTest(BaseWithDb):
    def setUp(self):
        super(UtilsSmallFunctionsTest, self).setUp()

    def test_is_user_in_room(self):
        self.assertTrue(utils.is_user_in_room(BaseWithDb.USER_ID, BaseWithDb.ROOM_ID))

    def test_is_user_in_room_blank_room(self):
        self.assertFalse(utils.is_user_in_room(BaseWithDb.USER_ID, ''))

    def test_set_name_for_user_id(self):
        utils.set_name_for_user_id(BaseWithDb.USER_ID, BaseWithDb.USER_NAME)

    def test_is_not_banned(self):
        is_banned, msg = utils.is_banned(BaseWithDb.USER_ID, BaseWithDb.ROOM_ID)
        self.assertFalse(is_banned)

    def test_is_banned_channel(self):
        self.ban_user(target='channel')
        is_banned, msg = utils.is_banned(BaseWithDb.USER_ID, BaseWithDb.ROOM_ID)
        self.assertTrue(is_banned)

    def test_is_banned_room(self):
        self.ban_user(target='room')
        is_banned, msg = utils.is_banned(BaseWithDb.USER_ID, BaseWithDb.ROOM_ID)
        self.assertTrue(is_banned)

    def test_is_banned_global(self):
        self.ban_user(target='global')
        is_banned, msg = utils.is_banned(BaseWithDb.USER_ID, BaseWithDb.ROOM_ID)
        self.assertTrue(is_banned)

    def test_get_channel_name(self):
        self.assertEqual(BaseWithDb.CHANNEL_NAME, utils.get_channel_name(BaseWithDb.CHANNEL_ID))

    def test_get_admin_room(self):
        self.assertEqual(BaseWithDb.ROOM_ID, utils.get_admin_room())

    def test_owner_is_allowed_to_delete_message(self):
        self.set_owner()
        self.assertTrue(utils.user_is_allowed_to_delete_message(BaseWithDb.ROOM_ID, BaseWithDb.USER_ID))

    def test_admin_is_allowed_to_delete_message(self):
        self.set_channel_admin()
        self.assertTrue(utils.user_is_allowed_to_delete_message(BaseWithDb.ROOM_ID, BaseWithDb.USER_ID))

    def test_moderator_is_allowed_to_delete_message(self):
        self.set_moderator()
        self.assertTrue(utils.user_is_allowed_to_delete_message(BaseWithDb.ROOM_ID, BaseWithDb.USER_ID))

    def test_super_user_is_allowed_to_delete_message(self):
        self.set_super_user()
        self.assertTrue(utils.user_is_allowed_to_delete_message(BaseWithDb.ROOM_ID, BaseWithDb.USER_ID))

    def test_user_is_not_allowed_to_delete_message(self):
        self.assertFalse(utils.user_is_allowed_to_delete_message(BaseWithDb.ROOM_ID, BaseWithDb.USER_ID))

    def test_get_last_read_for(self):
        self.assertIsNotNone(utils.get_last_read_for(BaseWithDb.ROOM_ID, BaseWithDb.USER_ID))


class UtilsCanSendCrossRoomTest(BaseWithDb):
    def json(self):
        return {
            'actor': {
                'id': BaseWithDb.USER_ID
            },
            'object': {
                'url': BaseWithDb.CHANNEL_ID
            },
            'provider': {
                'url': BaseWithDb.CHANNEL_ID
            },
            'target': {
                'objectType': 'room'
            },
            'verb': 'send'
        }

    def test_allowed(self):
        act = self.json()
        FakeDb._channel_acls[ApiActions.CROSSROOM] = {'samechannel': ''}
        allowed = utils.can_send_cross_room(as_parser(act), BaseWithDb.ROOM_ID, BaseWithDb.OTHER_ROOM_ID)
        self.assertTrue(allowed)

    def test_allowed_same_room(self):
        act = self.json()
        FakeDb._channel_acls[ApiActions.CROSSROOM] = {'samechannel': ''}
        allowed = utils.can_send_cross_room(as_parser(act), BaseWithDb.ROOM_ID, BaseWithDb.ROOM_ID)
        self.assertTrue(allowed)

    def test_not_allowed_different_channel(self):
        act = self.json()
        FakeDb._channel_acls[ApiActions.CROSSROOM] = {'samechannel': ''}
        act['provider']['url'] = BaseWithDb.OTHER_CHANNEL_ID
        allowed = utils.can_send_cross_room(as_parser(act), BaseWithDb.ROOM_ID, BaseWithDb.OTHER_ROOM_ID)
        self.assertFalse(allowed)

    def test_no_origin_room(self):
        act = self.json()
        FakeDb._channel_acls[ApiActions.CROSSROOM] = {'samechannel': ''}
        self.assertRaises(NoOriginRoomException, utils.can_send_cross_room, as_parser(act), None, BaseWithDb.OTHER_ROOM_ID)

    def test_no_target_room(self):
        act = self.json()
        FakeDb._channel_acls[ApiActions.CROSSROOM] = {'samechannel': ''}
        self.assertRaises(NoTargetRoomException, utils.can_send_cross_room, as_parser(act), BaseWithDb.ROOM_ID, None)

    def test_not_allowed(self):
        act = self.json()
        FakeDb._channel_acls[ApiActions.CROSSROOM] = {'disallow': ''}
        allowed = utils.can_send_cross_room(as_parser(act), BaseWithDb.ROOM_ID, BaseWithDb.OTHER_ROOM_ID)
        self.assertFalse(allowed)


class UtilsBanDurationTest(TestCase):
    def get_now_plus(self, days=0, hours=0, minutes=0, seconds=0):
        now = datetime.utcnow()
        if minutes != 0:
            seconds += minutes*60
        ban_time = timedelta(days=days, hours=hours, seconds=seconds)
        end_date = now + ban_time
        return str(int(end_date.timestamp()))

    def test_ban_duration_seconds(self):
        expected = self.get_now_plus(seconds=50)
        timestamp = utils.ban_duration_to_timestamp('50s')
        self.assertEqual(expected, timestamp)

    def test_ban_duration_hours(self):
        expected = self.get_now_plus(hours=12)
        timestamp = utils.ban_duration_to_timestamp('12h')
        self.assertEqual(expected, timestamp)

    def test_ban_duration_minutes(self):
        expected = self.get_now_plus(minutes=15)
        timestamp = utils.ban_duration_to_timestamp('15m')
        self.assertEqual(expected, timestamp)

    def test_ban_duration_days(self):
        expected = self.get_now_plus(days=5)
        timestamp = utils.ban_duration_to_timestamp('5d')
        self.assertEqual(expected, timestamp)

    def test_negative_duration(self):
        self.assertRaises(ValueError, utils.ban_duration_to_timestamp, '-5d')

    def test_ban_duration_invalid_unit(self):
        self.assertRaises(ValueError, utils.ban_duration_to_timestamp, '5u')
