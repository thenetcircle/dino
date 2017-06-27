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
import time

from activitystreams import parse
from uuid import uuid4 as uuid
from datetime import datetime

from test.base import BaseTest
from dino import environ
from dino.config import ConfigKeys
from dino.storage.cassandra import CassandraStorage
from dino.db.redis import DatabaseRedis


class StorageCassandraTest(BaseTest):
    MESSAGE_ID = str(uuid())
    KEY_SPACE = 'testing'

    def setUp(self):
        environ.env.config.set(ConfigKeys.TESTING, False)
        environ.env.logger = logging.getLogger()
        logging.getLogger('cassandra').setLevel(logging.WARNING)
        self.env = environ.env
        self.key_space = StorageCassandraTest.KEY_SPACE
        self.storage = CassandraStorage(hosts=['127.0.0.1'], key_space=self.key_space)
        self.env.db = DatabaseRedis(self.env, host='mock')

        try:
            self.storage.driver.session.execute("use " + self.key_space)
        except Exception as e:
            # keyspace doesn't exist, so the table's doesn't exist either
            self.storage.init()
            return

        self.storage.driver.session.execute("drop materialized view if exists messages_by_id")
        self.storage.driver.session.execute("drop materialized view if exists messages_by_time_stamp")
        self.storage.driver.session.execute("drop table if exists messages")
        self.storage.driver.session.execute("drop keyspace if exists " + self.key_space)
        self.storage.init()

    def tearDown(self):
        self.storage.driver.session.execute("drop materialized view messages_by_id")
        self.storage.driver.session.execute("drop materialized view messages_by_time_stamp")
        self.storage.driver.session.execute("drop table messages")
        self.storage.driver.session.execute("drop keyspace " + self.key_space)

    def test_delete_message(self):
        self.storage.store_message(self.act_message())
        res = self.storage.get_history(BaseTest.ROOM_ID)
        self.assertEqual(1, len(res))
        self.assertFalse(res[0]['deleted'])

        self.storage.delete_message(BaseTest.ROOM_ID, StorageCassandraTest.MESSAGE_ID)
        res = self.storage.get_history(BaseTest.ROOM_ID)
        self.assertEqual(0, len(res))

    def test_history(self):
        self.assertEqual(0, len(self.storage.get_history(BaseTest.ROOM_ID)))

    def test_store_message(self):
        self.storage.store_message(self.act_message())

        res = self.storage.get_history(BaseTest.ROOM_ID)
        self.assertEqual(1, len(res))
        self.assertEqual(BaseTest.USER_ID, res[0]['from_user'])
        self.assertEqual(BaseTest.ROOM_ID, res[0]['to_user'])

    def act_message(self):
        data = self.activity_for_message()
        data['id'] = StorageCassandraTest.MESSAGE_ID
        data['target']['objectType'] = 'group'
        data['published'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%SZ')
        return parse(data)
