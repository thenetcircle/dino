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
                            'gender'
                        ]
                    }
                },
                'available': {
                    'acls': [
                        'gender'
                    ]
                },
                'validation': {
                    'gender': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('m,f')
                    }
                }
            }
        }
        self.auth.redis.hmset(RedisKeys.auth_key(TestAclValidator.USER_ID), environ.env.session)
        self.validator = AclValidator()

    def test_validate_acl_for_action_join(self):
        is_valid, msg = self.validator.validate_acl_for_action(self.act(), 'room', 'join', self.acls())
        self.assertTrue(is_valid)

    def acls(self):
        return {
            'gender': 'm,f'
        }

    def act(self):
        return as_parser({
            'actor': {
                'id': TestAclValidator.USER_ID
            },
            'verb': 'join',
            'object': {
                'url': TestAclValidator.CHANNEL_ID,
            },
            'target': {
                'id': TestAclValidator.ROOM_ID,
                'objectType': 'group'
            }
        })
