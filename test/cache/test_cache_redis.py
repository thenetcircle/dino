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
from dino.environ import GNEnvironment, ConfigDict, ConfigKeys
from dino.cache.redis import CacheRedis
from dino.config import RedisKeys
from datetime import datetime, timedelta

import time

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class CacheRedisTest(TestCase):
    class FakeEnv(GNEnvironment):
        def __init__(self):
            super(CacheRedisTest.FakeEnv, self).__init__(None, ConfigDict(), skip_init=True)
            self.config = ConfigDict()
            self.config.set(ConfigKeys.TESTING, True)
            self.cache = CacheRedis(self, 'mock')
            self.session = dict()

    USER_ID = '8888'
    CHANNEL_ID = '1234'
    ROOM_ID = '4321'
    USER_NAME = 'Batman'
    CHANNEL_NAME = 'Shanghai'
    ROOM_NAME = 'cool kids'

    def setUp(self):
        self.env = CacheRedisTest.FakeEnv()
        self.cache = self.env.cache
        self.cache._flushall()

    def test_set_user_status(self):
        self.cache.set_user_status(CacheRedisTest.USER_ID, '1')
        self.assertEqual('1', self.cache.get_user_status(CacheRedisTest.USER_ID))

    def test_user_check_status(self):
        self.assertFalse(self.cache.user_check_status(CacheRedisTest.USER_ID, '1'))
        self.cache.set_user_status(CacheRedisTest.USER_ID, '1')
        self.assertTrue(self.cache.user_check_status(CacheRedisTest.USER_ID, '1'))

    def test_get_not_expired(self):
        self.cache._set('foo', 'bar')
        self.assertEqual('bar', self.cache._get('foo'))

    def test_get_expired(self):
        self.cache._set('foo', 'bar', ttl=0.1)
        self.assertEqual('bar', self.cache._get('foo'))
        time.sleep(0.15)
        self.assertEqual(None, self.cache._get('foo'))

    def test_get_admin_room_after_expired(self):
        self.cache.set_admin_room(CacheRedisTest.ROOM_ID)
        self.assertEqual(CacheRedisTest.ROOM_ID, self.cache.get_admin_room())
        key = RedisKeys.admin_room()
        self.cache._del(key)
        self.assertEqual(CacheRedisTest.ROOM_ID, self.cache.get_admin_room())

    def test_get_global_ban_timestamp_after_expired(self):
        timestamp = str(int((datetime.utcnow() + timedelta(seconds=5*60)).timestamp()))
        duration = '5m'
        self.cache.set_global_ban_timestamp(CacheRedisTest.USER_ID, duration, timestamp, CacheRedisTest.USER_NAME)
        _dur, _time, _name = self.cache.get_global_ban_timestamp(CacheRedisTest.USER_ID)
        self.assertEqual(duration, _dur)
        self.assertEqual(timestamp, _time)
        self.assertEqual(CacheRedisTest.USER_NAME, _name)

        key = RedisKeys.banned_users()
        cache_key = '%s-%s' % (key, CacheRedisTest.USER_ID)
        self.cache._del(cache_key)

        _dur, _time, _name = self.cache.get_global_ban_timestamp(CacheRedisTest.USER_ID)
        self.assertEqual(duration, _dur)
        self.assertEqual(timestamp, _time)
        self.assertEqual(CacheRedisTest.USER_NAME, _name)

    def test_get_room_id_for_name_after_expired(self):
        self.cache.set_room_id_for_name(CacheRedisTest.CHANNEL_ID, CacheRedisTest.ROOM_NAME, CacheRedisTest.ROOM_ID)
        self.assertEqual(
                CacheRedisTest.ROOM_ID,
                self.cache.get_room_id_for_name(CacheRedisTest.CHANNEL_ID, CacheRedisTest.ROOM_NAME))

        key = RedisKeys.room_id_for_name(CacheRedisTest.CHANNEL_ID)
        cache_key = '%s-%s' % (key, CacheRedisTest.ROOM_NAME)
        self.cache._del(cache_key)

        self.assertEqual(
                CacheRedisTest.ROOM_ID,
                self.cache.get_room_id_for_name(CacheRedisTest.CHANNEL_ID, CacheRedisTest.ROOM_NAME))

    def test_get_user_name_after_expired(self):
        self.cache.set_user_name(CacheRedisTest.USER_ID, CacheRedisTest.USER_NAME)
        self.assertEqual(CacheRedisTest.USER_NAME, self.cache.get_user_name(CacheRedisTest.USER_ID))

        key = RedisKeys.user_names()
        cache_key = '%s-%s' % (key, CacheRedisTest.USER_ID)
        self.cache._del(cache_key)

        self.assertEqual(CacheRedisTest.USER_NAME, self.cache.get_user_name(CacheRedisTest.USER_ID))

    def test_get_room_exists_after_expired(self):
        self.assertFalse(self.cache.get_room_exists(CacheRedisTest.CHANNEL_ID, CacheRedisTest.ROOM_ID))
        self.cache.set_room_exists(CacheRedisTest.CHANNEL_ID, CacheRedisTest.ROOM_ID, CacheRedisTest.ROOM_NAME)
        self.assertTrue(self.cache.get_room_exists(CacheRedisTest.CHANNEL_ID, CacheRedisTest.ROOM_ID))

        key = RedisKeys.rooms(CacheRedisTest.CHANNEL_ID)
        cache_key = '%s-%s' % (key, CacheRedisTest.ROOM_ID)
        self.cache._del(cache_key)

        self.assertTrue(self.cache.get_room_exists(CacheRedisTest.CHANNEL_ID, CacheRedisTest.ROOM_ID))

    def test_get_channel_exists_after_expired(self):
        self.assertFalse(self.cache.get_channel_exists(CacheRedisTest.CHANNEL_ID))
        self.cache.set_channel_exists(CacheRedisTest.CHANNEL_ID)
        self.assertTrue(self.cache.get_channel_exists(CacheRedisTest.CHANNEL_ID))

        key = RedisKeys.channel_exists()
        cache_key = '%s-%s' % (key, CacheRedisTest.CHANNEL_ID)
        self.cache._del(cache_key)

        self.assertTrue(self.cache.get_channel_exists(CacheRedisTest.CHANNEL_ID))

    def test_get_channel_name_after_expired(self):
        self.assertIsNone(self.cache.get_channel_name(CacheRedisTest.CHANNEL_ID))
        self.cache.set_channel_name(CacheRedisTest.CHANNEL_ID, CacheRedisTest.CHANNEL_NAME)
        self.assertEqual(CacheRedisTest.CHANNEL_NAME, self.cache.get_channel_name(CacheRedisTest.CHANNEL_ID))

        key = RedisKeys.channels()
        cache_key = '%s-name-%s' % (key, CacheRedisTest.CHANNEL_ID)
        self.cache._del(cache_key)

        self.assertEqual(CacheRedisTest.CHANNEL_NAME, self.cache.get_channel_name(CacheRedisTest.CHANNEL_ID))

    def test_get_user_status_after_expired(self):
        self.assertIsNone(self.cache.get_user_status(CacheRedisTest.USER_ID))
        self.cache.set_user_status(CacheRedisTest.USER_ID, '1')
        self.assertEqual('1', self.cache.get_user_status(CacheRedisTest.USER_ID))

        key = RedisKeys.user_status(CacheRedisTest.USER_ID)
        self.cache._del(key)

        self.assertEqual('1', self.cache.get_user_status(CacheRedisTest.USER_ID))
