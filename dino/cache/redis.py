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

from dino import environ
from dino.config import RedisKeys
from dino.config import ConfigKeys
from dino.config import UserKeys
from dino.cache import ICache
from datetime import datetime
from datetime import timedelta

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class MemoryCache(object):
    def __init__(self):
        self.vals = dict()

    def set(self, key, value, ttl=30):
        try:
            expires_at = (datetime.utcnow() + timedelta(0, ttl)).timestamp()
            self.vals[key] = (expires_at, value)
        except:
            pass

    def get(self, key):
        try:
            if key not in self.vals:
                return None
            expires_at, value = self.vals[key]
            now = datetime.utcnow().timestamp()
            if now > expires_at:
                del self.vals[key]
                return None
            return value
        except:
            return None

    def flushall(self):
        self.vals = dict()


@implementer(ICache)
class CacheRedis(object):
    redis = None

    def __init__(self, host: str, port: int = 6379, db: int = 0):
        if environ.env.config.get(ConfigKeys.TESTING, False) or host == 'mock':
            from fakeredis import FakeStrictRedis as Redis
        else:
            from redis import Redis

        self.redis = Redis(host=host, port=port, db=db)
        self.cache = MemoryCache()

    def _flushall(self):
        self.redis.flushdb()
        self.cache.flushall()

    def _set_ban_timestamp(self, key: str, user_id: str, timestamp: str) -> None:
        cache_key = '%s-%s' % (key, user_id)
        self.cache.set(cache_key, timestamp)
        self.redis.hset(key, user_id, timestamp)

    def set_global_ban_timestamp(self, user_id: str, duration: str, timestamp: str, username: str) -> None:
        key = RedisKeys.banned_users()
        self._set_ban_timestamp(key, user_id, '%s|%s|%s' % (duration, timestamp, username))

    def set_channel_ban_timestamp(self, channel_id: str, user_id: str, duration: str, timestamp: str, username: str) -> None:
        key = RedisKeys.banned_users_channel(channel_id)
        self._set_ban_timestamp(key, user_id, '%s|%s|%s' % (duration, timestamp, username))

    def set_room_ban_timestamp(self, room_id: str, user_id: str, duration: str, timestamp: str, username: str) -> None:
        key = RedisKeys.banned_users(room_id)
        self._set_ban_timestamp(key, user_id, '%s|%s|%s' % (duration, timestamp, username))

    def _get_ban_timestamp(self, key: str, user_id: str) -> str:
        cache_key = '%s-%s' % (key, user_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        ban_info = self.redis.hget(key, user_id)
        if ban_info is None:
            return None

        ban_info = str(ban_info, 'utf-8')
        return ban_info.split('|', 2)

    def get_global_ban_timestamp(self, user_id: str) -> str:
        key = RedisKeys.banned_users()
        return self._get_ban_timestamp(key, user_id)

    def get_channel_ban_timestamp(self, channel_id: str, user_id: str) -> str:
        key = RedisKeys.banned_users_channel(channel_id)
        return self._get_ban_timestamp(key, user_id)

    def get_room_ban_timestamp(self, room_id: str, user_id: str) -> str:
        key = RedisKeys.banned_users(room_id)
        return self._get_ban_timestamp(key, user_id)

    def get_room_id_for_name(self, channel_id: str, room_name: str) -> str:
        key = RedisKeys.room_id_for_name(channel_id)
        cache_key = '%s-%s' % (key, room_name)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        value = self.redis.hget(key, room_name)
        if value is None:
            return None

        value = str(value, 'utf-8')
        self.cache.set(cache_key, value)
        return value

    def set_room_id_for_name(self, channel_id, room_name, room_id):
        key = RedisKeys.room_id_for_name(channel_id)
        cache_key = '%s-%s' % (key, room_name)
        self.cache.set(cache_key, room_id)
        self.redis.hset(key, room_name, room_id)

    def get_user_name(self, user_id: str) -> str:
        key = RedisKeys.user_names()
        cache_key = '%s-%s' % (key, user_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        user_name = self.redis.hget(key, user_id)
        if user_name is not None:
            user_name = str(user_name, 'utf-8')
            self.cache.set(cache_key, user_name)
            return user_name
        return user_name

    def set_user_name(self, user_id: str, user_name: str):
        key = RedisKeys.user_names()
        cache_key = '%s-%s' % (key, user_id)
        user_name = self.redis.hset(key, user_id, user_name)
        self.cache.set(cache_key, user_name)

    def get_room_exists(self, channel_id, room_id):
        key = RedisKeys.rooms(channel_id)
        cache_key = '%s-%s' % (channel_id, room_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return True

        exists = self.redis.hexists(key, room_id)
        if exists == 1:
            self.cache.set(cache_key, True)
            return True
        return None

    def set_room_exists(self, channel_id, room_id, room_name):
        key = RedisKeys.rooms(channel_id)
        cache_key = '%s-%s' % (channel_id, room_id)
        self.cache.set(cache_key, True)
        self.redis.hset(key, room_id, room_name)

    def set_channel_exists(self, channel_id: str) -> None:
        key = RedisKeys.channels()
        cache_key = '%s-%s' % (key, channel_id)
        self.cache.set(cache_key, True)

    def set_channel_for_room(self, channel_id: str, room_id: str) -> None:
        key = RedisKeys.channel_for_rooms()
        cache_key = '%s-%s' % (key, room_id)
        self.cache.set(cache_key, channel_id)

    def get_channel_exists(self, channel_id):
        key = RedisKeys.channels()
        cache_key = '%s-%s' % (key, channel_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        value = self.redis.hget(key, channel_id)
        if value is None:
            return None

        self.cache.set(cache_key, True)
        return True

    def get_channel_name(self, channel_id: str) -> str:
        key = RedisKeys.channels()
        cache_key = '%s-name-%s' % (key, channel_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        value = self.redis.hget(key, channel_id)
        if value is None:
            return None

        self.cache.set(cache_key, value)
        return value

    def get_room_name(self, room_id: str) -> str:
        key = RedisKeys.room_name_for_id()
        cache_key = '%s-%s-name' % (key, room_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        value = self.redis.hget(key, room_id)
        if value is None:
            return None

        self.cache.set(cache_key, value)
        return value

    def get_channel_for_room(self, room_id):
        key = RedisKeys.channel_for_rooms()
        cache_key = '%s-%s' % (key, room_id)
        value = self.cache.get(key)
        if value is not None:
            return value

        channel_id = self.redis.hget(key, room_id)
        if channel_id is None:
            return None

        self.cache.set(cache_key, channel_id)
        return channel_id

    def get_user_status(self, user_id: str):
        key = RedisKeys.user_status(user_id)
        value = self.cache.get(key)
        if value is not None:
            return value

        status = self.redis.get(key)
        if status is None or status == '':
            self.cache.set(key, UserKeys.STATUS_UNAVAILABLE)
            return UserKeys.STATUS_UNAVAILABLE

        user_status = str(status, 'utf-8')
        self.cache.set(key, user_status)
        return user_status

    def user_check_status(self, user_id, other_status):
        return self.get_user_status(user_id) == other_status

    def user_is_offline(self, user_id):
        return self.user_check_status(user_id, UserKeys.STATUS_UNAVAILABLE)

    def user_is_online(self, user_id):
        return self.user_check_status(user_id, UserKeys.STATUS_AVAILABLE)

    def user_is_invisible(self, user_id):
        return self.user_check_status(user_id, UserKeys.STATUS_INVISIBLE)

    def set_user_offline(self, user_id: str) -> None:
        self.cache.set(RedisKeys.user_status(user_id), UserKeys.STATUS_UNAVAILABLE)
        self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 0)
        self.redis.srem(RedisKeys.online_set(), int(user_id))
        self.redis.srem(RedisKeys.users_multi_cast(), user_id)
        self.redis.set(RedisKeys.user_status(user_id), UserKeys.STATUS_UNAVAILABLE)

    def set_user_online(self, user_id: str) -> None:
        self.cache.set(RedisKeys.user_status(user_id), UserKeys.STATUS_AVAILABLE)
        self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 1)
        self.redis.sadd(RedisKeys.online_set(), int(user_id))
        self.redis.sadd(RedisKeys.users_multi_cast(), user_id)
        self.redis.set(RedisKeys.user_status(user_id), UserKeys.STATUS_AVAILABLE)

    def set_user_invisible(self, user_id: str) -> None:
        self.cache.set(RedisKeys.user_status(user_id), UserKeys.STATUS_INVISIBLE)
        self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 0)
        self.redis.srem(RedisKeys.online_set(), int(user_id))
        self.redis.sadd(RedisKeys.users_multi_cast(), user_id)
        self.redis.set(RedisKeys.user_status(user_id), UserKeys.STATUS_INVISIBLE)
