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
from test.storage.fake_cassandra import FakeCassandraDriver


class StorageMockCassandraTest(BaseTest):
    def setUp(self):
        environ.env.config.set(ConfigKeys.TESTING, True)
        environ.env.logger = logging.getLogger()
        logging.getLogger('cassandra').setLevel(logging.WARNING)
        self.key_space = 'testing'
        self.storage = CassandraStorage(hosts=['mock'], key_space=self.key_space)
        self.storage.driver = FakeCassandraDriver()

    def test_replications(self):
        self.storage = CassandraStorage(hosts=['mock'], key_space=self.key_space, replications=12)
        self.storage.driver = FakeCassandraDriver()
        self.assertEqual(12, self.storage.replications)

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

    def test_remove_current_rooms_for_user(self):
        self.create()
        self.join()

        fetched = self.storage.users_in_room(BaseTest.ROOM_ID)
        self.assertEqual(1, len(fetched))
        self.assertEqual(fetched[0]['user_id'], BaseTest.USER_ID)

        self.storage.remove_current_rooms_for_user(BaseTest.USER_ID)
        fetched = self.storage.users_in_room(BaseTest.ROOM_ID)
        self.assertEqual(0, len(fetched))

    def test_remove_current_rooms_for_user_without_joining(self):
        self.create()
        self.storage.remove_current_rooms_for_user(BaseTest.USER_ID)

    def test_room_exists_without_creating(self):
        self.assertFalse(self.storage.room_exists(BaseTest.ROOM_ID))

    def test_room_exists_after_creating(self):
        self.create()
        self.assertTrue(self.storage.room_exists(BaseTest.ROOM_ID))

    def test_room_name_without_creating(self):
        self.assertFalse(self.storage.room_name_exists(BaseTest.ROOM_NAME))

    def test_room_name_after_creating(self):
        self.create()
        self.assertTrue(self.storage.room_name_exists(BaseTest.ROOM_NAME))

    def test_room_contains_before_creating(self):
        self.assertFalse(self.storage.room_contains(BaseTest.ROOM_ID, BaseTest.USER_ID))

    def test_room_contains_after_creating(self):
        self.create()
        self.assertFalse(self.storage.room_contains(BaseTest.ROOM_ID, BaseTest.USER_ID))

    def test_room_contains_after_joining(self):
        self.create()
        self.join()
        self.assertTrue(self.storage.room_contains(BaseTest.ROOM_ID, BaseTest.USER_ID))

    def test_room_contains_after_joining_other_user(self):
        self.create()
        self.join()
        self.assertFalse(self.storage.room_contains(BaseTest.ROOM_ID, BaseTest.OTHER_USER_ID))

    def test_get_all_rooms_before_creating(self):
        self.assertEqual(0, len(self.storage.get_all_rooms()))

    def test_get_all_rooms_after_creating(self):
        self.create()
        self.assertEqual(1, len(self.storage.get_all_rooms()))

    def test_get_all_rooms_after_joining(self):
        self.create()
        self.join()
        self.assertEqual(1, len(self.storage.get_all_rooms()))

    def test_get_all_rooms_after_joining_one_user(self):
        self.create()
        self.join()
        self.assertEqual(1, len(self.storage.get_all_rooms(BaseTest.USER_ID)))

    def test_get_all_rooms_after_joining_other_user(self):
        self.create()
        self.join()
        self.assertEqual(0, len(self.storage.get_all_rooms(BaseTest.OTHER_USER_ID)))

    def test_get_owners_before_create(self):
        self.assertEqual(0, len(self.storage.get_owners(BaseTest.ROOM_ID)))

    def test_get_owners_after_create(self):
        self.create()
        self.assertEqual(1, len(self.storage.get_owners(BaseTest.ROOM_ID)))
        self.assertEqual(BaseTest.USER_ID, self.storage.get_owners(BaseTest.ROOM_ID)[0]['user_id'])

    def test_get_owners_after_join(self):
        self.create()
        self.join()
        self.assertEqual(1, len(self.storage.get_owners(BaseTest.ROOM_ID)))
        self.assertEqual(BaseTest.USER_ID, self.storage.get_owners(BaseTest.ROOM_ID)[0]['user_id'])

    def test_room_owners_contain_before_create(self):
        self.assertFalse(self.storage.room_owners_contain(BaseTest.ROOM_ID, BaseTest.USER_ID))

    def test_room_owners_contain_after_create(self):
        self.create()
        self.assertTrue(self.storage.room_owners_contain(BaseTest.ROOM_ID, BaseTest.USER_ID))

    def test_room_owners_contain_after_create_other_id(self):
        self.create()
        self.assertFalse(self.storage.room_owners_contain(BaseTest.ROOM_ID, BaseTest.OTHER_USER_ID))

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

    def test_all_acls(self):
        self.create()
        self.join()
        acls = {
            'gender': 'm,f',
            'membership': '0,1,2',
            'has_webcam': 'y',
            'fake_checked': 'y',
            'image': 'n',
            'age': '23:30',
            'city': 'Shanghai,Berlin',
            'country': 'cn,de',
            'group': '1'
        }
        self.storage.add_acls(BaseTest.ROOM_ID, acls)
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
