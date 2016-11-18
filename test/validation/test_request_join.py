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
import datetime

from test.utils import BaseTest

from dino.config import ApiActions
from dino.config import ConfigKeys
from dino.config import RedisKeys
from dino.config import ErrorCodes
from dino.validation import request


class RequestJoinTest(BaseTest):
    def setUp(self):
        super(RequestJoinTest, self).setUp()
        self.create_channel_and_room()

    def ban_user(self, past=False):
        if past:
            bantime = datetime.datetime.utcnow() - datetime.timedelta(0, 240)  # 4 minutes ago
        else:
            bantime = datetime.datetime.utcnow() + datetime.timedelta(0, 240)  # 4 minutes left

        bantime = bantime.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
        self.env.db.redis.hset(RedisKeys.banned_users(), BaseTest.USER_ID, 'asdf|%s' % bantime)

    def test_join_non_owner_no_acl(self):
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_missing_actor_id_fails(self):
        activity = self.activity_for_join()
        del activity['actor']['id']
        response = request.on_join(as_parser(activity))
        self.assertEqual(True, response[0])

    def test_join_is_banned(self):
        self.ban_user()
        activity = self.activity_for_join()
        is_valid, code, msg = request.on_join(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.USER_IS_BANNED)

    def test_join_owner_no_acl(self):
        self.set_owner()
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_owner_ignores_acl(self):
        self.set_owner()
        self.set_acl({ApiActions.JOIN: {'age': '18:25'}})
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_too_young(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'age': '35:40'}})
        self.assertEqual(False, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_too_old(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'age': '18:25'}})
        self.assertEqual(False, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_in_age_range(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'age': '18:40'}})
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_wrong_gender(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'gender': 'ts,m'}})
        self.assertEqual(False, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_wrong_membership(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'membership': '1,2'}})
        self.assertEqual(False, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_correct_membership(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'membership': '0,1,2'}})
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_no_image(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'image': 'n'}})
        self.assertEqual(False, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_has_image(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'image': 'y'}})
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_fake_checkede(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'fake_checked': 'y'}})
        self.assertEqual(False, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_not_fake_checked(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'fake_checked': 'n'}})
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_webcam(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'has_webcam': 'y'}})
        self.assertEqual(200, self.response_code_for_joining())
        self.assert_in_room(True)

    def test_join_non_owner_no_webcam(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'has_webcam': 'n'}})
        self.assertEqual(False, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_invalid_acl(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'unknown_acl': 'asdf'}})
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_owner_invalid_acl(self):
        self.set_acl({ApiActions.JOIN: {'unknown_acl': 'asdf'}})
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_owner_wrong_country(self):
        self.set_acl({ApiActions.JOIN: {'country': 'de,dk'}})
        self.set_owner()
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_wrong_country(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'country': 'de,dk'}})
        self.assertEqual(False, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_correct_country(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk'}})
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_owner_correct_country(self):
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk'}})
        self.set_owner()
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_owner_correct_city(self):
        self.set_acl({ApiActions.JOIN: {'city': 'Shanghai,Berlin,Copenhagen'}})
        self.set_owner()
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_correct_city(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'city': 'Shanghai,Berlin,Copenhagen'}})
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_owner_wrong_city(self):
        self.set_acl({ApiActions.JOIN: {'city': 'Berlin,Copenhagen'}})
        self.set_owner()
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_wrong_city(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'city': 'Berlin,Copenhagen'}})
        self.assertEqual(False, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_owner_correct_country_and_city(self):
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk', 'city': 'Shanghai,Berlin,Copenhagen'}})
        self.set_owner()
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_owner_correct_country_wrong_city(self):
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk', 'city': 'Beijing,Berlin,Copenhagen'}})
        self.set_owner()
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_owner_wrong_country_correct_city(self):
        # stupid test, but what the hell; should not be able to set a city in a country that's not allowed anyway
        self.set_acl({ApiActions.JOIN: {'country': 'de,dk', 'city': 'Beijing,Berlin,Copenhagen'}})
        self.set_owner()
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_correct_country_and_city(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk', 'city': 'Shanghai,Berlin,Copenhagen'}})
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_correct_country_wrong_city(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk', 'city': 'Beijing,Berlin,Copenhagen'}})
        self.assertEqual(False, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_wrong_country_correct_city(self):
        self.remove_owner_channel()
        self.remove_owner()
        # stupid test, but what the hell; should not be able to set a city in a country that's not allowed anyway
        self.set_acl({ApiActions.JOIN: {'country': 'de,dk', 'city': 'Beijing,Berlin,Copenhagen'}})
        self.assertEqual(False, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_with_all_acls(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {
            'country': 'de,cn,dk',
            'city': 'Beijing,Shanghai,Berlin,Copenhagen',
            'age': '18:45',
            'gender': 'm,f',
            'membership': '0,1',
            'has_webcam': 'y',
            'fake_checked': 'y,n',
            'image': 'y'
        }})
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_owner_with_all_acls(self):
        self.set_owner()
        self.set_acl({ApiActions.JOIN: {
            'country': 'de,cn,dk',
            'city': 'Beijing,Shanghai,Berlin,Copenhagen',
            'age': '18:45',
            'gender': 'm,f',
            'membership': '0,1',
            'has_webcam': 'y',
            'fake_checked': 'y,n',
            'image': 'n'
        }})
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_with_all_acls_one_incorrect(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {
            'country': 'de,cn,dk',
            'city': 'Beijing,Shanghai,Berlin,Copenhagen',
            'age': '18:45',
            'gender': 'm,f',
            'membership': '0,1',
            'has_webcam': 'y',  # the test user has a webcam, everything else checks out
            'fake_checked': 'y,n',
            'image': 'n'
        }})
        self.assertEqual(False, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_non_owner_with_all_acls_one_missing(self):
        self.remove_owner_channel()
        self.remove_owner()
        self.set_acl({ApiActions.JOIN: {
            'country': 'de,cn,dk',
            'city': 'Beijing,Shanghai,Berlin,Copenhagen',
            'age': '18:45',
            'gender': 'm,f',
            'membership': '0,1',
            'has_webcam': 'y',
            'fake_checked': 'y,n',
            'image': 'n'
        }})
        self.set_session('has_webcam', None)
        self.assertEqual(False, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_invalid_acl_in_redis(self):
        self.set_acl({ApiActions.JOIN: {'country': 'de,cn,dk'}})
        invalid_key = 'invalid|stuff'
        self.set_session(invalid_key, 't')
        self.set_acl_single(invalid_key, 't,r,e,w')
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])

    def test_join_owner_with_all_acls_one_incorrect(self):
        self.set_owner()
        self.set_acl({ApiActions.JOIN: {
            'country': 'de,cn,dk',
            'city': 'Beijing,Shanghai,Berlin,Copenhagen',
            'age': '18:45',
            'gender': 'm,f',
            'membership': '0,1',
            'has_webcam': 'y',
            'fake_checked': 'y,n',
            'image': 'n'
        }})
        self.assertEqual(True, request.on_join(as_parser(self.activity_for_join()))[0])
