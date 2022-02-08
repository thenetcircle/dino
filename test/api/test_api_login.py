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

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

from test.base import BaseTest
from activitystreams import parse as as_parser

from dino import api
from dino import environ
from dino.config import RedisKeys


class ApiLoginTest(BaseTest):
    def setUp(self):
        super().setUp()
        # self.clear_session()

    def test_login(self):
        self.assert_login_succeeds()

    def test_login_missing_gender(self):
        self.remove_from_auth('gender')
        data = self.activity_for_login(skip={'gender'})
        self.assert_login_succeeds(data)

    def test_login_missing_age(self):
        self.remove_from_auth('age')
        data = self.activity_for_login(skip={'age'})
        self.assert_login_succeeds(data)

    def test_login_missing_image(self):
        self.remove_from_auth('image')
        data = self.activity_for_login(skip={'image'})
        self.assert_login_succeeds(data)

    def test_login_missing_has_webcam(self):
        self.remove_from_auth('has_webcam')
        data = self.activity_for_login(skip={'has_webcam'})
        self.assert_login_succeeds(data)

    def test_login_missing_fake_checked(self):
        self.remove_from_auth('fake_checked')
        data = self.activity_for_login(skip={'fake_checked'})
        self.assert_login_succeeds(data)

    def test_login_missing_city(self):
        self.remove_from_auth('city')
        data = self.activity_for_login(skip={'city'})
        self.assert_login_succeeds(data)

    def test_login_missing_country(self):
        self.remove_from_auth('country')
        data = self.activity_for_login(skip={'country'})
        self.assert_login_succeeds(data)

    def test_login_missing_membership(self):
        self.remove_from_auth('membership')
        data = self.activity_for_login(skip={'membership'})
        self.assert_login_succeeds(data)

    def assert_login_fails(self, data=None):
        self.assertEqual(400, self.response_code_for_login(data))

    def assert_login_succeeds(self, data=None):
        self.assertEqual(200, self.response_code_for_login(data))

    def remove_from_auth(self, key: str):
        auth_key = RedisKeys.auth_key(BaseTest.USER_ID)
        environ.env.auth.redis.hdel(auth_key, key)

    def response_code_for_login(self, data=None):
        return self.login(data)[0]

    def login(self, data=None):
        if data is None:
            data = self.activity_for_login()
        return api.on_login(data, as_parser(data))
