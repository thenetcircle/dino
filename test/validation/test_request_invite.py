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
from activitystreams import parse as as_parser

from dino.validation import request
from dino.exceptions import NoSuchRoomException
from dino.exceptions import NoSuchUserException
from dino.exceptions import NoSuchChannelException
from dino import environ

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class FakeDb:
    _user_names = dict()
    _channel_for_rooms = dict()
    _channel_names = dict()
    _room_names = dict()

    def type_of_rooms_in_channel(self, _):
        return "temporary"

    def get_user_name(self, user_id):
        if user_id not in FakeDb._user_names:
            raise NoSuchUserException(user_id)
        return FakeDb._user_names[user_id]

    def channel_for_room(self, room_id):
        if room_id not in FakeDb._channel_for_rooms:
            raise NoSuchRoomException(room_id)
        return FakeDb._channel_for_rooms[room_id]

    def room_exists(self, channel_id, room_id):
        return room_id in FakeDb._room_names

    def get_channel_name(self, channel_id):
        if channel_id not in FakeDb._channel_names:
            raise NoSuchChannelException(channel_id)
        return FakeDb._channel_names[channel_id]

    def get_room_name(self, room_id):
        if room_id not in FakeDb._room_names:
            raise NoSuchRoomException(room_id)
        return FakeDb._room_names[room_id]


class RequestInviteTest(TestCase):
    ROOM_ID = '8888'
    ROOM_NAME = 'some name'
    CHANNEL_ID = '1234'
    CHANNEL_NAME = 'other name'
    USER_ID = '5432'
    USER_NAME = 'batman'
    OTHER_USER_ID = '9876'
    OTHER_USER_NAME = 'superman'

    def setUp(self):
        environ.env.db = FakeDb()
        FakeDb._user_names = {
            RequestInviteTest.USER_ID: RequestInviteTest.USER_NAME,
            RequestInviteTest.OTHER_USER_ID: RequestInviteTest.OTHER_USER_NAME
        }
        FakeDb._channel_for_rooms = {
            RequestInviteTest.ROOM_ID: RequestInviteTest.CHANNEL_ID
        }
        FakeDb._channel_names = {
            RequestInviteTest.CHANNEL_ID: RequestInviteTest.CHANNEL_NAME
        }
        FakeDb._room_names = {
            RequestInviteTest.ROOM_ID: RequestInviteTest.ROOM_NAME
        }

    def test_invite(self):
        is_valid, code, msg = request.on_invite(as_parser(self.json_act()))
        self.assertTrue(is_valid)

    def json_act(self):
        return {
            'verb': 'invite',
            'actor': {
                'url': RequestInviteTest.ROOM_ID
            },
            'target': {
                'id': RequestInviteTest.OTHER_USER_ID
            }
        }
