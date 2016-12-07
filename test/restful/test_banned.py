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
from dino.rest.resources.banned import BannedResource

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class FakeDb(object):
    _banned = dict()

    def get_banned_users(self):
        return FakeDb._banned


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

    def test_get(self):
        self.assertEqual(1, len(self.resource.do_get()))

    def test_set_last_cleared(self):
        last_cleared = self.resource._get_last_cleared()
        self.resource._set_last_cleared(datetime.utcnow()+timedelta(minutes=5))
        self.assertNotEqual(last_cleared, self.resource._get_last_cleared())

    def test_get_lru_method(self):
        func = self.resource._get_lru_method()
        self.assertTrue(callable(func))
