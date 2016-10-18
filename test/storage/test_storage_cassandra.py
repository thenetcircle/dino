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
from activitystreams import parse
from uuid import uuid4 as uuid
from datetime import datetime
import time

from test.utils import BaseTest

from dino import environ
from dino.config import ConfigKeys
from dino.storage.cassandra import CassandraStorage
from dino.db.redis import DatabaseRedis
from test.storage.fake_cassandra import FakeCassandraDriver


class StorageMockCassandraTest(BaseTest):
    def setUp(self):
        environ.env.config.set(ConfigKeys.TESTING, True)
        environ.env.logger = logging.getLogger()
        logging.getLogger('cassandra').setLevel(logging.WARNING)
        self.key_space = 'testing'
        self.storage = CassandraStorage(hosts=['mock'], key_space=self.key_space)
        self.storage.driver = FakeCassandraDriver()
        environ.env.db = DatabaseRedis('mock')

    def test_replications(self):
        self.storage = CassandraStorage(hosts=['mock'], key_space=self.key_space, replications=12)
        self.storage.driver = FakeCassandraDriver()
        self.assertEqual(12, self.storage.replications)

    def test_validate_0_replications(self):
        environ.env.config.set(ConfigKeys.TESTING, False)
        self.assertRaises(ValueError, CassandraStorage.validate, ['localhost'], 0, 'SimpleStrategy')

    def test_validate_negative_replications(self):
        environ.env.config.set(ConfigKeys.TESTING, False)
        self.assertRaises(ValueError, CassandraStorage.validate, ['localhost'], -9, 'SimpleStrategy')

    def test_validate_too_high_replications(self):
        environ.env.config.set(ConfigKeys.TESTING, False)
        self.assertRaises(ValueError, CassandraStorage.validate, ['localhost'], 500, 'SimpleStrategy')

    def test_validate_ok_params(self):
        environ.env.config.set(ConfigKeys.TESTING, False)
        CassandraStorage.validate(['localhost'], 2, 'SimpleStrategy')

    def test_validate_other_strat(self):
        environ.env.config.set(ConfigKeys.TESTING, False)
        CassandraStorage.validate(['localhost'], 2, 'NetworkTopologyStrategy')

    def test_validate_invalid_strat(self):
        environ.env.config.set(ConfigKeys.TESTING, False)
        self.assertRaises(ValueError, CassandraStorage.validate, ['localhost'], 2, 'UnknownStrategy')

    def test_validate_invalid_rep_type(self):
        environ.env.config.set(ConfigKeys.TESTING, False)
        self.assertRaises(ValueError, CassandraStorage.validate, ['localhost'], '2', 'UnknownStrategy')

    def test_validate_invalid_strat_type(self):
        environ.env.config.set(ConfigKeys.TESTING, False)
        self.assertRaises(ValueError, CassandraStorage.validate, ['localhost'], 2, 1)

    def test_history(self):
        self.assertEqual(0, len(self.storage.get_history(BaseTest.ROOM_ID)))

    def test_store_message(self):
        self.storage.store_message(self.act_message())

        res = self.storage.get_history(BaseTest.ROOM_ID)
        self.assertEqual(1, len(res))
        self.assertEqual(BaseTest.USER_ID, res[0]['from_user'])
        self.assertEqual(BaseTest.ROOM_ID, res[0]['to_user'])

    def join(self):
        environ.env.db.join_room(BaseTest.USER_ID, BaseTest.USER_NAME, BaseTest.ROOM_ID, BaseTest.ROOM_NAME)

    def act_message(self):
        data = self.activity_for_message()
        data['id'] = str(uuid())
        data['target']['objectType'] = 'group'
        data['object']['url'] = BaseTest.CHANNEL_ID
        data['published'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%SZ')
        return parse(data)

    def act_create(self):
        data = self.activity_for_create()
        data['target']['id'] = BaseTest.ROOM_ID
        data['published'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%SZ')
        return parse(data)
