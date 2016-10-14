from test.utils import BaseTest

from dino import api
from dino import environ
from dino import rkeys
from dino.config import ConfigKeys


class ApiLoginTest(BaseTest):
    def setUp(self):
        super(ApiLoginTest, self).setUp()
        self.clear_session()

    def test_login(self):
        self.assert_login_succeeds()

    def test_login_session_contains_user_id(self):
        self.assert_not_in_session('user_id', ApiLoginTest.USER_ID)
        self.login()
        self.assert_in_session('user_id', ApiLoginTest.USER_ID)

    def test_login_session_contains_user_name(self):
        self.assert_not_in_session('user_name', ApiLoginTest.USER_NAME)
        self.login()
        self.assert_in_session('user_name', ApiLoginTest.USER_NAME)

    def test_login_session_contains_gender(self):
        self.assert_not_in_session('gender', ApiLoginTest.GENDER)
        self.login()
        self.assert_in_session('gender', ApiLoginTest.GENDER)

    def test_login_session_contains_membership(self):
        self.assert_not_in_session('membership', ApiLoginTest.MEMBERSHIP)
        self.login()
        self.assert_in_session('membership', ApiLoginTest.MEMBERSHIP)

    def test_login_session_contains_city(self):
        self.assert_not_in_session('city', ApiLoginTest.CITY)
        self.login()
        self.assert_in_session('city', ApiLoginTest.CITY)

    def test_login_session_contains_country(self):
        self.assert_not_in_session('country', ApiLoginTest.COUNTRY)
        self.login()
        self.assert_in_session('country', ApiLoginTest.COUNTRY)

    def test_login_session_contains_fake_checked(self):
        self.assert_not_in_session('fake_checked', ApiLoginTest.FAKE_CHECKED)
        self.login()
        self.assert_in_session('fake_checked', ApiLoginTest.FAKE_CHECKED)

    def test_login_session_contains_has_webcam(self):
        self.assert_not_in_session('has_webcam', ApiLoginTest.HAS_WEBCAM)
        self.login()
        self.assert_in_session('has_webcam', ApiLoginTest.HAS_WEBCAM)

    def test_login_session_contains_image(self):
        self.assert_not_in_session('image', ApiLoginTest.IMAGE)
        self.login()
        self.assert_in_session('image', ApiLoginTest.IMAGE)

    def test_login_session_contains_age(self):
        self.assert_not_in_session('age', ApiLoginTest.AGE)
        self.login()
        self.assert_in_session('age', ApiLoginTest.AGE)

    def test_login_no_attachments(self):
        data = {
            'actor': {
                'id': ApiLoginTest.USER_ID,
                'summary': ApiLoginTest.USER_NAME,
                'image': {
                    'url': 'http://some-url.com/image.jpg',
                    'width': '120',
                    'height': '120'
                }
            },
            'verb': 'login'
        }
        self.assert_login_fails(data)

    def test_login_missing_all_attachments(self):
        data = {
            'actor': {
                'id': ApiLoginTest.USER_ID,
                'summary': ApiLoginTest.USER_NAME,
                'image': {
                    'url': 'http://some-url.com/image.jpg',
                    'width': '120',
                    'height': '120'
                },
                'attachments': list()
            },
            'verb': 'login'
        }
        self.assert_login_fails(data)

    def test_login_missing_user_id(self):
        self.remove_from_auth('user_id')
        data = self.activity_for_login(skip={'user_id'})
        self.assert_login_fails(data)

    def test_login_missing_user_name(self):
        self.remove_from_auth('user_name')
        data = self.activity_for_login(skip={'user_name'})
        self.assert_login_fails(data)

    def test_login_missing_gender(self):
        self.remove_from_auth('gender')
        data = self.activity_for_login(skip={'gender'})
        self.assert_login_fails(data)

    def test_login_missing_age(self):
        self.remove_from_auth('age')
        data = self.activity_for_login(skip={'age'})
        self.assert_login_fails(data)

    def test_login_missing_image(self):
        self.remove_from_auth('image')
        data = self.activity_for_login(skip={'image'})
        self.assert_login_fails(data)

    def test_login_missing_has_webcam(self):
        self.remove_from_auth('has_webcam')
        data = self.activity_for_login(skip={'has_webcam'})
        self.assert_login_fails(data)

    def test_login_missing_fake_checked(self):
        self.remove_from_auth('fake_checked')
        data = self.activity_for_login(skip={'fake_checked'})
        self.assert_login_fails(data)

    def test_login_missing_city(self):
        self.remove_from_auth('city')
        data = self.activity_for_login(skip={'city'})
        self.assert_login_fails(data)

    def test_login_missing_country(self):
        self.remove_from_auth('country')
        data = self.activity_for_login(skip={'country'})
        self.assert_login_fails(data)

    def test_login_missing_membership(self):
        self.remove_from_auth('membership')
        data = self.activity_for_login(skip={'membership'})
        self.assert_login_fails(data)

    def test_login_missing_token(self):
        self.remove_from_auth('token')
        data = self.activity_for_login(skip={'token'})
        self.assert_login_fails(data)

    def assert_login_fails(self, data=None):
        self.assertEqual(400, self.response_code_for_login(data))
        self.assert_in_own_room(False)

    def assert_login_succeeds(self, data=None):
        self.assertEqual(200, self.response_code_for_login(data))
        self.assert_in_own_room(True)

    def remove_from_auth(self, key: str):
        auth_key = environ.env.config.get(ConfigKeys.REDIS_AUTH_KEY, None)
        if auth_key is None:
            auth_key = rkeys.auth_key(BaseTest.USER_ID)
        else:
            auth_key %= BaseTest.USER_ID
        environ.env.auth.redis.hdel(auth_key, key)

    def response_code_for_login(self, data=None):
        return self.login(data)[0]

    def login(self, data=None):
        if data is None:
            data = self.activity_for_login()
        return api.on_login(data)
