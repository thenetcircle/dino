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
from dino.config import ConfigKeys
from dino.rest.resources.banned import BannedResource

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class FakeDb(object):
    _banned = dict()

    def type_of_rooms_in_channel(self, _):
        return "temporary"

    def get_banned_users(self):
        return FakeDb._banned

    def get_mutes_for_user(self, user_id):
        return  {
            'room': {
                'name': RoomsForUsersTest.ROOM_NAME,
                'duration': '5m',
                'timestamp': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
            }
        }

    def get_bans_for_user(self, user_id):
        return  {
            'global': dict(),
            'room': {
                'name': RoomsForUsersTest.ROOM_NAME,
                'duration': '5m',
                'timestamp': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
            },
            'channel': dict()
        }


class FakeRequest(object):
    _json = dict()

    def get_json(self, silent=False):
        return FakeRequest._json


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
        FakeDb._banned = {RoomsForUsersTest.USER_ID}
        self.resource = BannedResource()
        self.resource.request = FakeRequest()
        FakeRequest._json = {
            'users': [RoomsForUsersTest.USER_ID]
        }

    def test_get(self):
        self.assertEqual(1, len(self.resource.do_get()))

    def test_set_last_cleared(self):
        last_cleared = self.resource._get_last_cleared()
        self.resource._set_last_cleared(datetime.utcnow()+timedelta(minutes=5))
        self.assertNotEqual(last_cleared, self.resource._get_last_cleared())

    def test_get_lru_method(self):
        func = self.resource._get_lru_method()
        self.assertTrue(callable(func))
