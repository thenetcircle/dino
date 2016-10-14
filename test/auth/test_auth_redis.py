from unittest import TestCase
from uuid import uuid4 as uuid

from dino import environ
from dino.auth.redis import AuthRedis
from dino.config import ConfigKeys
from dino.config import SessionKeys

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
        environ.env.session = dict()
        environ.env.session[ConfigKeys.TESTING] = True
        self.auth = AuthRedis(host='mock')
        self.session = {
            SessionKeys.user_id.value: TestAuthRedis.USER_ID,
            SessionKeys.user_name.value: TestAuthRedis.USER_NAME,
            SessionKeys.age.value: TestAuthRedis.AGE,
            SessionKeys.gender.value: TestAuthRedis.GENDER,
            SessionKeys.membership.value: TestAuthRedis.MEMBERSHIP,
            SessionKeys.image.value: TestAuthRedis.IMAGE,
            SessionKeys.has_webcam.value: TestAuthRedis.HAS_WEBCAM,
            SessionKeys.fake_checked.value: TestAuthRedis.FAKE_CHECKED,
            SessionKeys.country.value: TestAuthRedis.COUNTRY,
            SessionKeys.city.value: TestAuthRedis.CITY,
            SessionKeys.token.value: TestAuthRedis.TOKEN
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
        del self.session[SessionKeys.fake_checked.value]
        self.auth.redis.hdel(AuthRedis.DEFAULT_AUTH_KEY % TestAuthRedis.USER_ID, SessionKeys.fake_checked.value)

        *rest, error_msg, session = self.auth.authenticate_and_populate_session(
            TestAuthRedis.USER_ID, TestAuthRedis.TOKEN)
        self.assertEqual(self.session, session)
