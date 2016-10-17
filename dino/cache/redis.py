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

from zope.interface import implementer

from dino.config import RedisKeys
from dino.cache import ICache
from dino.config import ConfigKeys
from dino import environ
from datetime import datetime
from datetime import timedelta

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class MemoryCache(object):
    def __init__(self):
        self.vals = dict()

    def set(self, key, value, ttl=30):
        expires_at = (datetime.now() + timedelta(0, ttl)).timestamp()
        self.vals[key] = (expires_at, value)

    def get(self, key):
        if key not in self.vals:
            return None
        expires_at, value = self.vals[key]
        now = datetime.now().timestamp()
        if now > expires_at:
            del self.vals[key]
            return None
        return value


@implementer(ICache)
class CacheRedis(object):
    USER_STATUS = 'user-status'

    redis = None

    def __init__(self, host: str, port: int = 6379, db: int = 0):
        if environ.env.config.get(ConfigKeys.TESTING, False) or host == 'mock':
            from fakeredis import FakeStrictRedis as Redis
        else:
            from redis import Redis

        self.redis = Redis(host=host, port=port, db=db)
        self.cache = MemoryCache()

    def user_check_status(self, user_id, other_status):
        value = self.cache.get(CacheRedis.USER_STATUS)
        if value is not None:
            return value

        status = self.redis.get(RedisKeys.user_status(user_id))
        if status is None or status == '':
            self.cache.set(CacheRedis.USER_STATUS, RedisKeys.REDIS_STATUS_UNAVAILABLE)
            return True

        user_status = str(status, 'utf-8')
        self.cache.set(CacheRedis.USER_STATUS, user_status)
        return user_status == other_status

    def user_is_offline(self, user_id):
        return self.user_check_status(user_id, RedisKeys.REDIS_STATUS_UNAVAILABLE)

    def user_is_online(self, user_id):
        return self.user_check_status(user_id, RedisKeys.REDIS_STATUS_AVAILABLE)

    def user_is_invisible(self, user_id):
        return self.user_check_status(user_id, RedisKeys.REDIS_STATUS_INVISIBLE)

    def set_user_offline(self, user_id: str) -> None:
        self.cache.set(CacheRedis.USER_STATUS, RedisKeys.REDIS_STATUS_UNAVAILABLE)
        self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 0)
        self.redis.srem(RedisKeys.online_set(), int(user_id))
        self.redis.srem(RedisKeys.users_multi_cast(), user_id)
        self.redis.set(RedisKeys.user_status(user_id), RedisKeys.REDIS_STATUS_UNAVAILABLE)

    def set_user_online(self, user_id: str) -> None:
        self.cache.set(CacheRedis.USER_STATUS, RedisKeys.REDIS_STATUS_AVAILABLE)
        self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 1)
        self.redis.sadd(RedisKeys.online_set(), int(user_id))
        self.redis.sadd(RedisKeys.users_multi_cast(), user_id)
        self.redis.set(RedisKeys.user_status(user_id), RedisKeys.REDIS_STATUS_AVAILABLE)

    def set_user_invisible(self, user_id: str) -> None:
        self.cache.set(CacheRedis.USER_STATUS, RedisKeys.REDIS_STATUS_INVISIBLE)
        self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 0)
        self.redis.srem(RedisKeys.online_set(), int(user_id))
        self.redis.sadd(RedisKeys.users_multi_cast(), user_id)
        self.redis.set(RedisKeys.user_status(user_id), RedisKeys.REDIS_STATUS_INVISIBLE)
