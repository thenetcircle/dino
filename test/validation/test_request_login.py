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

from test.utils import BaseTest
from activitystreams import parse as as_parser

import datetime

from dino import environ
from dino.validation import request
from dino.config import RedisKeys
from dino.config import ConfigKeys
from dino.config import ErrorCodes


class RequestLogintest(BaseTest):
    def setUp(self):
        super(RequestLogintest, self).setUp()
        self.clear_session()
        environ.env.db.redis.hdel(RedisKeys.banned_users(), BaseTest.USER_ID)

    def assert_login_ok(self, act: dict = None):
        if act is None:
            response = request.on_login(as_parser(self.activity_for_login()))[0]
        else:
            response = request.on_login(as_parser(act))[0]
        self.assertTrue(response)

    def assert_login_not_ok(self, act: dict = None):
        if act is None:
            response = request.on_login(as_parser(self.activity_for_login()))[0]
        else:
            response = request.on_login(as_parser(act))[0]
        self.assertFalse(response)

    def ban_user(self, past=False):
        if past:
            bantime = datetime.datetime.utcnow() - datetime.timedelta(0, 240)  # 4 minutes ago
        else:
            bantime = datetime.datetime.utcnow() + datetime.timedelta(0, 240)  # 4 minutes left

        bantime = bantime.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
        environ.env.db.redis.hset(RedisKeys.banned_users(), BaseTest.USER_ID, 'asdf|%s' % bantime)

    def test_login(self):
        self.assert_login_ok()

    def test_login_is_banned(self):
        self.ban_user()
        is_valid, code, message = request.on_login(as_parser(self.activity_for_login()))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.USER_IS_BANNED)

    """
    def test_login_was_banned(self):
        self.ban_user(past=True)
        is_valid, code, message = request.on_login(as_parser(self.activity_for_login()))
        self.assertTrue(is_valid)
    """

    def test_login_session_contains_user_id(self):
        self.assert_not_in_session('user_id', RequestLogintest.USER_ID)
        self.assert_login_ok()

    def test_login_session_contains_user_name(self):
        self.assert_not_in_session('user_name', RequestLogintest.USER_NAME)
        self.assert_login_ok()

    def test_login_session_contains_gender(self):
        self.assert_not_in_session('gender', RequestLogintest.GENDER)
        self.assert_login_ok()

    def test_login_session_contains_membership(self):
        self.assert_not_in_session('membership', RequestLogintest.MEMBERSHIP)
        self.assert_login_ok()

    def test_login_session_contains_city(self):
        self.assert_not_in_session('city', RequestLogintest.CITY)
        self.assert_login_ok()

    def test_login_session_contains_country(self):
        self.assert_not_in_session('country', RequestLogintest.COUNTRY)
        self.assert_login_ok()

    def test_login_session_contains_fake_checked(self):
        self.assert_not_in_session('fake_checked', RequestLogintest.FAKE_CHECKED)
        self.assert_login_ok()

    def test_login_session_contains_has_webcam(self):
        self.assert_not_in_session('has_webcam', RequestLogintest.HAS_WEBCAM)
        self.assert_login_ok()

    def test_login_session_contains_image(self):
        self.assert_not_in_session('image', RequestLogintest.IMAGE)
        self.assert_login_ok()

    def test_login_session_contains_age(self):
        self.assert_not_in_session('age', RequestLogintest.AGE)
        self.assert_login_ok()

    def test_login_no_attachments(self):
        act = {
            'actor': {
                'id': RequestLogintest.USER_ID,
                'summary': RequestLogintest.USER_NAME,
                'image': {
                    'url': 'http://some-url.com/image.jpg',
                    'width': '120',
                    'height': '120'
                }
            },
            'verb': 'login'
        }
        self.assert_login_not_ok(act)

    def test_login_missing_all_attachments(self):
        act = {
            'actor': {
                'id': RequestLogintest.USER_ID,
                'summary': RequestLogintest.USER_NAME,
                'image': {
                    'url': 'http://some-url.com/image.jpg',
                    'width': '120',
                    'height': '120'
                },
                'attachments': list()
            },
            'verb': 'login'
        }
        self.assert_login_not_ok(act)

    def test_login_missing_user_id(self):
        self.remove_from_auth('user_id')
        act = self.activity_for_login(skip={'user_id'})
        self.assert_login_not_ok(act)

    def test_login_missing_user_name(self):
        self.remove_from_auth('user_name')
        act = self.activity_for_login(skip={'user_name'})
        self.assert_login_not_ok(act)

    def test_login_missing_token(self):
        self.remove_from_auth('token')
        act = self.activity_for_login(skip={'token'})
        self.assert_login_not_ok(act)

    def test_login_missing_gender(self):
        self.remove_from_auth('gender')
        act = self.activity_for_login(skip={'gender'})
        self.assert_login_ok(act)

    def test_login_missing_age(self):
        self.remove_from_auth('age')
        act = self.activity_for_login(skip={'age'})
        self.assert_login_ok(act)

    def test_login_missing_image(self):
        self.remove_from_auth('image')
        act = self.activity_for_login(skip={'image'})
        self.assert_login_ok(act)

    def test_login_missing_has_webcam(self):
        self.remove_from_auth('has_webcam')
        act = self.activity_for_login(skip={'has_webcam'})
        self.assert_login_ok(act)

    def test_login_missing_fake_checked(self):
        self.remove_from_auth('fake_checked')
        act = self.activity_for_login(skip={'fake_checked'})
        self.assert_login_ok(act)

    def test_login_missing_city(self):
        self.remove_from_auth('city')
        act = self.activity_for_login(skip={'city'})
        self.assert_login_ok(act)

    def test_login_missing_country(self):
        self.remove_from_auth('country')
        act = self.activity_for_login(skip={'country'})
        self.assert_login_ok(act)

    def test_login_missing_membership(self):
        self.remove_from_auth('membership')
        act = self.activity_for_login(skip={'membership'})
        self.assert_login_ok(act)

    def remove_from_auth(self, key: str):
        auth_key = RedisKeys.auth_key(BaseTest.USER_ID)
        environ.env.auth.redis.hdel(auth_key, key)
