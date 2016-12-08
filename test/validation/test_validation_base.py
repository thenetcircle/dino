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

from unittest import TestCase
from activitystreams import parse as as_parser
from uuid import uuid4 as uuid

from dino.validation.base import BaseValidator
from dino.environ import ConfigDict
from dino.config import SessionKeys
from dino import environ

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class BaseValidatorTest(TestCase):
    def setUp(self):
        self.validator = BaseValidator()
        environ.env.session = ConfigDict({})
        environ.env.session.set(SessionKeys.user_id.value, '1234')

    def test_id_on_actor(self):
        activity = as_parser(self.get_act())
        valid, reason = self.validator.validate_request(activity)
        self.assertTrue(valid)

    def test_wrong_on_actor(self):
        activity = self.get_act()
        activity['actor']['id'] = '5678'
        activity = as_parser(activity)
        valid, reason = self.validator.validate_request(activity)
        self.assertFalse(valid)

    def test_no_id_on_actor(self):
        activity = self.get_act()
        del activity['actor']['id']
        activity = as_parser(activity)
        valid, reason = self.validator.validate_request(activity)
        self.assertFalse(valid)

    def test_valid_session(self):
        is_valid, reason = self.validator.validate_session({
            'user_id': '1234',
            'user_name': 'Batman',
            'token': str(uuid())
        })
        self.assertTrue(is_valid)

    def test_session_is_missing_user_id(self):
        is_valid, reason = self.validator.validate_session({
            'user_name': 'Batman',
            'token': str(uuid())
        })
        self.assertFalse(is_valid)

    def test_session_is_missing_user_name(self):
        is_valid, reason = self.validator.validate_session({
            'user_id': '1234',
            'token': str(uuid())
        })
        self.assertFalse(is_valid)

    def test_session_is_missing_token(self):
        is_valid, reason = self.validator.validate_session({
            'user_id': '1234',
            'user_name': 'Batman'
        })
        self.assertFalse(is_valid)

    def test_session_is_blank_user_id(self):
        is_valid, reason = self.validator.validate_session({
            'user_id': '',
            'user_name': 'Batman',
            'token': str(uuid())
        })
        self.assertFalse(is_valid)

    def test_session_is_blank_user_name(self):
        is_valid, reason = self.validator.validate_session({
            'user_id': '1234',
            'user_name': '',
            'token': str(uuid())
        })
        self.assertFalse(is_valid)

    def test_session_is_blank_token(self):
        is_valid, reason = self.validator.validate_session({
            'user_id': '1234',
            'user_name': 'Batman',
            'token': ''
        })
        self.assertFalse(is_valid)

    def test_session_is_missing_all(self):
        is_valid, reason = self.validator.validate_session({})
        self.assertFalse(is_valid)

    def get_act(self):
        return {
            'actor': {
                'id': '1234'
            },
            'verb': 'test',
            'target': {
                'id': '4321'
            }
        }
