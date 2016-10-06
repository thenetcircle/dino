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

import logging

from test.utils import BaseTest
from dino.env import env, ConfigKeys
from dino.storage.cassandra import CassandraStorage


class StorageCassandraTest(BaseTest):
    def setUp(self):
        env.config.set(ConfigKeys.TESTING, False)
        env.logger = logging.getLogger()
        key_space = 'testing'
        self.storage = CassandraStorage(hosts=['127.0.0.1'], key_space=key_space)
        self.storage.session.execute("use " + key_space)
        self.storage.session.execute("drop table if exists messages")
        self.storage.session.execute("drop table if exists rooms")
        self.storage.session.execute("drop table if exists users_in_room_by_user")
        self.storage.session.execute("drop table if exists users_in_room_by_room")
        self.storage.session.execute("drop keyspace if exists " + key_space)
        self.storage.init()

    def test_get_all_rooms(self):
        self.storage.get_all_rooms()
