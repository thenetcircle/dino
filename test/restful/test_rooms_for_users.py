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


class RoomsForUsersTest(TestCase):
    USER_ID = '8888'
    ROOM_ID = '1234'
    ROOM_NAME = 'cool guys'
    CHANNEL_ID = '5555'
    CHANNEL_NAME = 'Shanghai'

    def setUp(self):
        environ.env.db = FakeDb()
        FakeDb._rooms_for_user = {
            RoomsForUsersTest.USER_ID: {
                RoomsForUsersTest.ROOM_ID: RoomsForUsersTest.ROOM_NAME
            }
        }
        self.resource = RoomsForUsersResource()

    def test_get(self):
        self.assertEqual(0, len(self.resource._do_get('1234')))

    def test_get_existing_user(self):
        self.assertEqual(1, len(self.resource._do_get(RoomsForUsersTest.USER_ID)))
