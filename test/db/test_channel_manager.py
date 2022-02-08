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
from uuid import uuid4 as uuid

from dino import environ
from dino.db.manager.channels import ChannelManager
from dino.exceptions import NoSuchChannelException
from dino.exceptions import EmptyChannelNameException

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class FakeDb(object):
    _channel_names = dict()

    def type_of_rooms_in_channel(self, _):
        return "temporary"

    def get_channels(self):
        return {ChannelManagerTest.CHANNEL_ID: (ChannelManagerTest.CHANNEL_NAME, 1, 'normal')}

    def create_channel(self, name, uuid, user_id):
        if name is None or len(name.strip()) == 0:
            raise EmptyChannelNameException(uuid)
        pass

    def create_admin_room_for(self, channel_id):
        pass

    def get_channel_name(self, channel_id):
        if channel_id != ChannelManagerTest.CHANNEL_ID:
            raise NoSuchChannelException(channel_id)
        return ChannelManagerTest.CHANNEL_NAME

    def rename_channel(self, channel_id: str, channel_name: str):
        if channel_name is None or len(channel_name.strip()) == 0:
            raise EmptyChannelNameException(channel_id)
        FakeDb._channel_names[channel_id] = channel_name

    def get_owners_channel(self, channel_id):
        if channel_id != ChannelManagerTest.CHANNEL_ID:
            raise NoSuchChannelException(channel_id)
        return {ChannelManagerTest.USER_ID: ChannelManagerTest.USER_NAME}

    def get_admins_channel(self, channel_id):
        if channel_id != ChannelManagerTest.CHANNEL_ID:
            raise NoSuchChannelException(channel_id)
        return {ChannelManagerTest.USER_ID: ChannelManagerTest.USER_NAME}


class ChannelManagerTest(TestCase):
    CHANNEL_ID = '1234'
    CHANNEL_NAME = 'Shanghai'

    OTHER_CHANNEL_ID = '4321'
    OTHER_CHANNEL_NAME = 'Beijing'

    USER_ID = '5555'
    USER_NAME = 'Batman'

    def setUp(self):
        environ.env.db = FakeDb()
        self.manager = ChannelManager(environ.env)
        FakeDb._channel_names[ChannelManagerTest.CHANNEL_ID] = ChannelManagerTest.CHANNEL_NAME

    def test_get_channels_correct_length(self):
        channels = self.manager.get_channels()
        self.assertEqual(1, len(channels))

    def test_get_channels_correct_uuid(self):
        channels = self.manager.get_channels()
        self.assertEqual(ChannelManagerTest.CHANNEL_ID, channels[0]['uuid'])

    def test_get_channels_correct_name(self):
        channels = self.manager.get_channels()
        self.assertEqual(ChannelManagerTest.CHANNEL_NAME, channels[0]['name'])

    def test_create_channel(self):
        self.assertEqual(None, self.manager.create_channel(
                ChannelManagerTest.OTHER_CHANNEL_NAME, ChannelManagerTest.OTHER_CHANNEL_ID, ChannelManagerTest.USER_ID))

    def test_create_channel_empty_name(self):
        value = self.manager.create_channel('', ChannelManagerTest.OTHER_CHANNEL_ID, ChannelManagerTest.USER_ID)
        self.assertEqual(type(value), str)

    def test_name_for_uuid(self):
        self.assertEqual(ChannelManagerTest.CHANNEL_NAME, self.manager.name_for_uuid(ChannelManagerTest.CHANNEL_ID))

    def test_name_for_uuid_no_such_channel(self):
        value = self.manager.name_for_uuid(str(uuid()))
        self.assertEqual(None, value)

    def test_rename(self):
        self.assertEqual(ChannelManagerTest.CHANNEL_NAME, FakeDb._channel_names[ChannelManagerTest.CHANNEL_ID])
        value = self.manager.rename(ChannelManagerTest.CHANNEL_ID, 'foobar')
        self.assertEqual(value, None)
        self.assertEqual('foobar', FakeDb._channel_names[ChannelManagerTest.CHANNEL_ID])

    def test_rename_empty_name(self):
        self.assertEqual(ChannelManagerTest.CHANNEL_NAME, FakeDb._channel_names[ChannelManagerTest.CHANNEL_ID])
        value = self.manager.rename(ChannelManagerTest.CHANNEL_ID, '')
        self.assertEqual(type(value), str)
        self.assertEqual(ChannelManagerTest.CHANNEL_NAME, FakeDb._channel_names[ChannelManagerTest.CHANNEL_ID])

    def test_get_owners(self):
        owners = self.manager.get_owners(ChannelManagerTest.CHANNEL_ID)
        self.assertEqual(1, len(owners))
        self.assertEqual(ChannelManagerTest.USER_ID, owners[0]['uuid'])
        self.assertEqual(ChannelManagerTest.USER_NAME, owners[0]['name'])

    def test_get_owners_no_such_channel(self):
        owners = self.manager.get_owners(str(uuid()))
        self.assertEqual(type(owners), str)

    def test_get_admins(self):
        admins = self.manager.get_admins(ChannelManagerTest.CHANNEL_ID)
        self.assertEqual(1, len(admins))
        self.assertEqual(ChannelManagerTest.USER_ID, admins[0]['uuid'])
        self.assertEqual(ChannelManagerTest.USER_NAME, admins[0]['name'])

    def test_get_admins_no_such_channel(self):
        admins = self.manager.get_admins(str(uuid()))
        self.assertEqual(type(admins), str)

