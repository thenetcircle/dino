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
    def _emit(event, *args, **kwargs):
        pass

    @staticmethod
    def _join_room(room):
        ApiJoinTest.users_in_room.add(ApiJoinTest.USER_ID)

    @staticmethod
    def _leave_room(room):
        ApiJoinTest.users_in_room.remove(ApiJoinTest.USER_ID)

    @staticmethod
    def _send(message, **kwargs):
        pass

    def setUp(self):
        redis.flushall()
        redis.set(rkeys.room_name_for_id(ApiJoinTest.ROOM_ID), ApiJoinTest.ROOM_NAME)
        ApiJoinTest.users_in_room.clear()

        env.emit = ApiJoinTest._emit
        env.join_room = ApiJoinTest._join_room
        env.send = ApiJoinTest._send
        env.leave_room = ApiJoinTest._leave_room
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

    def test_join_missing_actor_id_fails(self):
        activity = self.activity_for_join()
        del activity['actor']['id']
        response = api.on_join(activity)
        self.assertEqual(400, response[0])

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

    def test_join_non_owner_with_all_acls_one_missing(self):
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
        env.session['has_webcam'] = None
        self.assert_join_fails()

    def test_join_invalid_acl_in_redis(self):
        self.set_acl({
            'country': 'de,cn,dk'
        })
        invalid_key = 'invalidstuff'
        env.session[invalid_key] = 't'
        env.redis.hset(rkeys.room_acl(ApiJoinTest.ROOM_ID), invalid_key, 't,r,e,w')
        self.assert_join_fails()

    def test_join_acl_matcher_not_callable(self):
        self.set_acl({
            'country': 'de,cn,dk'
        })
        invalid_key = 'invalidstuff'
        env.session[invalid_key] = 't'
        from gridchat.validator import Validator
        Validator.ACL_MATCHERS[invalid_key] = 'definitely-not-callable'
        env.redis.hset(rkeys.room_acl(ApiJoinTest.ROOM_ID), invalid_key, 't,r,e,w')
        self.assert_join_fails()
        del Validator.ACL_MATCHERS[invalid_key]

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

    def test_join_returns_activity_with_4_attachments(self):
        response = api.on_join(self.activity_for_join())
        self.assertEqual(4, len(response[1]['object']['attachments']))

    def test_join_returns_activity_with_acl_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        acls = self.get_attachment_for_key(attachments, 'acl')
        self.assertIsNotNone(acls)

    def test_join_returns_activity_with_history_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        history = self.get_attachment_for_key(attachments, 'history')
        self.assertIsNotNone(history)

    def test_join_returns_activity_with_owner_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        owners = self.get_attachment_for_key(attachments, 'owner')
        self.assertIsNotNone(owners)

    def test_join_returns_activity_with_users_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        users = self.get_attachment_for_key(attachments, 'user')
        self.assertIsNotNone(users)

    def test_join_returns_activity_with_empty_acl_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        self.assert_attachment_equals(attachments, 'acl', [])

    def test_join_returns_activity_with_empty_history_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        self.assert_attachment_equals(attachments, 'history', [])

    def test_join_returns_activity_with_empty_owner_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        self.assert_attachment_equals(attachments, 'owner', [])

    def test_join_returns_activity_with_one_user_as_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        users = self.get_attachment_for_key(attachments, 'user')
        self.assertEqual(1, len(users))

    def test_join_returns_activity_with_this_user_as_attachment(self):
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        user = self.get_attachment_for_key(attachments, 'user')[0]
        self.assertEqual(ApiJoinTest.USER_ID, user['id'])
        self.assertEqual(ApiJoinTest.USER_NAME, user['content'])

    def test_join_returns_activity_with_one_owner(self):
        self.set_owner()
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        owners = self.get_attachment_for_key(attachments, 'owner')
        self.assertEqual(1, len(owners))

    def test_join_returns_activity_with_correct_owner(self):
        self.set_owner()
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        owners = self.get_attachment_for_key(attachments, 'owner')
        user_id, user_name = owners[0]['id'], owners[0]['content']
        self.assertEqual(ApiJoinTest.USER_ID, user_id)
        self.assertEqual(ApiJoinTest.USER_NAME, user_name)

    def test_join_returns_correct_nr_of_acls(self):
        correct_acls = {'country': 'de,cn,dk', 'city': 'Shanghai,Berlin,Copenhagen'}
        self.set_acl(correct_acls)
        self.set_owner()
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        returned_acls = self.get_attachment_for_key(attachments, 'acl')
        self.assertEqual(len(correct_acls), len(returned_acls))

    def test_join_returns_correct_acls(self):
        correct_acls = {'country': 'de,cn,dk', 'city': 'Shanghai,Berlin,Copenhagen'}
        self.set_acl(correct_acls)
        self.set_owner()
        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        returned_acls = self.get_attachment_for_key(attachments, 'acl')
        for acl in returned_acls:
            acl_key = acl['objectType']
            acl_value = acl['content']
            self.assertTrue(acl_key in correct_acls)
            self.assertEqual(correct_acls[acl_key], acl_value)

    def test_join_returns_history(self):
        msg = 'this is a test message'
        self.set_owner()
        self.assert_join_succeeds()
        self.send_message(msg)
        self.assert_user_in_room(True)
        self.leave_room()
        self.assert_user_in_room(False)

        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        returned_history = self.get_attachment_for_key(attachments, 'history')
        self.assertEqual(1, len(returned_history))

    def test_join_returns_correct_history(self):
        msg = 'this is a test message'
        self.set_owner()
        self.assert_join_succeeds()
        msg_response = self.send_message(msg)[1]
        self.leave_room()

        response = api.on_join(self.activity_for_join())
        attachments = response[1]['object']['attachments']
        history_obj = self.get_attachment_for_key(attachments, 'history')[0]

        self.assertEqual(msg_response['id'], history_obj['id'])
        self.assertEqual(msg, history_obj['content'])
        self.assertEqual(msg_response['published'], history_obj['published'])
        self.assertEqual(ApiJoinTest.USER_NAME, history_obj['summary'])

    def assert_attachment_equals(self, attachments, key, value):
        found = self.get_attachment_for_key(attachments, key)
        self.assertEqual(value, found)

    def get_attachment_for_key(self, attachments, key):
        for attachment in attachments:
            if attachment['objectType'] == key:
                return attachment['attachments']
        return None

    def assert_join_fails(self):
        self.assertEqual(400, self.response_code_for_joining())
        self.assert_user_in_room(False)

    def assert_join_succeeds(self):
        self.assertEqual(200, self.response_code_for_joining())
        self.assert_user_in_room(True)

    def set_owner(self):
        redis.hset(rkeys.room_owners(ApiJoinTest.ROOM_ID), ApiJoinTest.USER_ID, ApiJoinTest.USER_NAME)

    def set_acl(self, acls):
        redis.hmset(rkeys.room_acl(ApiJoinTest.ROOM_ID), acls)

    def assert_user_in_room(self, expected):
        self.assertEqual(expected, ApiJoinTest.USER_ID in ApiJoinTest.users_in_room)

    def response_code_for_joining(self):
        return api.on_join(self.activity_for_join())[0]

    def leave_room(self):
        return api.on_leave(self.activity_for_leave())

    def send_message(self, message: str) -> dict:
        return api.on_message(self.activity_for_message(message))

    def activity_for_message(self, message: str) -> dict:
        return {
            'actor': {
                'id': ApiJoinTest.USER_ID
            },
            'verb': 'send',
            'target': {
                'id': ApiJoinTest.ROOM_ID
            },
            'object': {
                'content': message
            }
        }

    def activity_for_leave(self):
        return {
            'actor': {
                'id': ApiJoinTest.USER_ID,
                'summary': ApiJoinTest.USER_NAME
            },
            'verb': 'leave',
            'target': {
                'id': ApiJoinTest.ROOM_ID
            }
        }

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
