#!/usr/bin/env python

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
from dino.validation import AclValidator
from dino.validation.acl import AclStrInCsvValidator
from dino.validation.acl import AclRangeValidator

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class FakeDb(object):
    def is_admin(self, *args):
        return False

    def is_owner(self, *args):
        return False

    def is_owner_channel(self, *args):
        return False

    def is_super_user(self, *args):
        return False


class TestAclValidator(TestCase):
    CHANNEL_ID = '8765'
    ROOM_ID = '4567'
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
        self.auth = AuthRedis(host='mock')
        environ.env.session = {
            SessionKeys.user_id.value: TestAclValidator.USER_ID,
            SessionKeys.user_name.value: TestAclValidator.USER_NAME,
            SessionKeys.age.value: TestAclValidator.AGE,
            SessionKeys.gender.value: TestAclValidator.GENDER,
            SessionKeys.membership.value: TestAclValidator.MEMBERSHIP,
            SessionKeys.image.value: TestAclValidator.IMAGE,
            SessionKeys.has_webcam.value: TestAclValidator.HAS_WEBCAM,
            SessionKeys.fake_checked.value: TestAclValidator.FAKE_CHECKED,
            SessionKeys.country.value: TestAclValidator.COUNTRY,
            SessionKeys.city.value: TestAclValidator.CITY,
            SessionKeys.token.value: TestAclValidator.TOKEN
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
                    }
                },
                'available': {
                    'acls': [
                        'gender',
                        'age'
                    ]
                },
                'validation': {
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
        self.auth.redis.hmset(RedisKeys.auth_key(TestAclValidator.USER_ID), environ.env.session)
        self.validator = AclValidator()

    def test_validate_acl_for_action_join(self):
        is_valid, msg = self.validator.validate_acl_for_action(
                self.act(), 'room', 'join', self.acls_for_room_join())
        self.assertTrue(is_valid)

    def test_validate_acl_for_action_join_country(self):
        is_valid, msg = self.validator.validate_acl_for_action(
                self.act(), 'room', 'join', self.acls_for_room_join_country())
        self.assertTrue(is_valid)

    def test_validate_acl_for_action_join_wrong_country(self):
        environ.env.session[SessionKeys.country.value] = 'xx'
        is_valid, msg = self.validator.validate_acl_for_action(
                self.act(), 'room', 'join', self.acls_for_room_join_country())
        self.assertFalse(is_valid)

    def test_validate_acl_for_action_join_wrong_gender(self):
        environ.env.session[SessionKeys.gender.value] = 'm'
        is_valid, msg = self.validator.validate_acl_for_action(
                self.act(), 'room', 'join', self.acls_for_room_join())
        self.assertFalse(is_valid)

    def test_validate_acl_for_action_message_too_young(self):
        is_valid, msg = self.validator.validate_acl_for_action(
                self.act(), 'room', 'message', self.acls_for_room_message())
        self.assertFalse(is_valid)

    def test_validate_acl_for_action_message_crossroom_same_channel(self):
        json_act = self.json_act()
        other_room_id = str(uuid())
        json_act['actor']['url'] = other_room_id
        is_valid, msg = self.validator.validate_acl_for_action(
                self.act(), 'room', 'message', self.acls_for_room_message())
        self.assertFalse(is_valid)

    def acls_for_room_join(self):
        return {
            'gender': 'f'
        }

    def acls_for_room_join_country(self):
        return {
            'country': 'cn,de'
        }

    def acls_for_room_message(self):
        return {
            'age': '35:'
        }

    def act(self):
        return as_parser(self.json_act())

    def json_act(self):
        return {
            'actor': {
                'id': TestAclValidator.USER_ID
            },
            'verb': 'join',
            'object': {
                'url': TestAclValidator.CHANNEL_ID,
            },
            'target': {
                'id': TestAclValidator.ROOM_ID,
                'objectType': 'room'
            }
        }
