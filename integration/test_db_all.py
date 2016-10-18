#!/usr/bin/env python

# Copyright 2013-2016 DataStax, Inc.
#
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

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

from activitystreams import parse
from uuid import uuid4 as uuid
from datetime import datetime
import time

from dino.environ import ConfigDict

from dino.config import ConfigKeys
from dino.cache.miss import CacheAllMiss

from test.utils import BaseTest


class BaseDatabaseTest(BaseTest):
    class FakeEnv(object):
        def __init__(self):
            self.config = ConfigDict()
            self.cache = CacheAllMiss()

    MESSAGE_ID = str(uuid())

    def set_up_env(self, db):
        self.env = BaseDatabaseTest.FakeEnv()
        self.env.config.set(ConfigKeys.TESTING, False)
        self.env.config.set(ConfigKeys.HOST, 'localhost', domain=ConfigKeys.DATABASE)
        self.env.config.set(ConfigKeys.PORT, 5432, domain=ConfigKeys.DATABASE)
        self.env.config.set(ConfigKeys.DB, 'dinotest', domain=ConfigKeys.DATABASE)
        self.env.config.set(ConfigKeys.USER, 'dinouser', domain=ConfigKeys.DATABASE)
        self.env.config.set(ConfigKeys.PASSWORD, 'dinopass', domain=ConfigKeys.DATABASE)
        self.env.cache.get_room_exists('asdf')

        if db == 'postgres':
            from dino.db.postgres.postgres import DatabasePostgres
            self.db = DatabasePostgres(self.env)
        elif db == 'redis':
            from dino.db.redis import DatabaseRedis
            self.db = DatabaseRedis('localhost:6379')
        else:
            raise ValueError('unknown type %s' % db)

    def act_message(self):
        data = self.activity_for_message()
        data['id'] = BaseDatabaseTest.MESSAGE_ID
        data['target']['objectType'] = 'group'
        data['published'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%SZ')
        return parse(data)

    def act_create(self):
        data = self.activity_for_create()
        data['target']['id'] = BaseTest.ROOM_ID
        data['published'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%SZ')
        return parse(data)

    def _test_room_exists(self):
        self.assertFalse(self.db.room_exists(str(uuid()), str(uuid())))


class DatabasePostgresTest(BaseDatabaseTest):
    """
    def is_admin(self, user_id: str) -> bool
    def get_channels(self) -> dict
    def channel_exists(self, channel_id) -> bool
    def rooms_for_channel(self, channel_id) -> dict
    def room_name_exists(self, channel_id, room_name: str) -> bool
    def room_exists(self, channel_id: str, room_id: str) -> bool
    def room_owners_contain(self, room_id, user_id) -> bool
    def delete_acl(self, room_id: str, acl_type: str) -> None
    def add_acls(self, room_id: str, acls: dict) -> None
    def get_acls(self, room_id: str) -> list
    def rooms_for_user(self, user_id: str = None) -> dict
    def remove_current_rooms_for_user(self, user_id: str) -> None
    def set_user_offline(self, user_id: str) -> None
    def set_user_online(self, user_id: str) -> None
    def set_user_invisible(self, user_id: str) -> None
    """

    def setUp(self):
        self.set_up_env('postgres')

    def test_room_exists(self):
        self._test_room_exists()
