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
from dino.db.manager.channels import ChannelManager

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class FakeDb(object):
    _channel_names = dict()

    def get_channels(self):
        return {ChannelManagerTest.CHANNEL_ID: ChannelManagerTest.CHANNEL_NAME}

    def create_channel(self, name, uuid, user_id):
        pass

    def create_admin_room_for(self, channel_id):
        pass

    def get_channel_name(self, *args):
        return ChannelManagerTest.CHANNEL_NAME

    def rename_channel(self, channel_id, channel_name):
        FakeDb._channel_names[channel_id] = channel_name


class ChannelManagerTest(TestCase):
    CHANNEL_ID = '1234'
    CHANNEL_NAME = 'Shanghai'

    OTHER_CHANNEL_ID = '4321'
    OTHER_CHANNEL_NAME = 'Beijing'

    USER_ID = '5555'

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
        self.assertEqual('', self.manager.create_channel(
                ChannelManagerTest.OTHER_CHANNEL_NAME, ChannelManagerTest.OTHER_CHANNEL_ID, ChannelManagerTest.USER_ID))

    def test_name_for_uuid(self):
        self.assertEqual(ChannelManagerTest.CHANNEL_NAME, self.manager.name_for_uuid(ChannelManagerTest.CHANNEL_ID))

    def test_rename(self):
        self.assertEqual(ChannelManagerTest.CHANNEL_NAME, FakeDb._channel_names[ChannelManagerTest.CHANNEL_ID])
        self.manager.rename(ChannelManagerTest.CHANNEL_ID, 'foobar')
        self.assertEqual('foobar', FakeDb._channel_names[ChannelManagerTest.CHANNEL_ID])

    def test_get_owners(self):
        # TODO
        pass

    def test_get_admins(self):
        # TODO
        pass
