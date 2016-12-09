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

from unittest import TestCase
from datetime import datetime
from datetime import timedelta

from dino import environ
from dino.rest.resources.rooms_for_users import RoomsForUsersResource

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class FakeDb(object):
    _rooms_for_user = dict()

    def rooms_for_user(self, user_id):
        if user_id not in FakeDb._rooms_for_user:
            return dict()
        return FakeDb._rooms_for_user[user_id]

    def channel_for_room(self, *args):
        return RoomsForUsersTest.CHANNEL_ID

    def get_channel_name(self, *args):
        return RoomsForUsersTest.CHANNEL_NAME


class FakeRequest(object):
    should_fail = False

    def get_json(*args, **kwargs):
        if FakeRequest.should_fail:
            raise RuntimeError('testing')

        return {
            'users': [
                RoomsForUsersTest.USER_ID
            ]
        }


class RoomsForUsersTest(TestCase):
    USER_ID = '8888'
    ROOM_ID = '1234'
    ROOM_ID_2 = '4321'
    ROOM_NAME = 'cool guys'
    ROOM_NAME_2 = 'bad guys'
    CHANNEL_ID = '5555'
    CHANNEL_NAME = 'Shanghai'

    def setUp(self):
        environ.env.db = FakeDb()
        FakeDb._rooms_for_user = {
            RoomsForUsersTest.USER_ID: {
                RoomsForUsersTest.ROOM_ID: RoomsForUsersTest.ROOM_NAME,
                RoomsForUsersTest.ROOM_ID_2: RoomsForUsersTest.ROOM_NAME_2
            }
        }
        self.resource = RoomsForUsersResource()
        self.resource.request = FakeRequest()
        FakeRequest.should_fail = False

    def test_do_get_no_cache(self):
        self.assertEqual(0, len(self.resource._do_get('1234')))

    def test_get_existing_user(self):
        self.assertEqual(2, len(self.resource._do_get(RoomsForUsersTest.USER_ID)))

    def test_do_get(self):
        self.assertEqual(1, len(self.resource.do_get()))

    def test_get(self):
        self.assertEqual(1, len(self.resource.get()['data']))

    def test_get_clear_cache(self):
        self.resource.CACHE_CLEAR_INTERVAL = -1
        self.assertEqual(1, len(self.resource.get()['data']))
        self.assertEqual(1, len(self.resource.get()['data']))

    def test_do_get_invalid_json(self):
        FakeRequest.should_fail = True
        self.assertEqual(0, len(self.resource.do_get()))

    def test_set_last_cleared(self):
        last_cleared = self.resource._get_last_cleared()
        self.resource._set_last_cleared(datetime.utcnow()+timedelta(minutes=5))
        self.assertNotEqual(last_cleared, self.resource._get_last_cleared())

    def test_get_lru_method(self):
        func = self.resource._get_lru_method()
        self.assertTrue(callable(func))
