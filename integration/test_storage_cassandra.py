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
from dino.env import env, ConfigKeys
from dino.storage.cassandra import CassandraStorage


class StorageCassandraTest(BaseTest):
    def setUp(self):
        env.config.set(ConfigKeys.TESTING, False)
        env.logger = logging.getLogger()
        logging.getLogger('cassandra').setLevel(logging.WARNING)
        key_space = 'testing'
        self.storage = CassandraStorage(hosts=['127.0.0.1'], key_space=key_space)

        try:
            self.storage.driver.session.execute("use " + key_space)
        except Exception as e:
            # keyspace doesn't exist, so the table's doesn't exist either
            self.storage.init()
            return

        self.storage.driver.session.execute("drop table if exists messages")
        self.storage.driver.session.execute("drop table if exists rooms")
        self.storage.driver.session.execute("drop table if exists acl")
        self.storage.driver.session.execute("drop materialized view if exists users_in_room_by_user")
        self.storage.driver.session.execute("drop table if exists users_in_room")
        self.storage.driver.session.execute("drop keyspace if exists " + key_space)
        self.storage.init()

    def test_get_acl(self):
        self.create()
        self.join()
        self.assertEqual(0, len(self.storage.get_acls(BaseTest.ROOM_ID)))

    def test_set_acl(self):
        self.create()
        self.join()
        acls = {
            'gender': 'm,f',
            'membership': '0,1,2'
        }
        self.storage.add_acls(BaseTest.ROOM_ID, acls)
        fetched = self.storage.get_acls(BaseTest.ROOM_ID)
        self.assertEqual(fetched.items(), acls.items())

    def test_delete_one_acl(self):
        self.create()
        self.join()
        acls = {
            'gender': 'm,f',
            'membership': '0,1,2'
        }
        self.storage.add_acls(BaseTest.ROOM_ID, acls)
        fetched = self.storage.get_acls(BaseTest.ROOM_ID)
        self.assertEqual(fetched.items(), acls.items())
        del acls['gender']

        self.storage.delete_acl(BaseTest.ROOM_ID, 'gender')
        fetched = self.storage.get_acls(BaseTest.ROOM_ID)

        self.assertEqual(fetched.items(), acls.items())

    def test_delete_one_non_existing_acl(self):
        self.create()
        self.join()
        acls = {
            'gender': 'm,f',
            'membership': '0,1,2'
        }
        self.storage.add_acls(BaseTest.ROOM_ID, acls)
        fetched = self.storage.get_acls(BaseTest.ROOM_ID)
        self.assertEqual(fetched.items(), acls.items())

        self.storage.delete_acl(BaseTest.ROOM_ID, 'image')
        fetched = self.storage.get_acls(BaseTest.ROOM_ID)

        self.assertEqual(fetched.items(), acls.items())

    def test_add_one_extra_acl(self):
        self.create()
        self.join()
        acls = {
            'gender': 'm,f',
            'membership': '0,1,2'
        }
        self.storage.add_acls(BaseTest.ROOM_ID, acls)
        fetched = self.storage.get_acls(BaseTest.ROOM_ID)
        self.assertEqual(fetched.items(), acls.items())

        self.storage.add_acls(BaseTest.ROOM_ID, {'image': 'y'})
        acls['image'] = 'y'
        fetched = self.storage.get_acls(BaseTest.ROOM_ID)

        self.assertEqual(fetched.items(), acls.items())

    def test_history(self):
        self.create()
        self.join()
        self.assertEqual(0, len(self.storage.get_history(BaseTest.ROOM_ID)))

    def test_store_message(self):
        self.create()
        self.join()

        self.storage.store_message(self.act_message())

        res = self.storage.get_history(BaseTest.ROOM_ID)
        self.assertEqual(1, len(res))
        self.assertEqual(BaseTest.USER_ID, res[0]['from_user'])
        self.assertEqual(BaseTest.ROOM_ID, res[0]['to_user'])

    def test_no_owners(self):
        self.assertEqual(0, len(self.storage.get_owners(BaseTest.ROOM_ID)))

    def test_owners_after_create(self):
        self.create()

        res = self.storage.get_owners(BaseTest.ROOM_ID)
        self.assertEqual(1, len(res))
        self.assertEqual(BaseTest.USER_ID, res[0]['user_id'])

    def test_get_room_name_non_existing(self):
        self.assertEqual('', self.storage.get_room_name(BaseTest.ROOM_ID))

    def test_get_room_name_after_create(self):
        self.create()
        self.assertEqual(BaseTest.ROOM_NAME, self.storage.get_room_name(BaseTest.ROOM_ID))

    def test_get_all_rooms(self):
        self.assertEqual(0, len(self.storage.get_all_rooms()))

    def test_create_room(self):
        self.create()
        self.assertEqual(1, len(self.storage.get_all_rooms()))

    def test_users_in_room(self):
        self.create()
        self.assertEqual(0, len(self.storage.users_in_room(BaseTest.ROOM_ID)))

    def test_join(self):
        self.create()
        self.join()

        res = self.storage.users_in_room(BaseTest.ROOM_ID)
        self.assertEqual(1, len(res))
        self.assertEqual(BaseTest.USER_ID, res[0]['user_id'])

    def create(self):
        self.storage.create_room(self.act_create())

    def join(self):
        self.storage.join_room(BaseTest.USER_ID, BaseTest.USER_NAME, BaseTest.ROOM_ID, BaseTest.ROOM_NAME)

    def act_message(self):
        data = self.activity_for_message()
        data['id'] = str(uuid())
        data['target']['objectType'] = 'group'
        data['published'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%SZ')
        return parse(data)

    def act_create(self):
        data = self.activity_for_create()
        data['target']['id'] = BaseTest.ROOM_ID
        data['published'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%SZ')
        return parse(data)
