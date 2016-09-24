import unittest
import fakeredis
from uuid import uuid4 as uuid
import logging

from gridchat.env import env, ConfigKeys
from gridchat import rkeys

redis = fakeredis.FakeStrictRedis()
env.config = dict()
env.config[ConfigKeys.REDIS] = redis
env.config[ConfigKeys.TESTING] = True
env.config[ConfigKeys.SESSION] = dict()
env.config[ConfigKeys.SESSION]['user_id'] = '1234'

from gridchat import api

logging.basicConfig(level='DEBUG')
logger = logging.getLogger(__name__)


class ApiJoinTest(unittest.TestCase):
    USER_ID = '1234'
    USER_NAME = 'Joe'
    ROOM_ID = str(uuid())
    ROOM_NAME = 'Shanghai'
    AGE = '30'
    GENDER = 'f'
    MEMBERSHIP = '0'
    IMAGE = 'n'
    HAS_WEBCAM = 'y'
    FAKE_CHECKED = 'n'
    COUNTRY = 'cn'
    CITY = 'Shanghai'

    users_in_room = set()

    @staticmethod
    def emit(event, *args, **kwargs):
        pass

    @staticmethod
    def join_room(room):
        ApiJoinTest.users_in_room.add(ApiJoinTest.USER_ID)

    def setUp(self):
        redis.flushall()
        redis.set(rkeys.room_name_for_id(ApiJoinTest.ROOM_ID), ApiJoinTest.ROOM_NAME)
        ApiJoinTest.users_in_room.clear()

        env.emit = ApiJoinTest.emit
        env.join_room = ApiJoinTest.join_room
        env.session = {
            'user_id': ApiJoinTest.USER_ID,
            'user_name': ApiJoinTest.USER_NAME,
            'age': ApiJoinTest.AGE,
            'gender': ApiJoinTest.GENDER,
            'membership': ApiJoinTest.MEMBERSHIP,
            'image': ApiJoinTest.IMAGE,
            'fake_checked': ApiJoinTest.FAKE_CHECKED,
            'has_webcam': ApiJoinTest.HAS_WEBCAM,
            'city': ApiJoinTest.CITY,
            'country': ApiJoinTest.COUNTRY
        }

        env.redis = redis

    def test_join_non_owner_no_acl(self):
        self.assert_join_succeeds()

    def test_join_owner_no_acl(self):
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_owner_ignores_acl(self):
        self.set_owner()
        self.set_acl({'age': '18:25'})
        self.assert_join_succeeds()

    def test_join_non_owner_too_young(self):
        self.set_acl({'age': '35:40'})
        self.assert_join_fails()

    def test_join_non_owner_too_old(self):
        self.set_acl({'age': '18:25'})
        self.assert_join_fails()

    def test_join_non_owner_in_age_range(self):
        self.set_acl({'age': '18:40'})
        self.assert_join_succeeds()

    def test_join_non_owner_wrong_gender(self):
        self.set_acl({'gender': 'ts,m'})
        self.assert_join_fails()

    def test_join_non_owner_wrong_membership(self):
        self.set_acl({'membership': '1,2'})
        self.assert_join_fails()

    def test_join_non_owner_correct_membership(self):
        self.set_acl({'membership': '0,1,2'})
        self.assert_join_succeeds()

    def test_join_non_owner_no_image(self):
        self.set_acl({'image': 'y'})
        self.assert_join_fails()

    def test_join_non_owner_has_image(self):
        self.set_acl({'image': 'n'})
        self.assert_join_succeeds()

    def test_join_non_owner_fake_checkede(self):
        self.set_acl({'fake_checked': 'y'})
        self.assert_join_fails()

    def test_join_non_owner_not_fake_checked(self):
        self.set_acl({'fake_checked': 'n'})
        self.assert_join_succeeds()

    def test_join_non_owner_webcam(self):
        self.set_acl({'has_webcam': 'y'})
        self.assertEqual(200, self.response_code_for_joining())
        self.assert_user_in_room(True)

    def test_join_non_owner_no_webcam(self):
        self.set_acl({'has_webcam': 'n'})
        self.assert_join_fails()

    def test_join_non_owner_invalid_acl(self):
        self.set_acl({'unknown_acl': 'asdf'})
        self.assert_join_fails()

    def test_join_owner_invalid_acl(self):
        self.set_acl({'unknown_acl': 'asdf'})
        self.assert_join_fails()

    def test_join_owner_wrong_country(self):
        self.set_acl({'country': 'de,dk'})
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_non_owner_wrong_country(self):
        self.set_acl({'country': 'de,dk'})
        self.assert_join_fails()

    def test_join_non_owner_correct_country(self):
        self.set_acl({'country': 'de,cn,dk'})
        self.assert_join_succeeds()

    def test_join_owner_correct_country(self):
        self.set_acl({'country': 'de,cn,dk'})
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_owner_correct_city(self):
        self.set_acl({'city': 'Shanghai,Berlin,Copenhagen'})
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_non_owner_correct_city(self):
        self.set_acl({'city': 'Shanghai,Berlin,Copenhagen'})
        self.assert_join_succeeds()

    def test_join_owner_wrong_city(self):
        self.set_acl({'city': 'Berlin,Copenhagen'})
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_non_owner_wrong_city(self):
        self.set_acl({'city': 'Berlin,Copenhagen'})
        self.assert_join_fails()

    def test_join_owner_correct_country_and_city(self):
        self.set_acl({'country': 'de,cn,dk', 'city': 'Shanghai,Berlin,Copenhagen'})
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_owner_correct_country_wrong_city(self):
        self.set_acl({'country': 'de,cn,dk', 'city': 'Beijing,Berlin,Copenhagen'})
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_owner_wrong_country_correct_city(self):
        # stupid test, but what the hell; should not be able to set a city in a country that's not allowed anyway
        self.set_acl({'country': 'de,dk', 'city': 'Beijing,Berlin,Copenhagen'})
        self.set_owner()
        self.assert_join_succeeds()

    def test_join_non_owner_correct_country_and_city(self):
        self.set_acl({'country': 'de,cn,dk', 'city': 'Shanghai,Berlin,Copenhagen'})
        self.assert_join_succeeds()

    def test_join_non_owner_correct_country_wrong_city(self):
        self.set_acl({'country': 'de,cn,dk', 'city': 'Beijing,Berlin,Copenhagen'})
        self.assert_join_fails()

    def test_join_non_owner_wrong_country_correct_city(self):
        # stupid test, but what the hell; should not be able to set a city in a country that's not allowed anyway
        self.set_acl({'country': 'de,dk', 'city': 'Beijing,Berlin,Copenhagen'})
        self.assert_join_fails()

    def test_join_non_owner_with_all_acls(self):
        self.set_acl({
            'country': 'de,cn,dk',
            'city': 'Beijing,Shanghai,Berlin,Copenhagen',
            'age': '18:45',
            'gender': 'm,f',
            'membership': '0,1',
            'has_webcam': 'y',
            'fake_checked': 'y,n',
            'image': 'n'
        })
        self.assert_join_succeeds()

    def test_join_owner_with_all_acls(self):
        self.set_acl({
            'country': 'de,cn,dk',
            'city': 'Beijing,Shanghai,Berlin,Copenhagen',
            'age': '18:45',
            'gender': 'm,f',
            'membership': '0,1',
            'has_webcam': 'y',
            'fake_checked': 'y,n',
            'image': 'n'
        })
        self.assert_join_succeeds()

    def test_join_non_owner_with_all_acls_one_incorrect(self):
        self.set_acl({
            'country': 'de,cn,dk',
            'city': 'Beijing,Shanghai,Berlin,Copenhagen',
            'age': '18:45',
            'gender': 'm,f',
            'membership': '0,1',
            'has_webcam': 'n',  # the test user doesn't have a webcam, everything else checks out
            'fake_checked': 'y,n',
            'image': 'n'
        })
        self.assert_join_fails()

    def test_join_owner_with_all_acls_one_incorrect(self):
        self.set_acl({
            'country': 'de,cn,dk',
            'city': 'Beijing,Shanghai,Berlin,Copenhagen',
            'age': '18:45',
            'gender': 'm,f',
            'membership': '0,1',
            'has_webcam': 'y',
            'fake_checked': 'y,n',
            'image': 'n'
        })
        self.assert_join_succeeds()

    def assert_join_fails(self):
        self.assertEqual(400, self.response_code_for_joining())
        self.assert_user_in_room(False)

    def assert_join_succeeds(self):
        self.assertEqual(200, self.response_code_for_joining())
        self.assert_user_in_room(True)

    def set_owner(self):
        redis.sadd(rkeys.room_owners(ApiJoinTest.ROOM_ID), ApiJoinTest.USER_ID)

    def set_acl(self, acls):
        redis.hmset(rkeys.room_acl(ApiJoinTest.ROOM_ID), acls)

    def assert_user_in_room(self, expected):
        self.assertEqual(expected, ApiJoinTest.USER_ID in ApiJoinTest.users_in_room)

    def response_code_for_joining(self):
        return api.on_join(self.activity_for_join())[0]

    def activity_for_join(self):
        return {
            'actor': {
                'id': ApiJoinTest.USER_ID,
                'summary': ApiJoinTest.USER_NAME
            },
            'verb': 'join',
            'target': {
                'id': ApiJoinTest.ROOM_ID
            }
        }
