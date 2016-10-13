from unittest import TestCase
from uuid import uuid4 as uuid

from dino.auth.redis import AuthRedis
from dino.env import env
from dino import environ
from dino.env import ConfigKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class TestAuthRedis(TestCase):
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
        env.session = dict()
        env.session[ConfigKeys.TESTING] = True
        self.auth = AuthRedis(host='mock')
        self.session = {
            environ.SessionKeys.user_id.value: TestAuthRedis.USER_ID,
            environ.SessionKeys.user_name.value: TestAuthRedis.USER_NAME,
            environ.SessionKeys.age.value: TestAuthRedis.AGE,
            environ.SessionKeys.gender.value: TestAuthRedis.GENDER,
            environ.SessionKeys.membership.value: TestAuthRedis.MEMBERSHIP,
            environ.SessionKeys.image.value: TestAuthRedis.IMAGE,
            environ.SessionKeys.has_webcam.value: TestAuthRedis.HAS_WEBCAM,
            environ.SessionKeys.fake_checked.value: TestAuthRedis.FAKE_CHECKED,
            environ.SessionKeys.country.value: TestAuthRedis.COUNTRY,
            environ.SessionKeys.city.value: TestAuthRedis.CITY,
            environ.SessionKeys.token.value: TestAuthRedis.TOKEN
        }

        self.auth.redis.hmset(AuthRedis.DEFAULT_AUTH_KEY % TestAuthRedis.USER_ID, self.session)

    def test_auth_with_empty_session(self):
        authenticated, *rest = self.auth.authenticate_and_populate_session('', '')
        self.assertFalse(authenticated)

    def test_auth_with_required_args(self):
        authenticated, *rest = self.auth.authenticate_and_populate_session(TestAuthRedis.USER_ID, TestAuthRedis.TOKEN)
        self.assertTrue(authenticated)

    def test_auth_without_token(self):
        authenticated, *rest = self.auth.authenticate_and_populate_session(TestAuthRedis.USER_ID, '')
        self.assertFalse(authenticated)

    def test_auth_without_user_id(self):
        authenticated, *rest = self.auth.authenticate_and_populate_session('', TestAuthRedis.TOKEN)
        self.assertFalse(authenticated)

    def test_session_gets_populated(self):
        *rest, error_msg, session = self.auth.authenticate_and_populate_session(
            TestAuthRedis.USER_ID, TestAuthRedis.TOKEN)
        self.assertEqual(self.session, session)

    def test_session_gets_populated_remove_one(self):
        del self.session[environ.SessionKeys.fake_checked.value]
        self.auth.redis.hdel(AuthRedis.DEFAULT_AUTH_KEY % TestAuthRedis.USER_ID, environ.SessionKeys.fake_checked.value)

        *rest, error_msg, session = self.auth.authenticate_and_populate_session(
            TestAuthRedis.USER_ID, TestAuthRedis.TOKEN)
        self.assertEqual(self.session, session)
