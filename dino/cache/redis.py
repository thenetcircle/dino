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

import json
import logging
import traceback
import random

from zope.interface import implementer

from dino.config import RedisKeys
from dino.config import ConfigKeys
from dino.config import UserKeys
from dino.config import RoleKeys
from dino.cache import ICache
from datetime import datetime
from datetime import timedelta

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

EIGHT_HOURS_IN_SECONDS = 8*60*60
TEN_MINUTES = 10*60
FIVE_MINUTES = 5*60
ONE_MINUTE = 60
ONE_HOUR = 60*60
TEN_SECONDS = 10

logger = logging.getLogger(__name__)


class MemoryCache(object):
    def __init__(self):
        self.vals = dict()

    def set(self, key, value, ttl=30):
        try:
            expires_at = (datetime.utcnow() + timedelta(seconds=ttl)).timestamp()
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

    def delete(self, key):
        if key in self.vals:
            del self.vals[key]

    def flushall(self):
        self.vals = dict()


@implementer(ICache)
class CacheRedis(object):
    redis = None

    def __init__(self, env, host: str, port: int = 6379, db: int = 0):
        if env.config.get(ConfigKeys.TESTING, False) or host == 'mock':
            from fakeredis import FakeStrictRedis as Redis
        else:
            from redis import Redis

        self.redis = Redis(host=host, port=port, db=db)
        self.cache = MemoryCache()

    def _flushall(self) -> None:
        self.redis.flushdb()
        self.cache.flushall()

    def _set(self, key, val, ttl=None) -> None:
        if ttl is None:
            self.cache.set(key, val)
        else:
            self.cache.set(key, val, ttl=ttl)

    def _get(self, key):
        return self.cache.get(key)

    def _del(self, key) -> None:
        self.cache.delete(key)

    def set_type_of_rooms_in_channel(self, channel_id: str, object_type: str) -> None:
        cache_key = RedisKeys.room_types_in_channel(channel_id)
        self.cache.set(cache_key, object_type, ttl=ONE_MINUTE + random.random()*ONE_MINUTE)

    def get_type_of_rooms_in_channel(self, channel_id: str) -> str:
        cache_key = RedisKeys.room_types_in_channel(channel_id)
        return self.cache.get(cache_key)

    def set_is_room_ephemeral(self, room_id: str, is_ephemeral: bool) -> None:
        redis_key = RedisKeys.non_ephemeral_rooms()
        cache_key = '%s-%s' % (redis_key, room_id)
        self.cache.set(cache_key, is_ephemeral)

    def is_room_ephemeral(self, room_id: str) -> bool:
        redis_key = RedisKeys.non_ephemeral_rooms()
        cache_key = '%s-%s' % (redis_key, room_id)
        return self.cache.get(cache_key)

    def set_default_rooms(self, rooms: list) -> None:
        cache_key = RedisKeys.default_rooms()
        self.cache.set(cache_key, rooms, ttl=FIVE_MINUTES)

    def clear_default_rooms(self) -> None:
        redis_key = RedisKeys.default_rooms()
        self.cache.delete(redis_key)

    def get_default_rooms(self) -> list:
        redis_key = RedisKeys.default_rooms()
        value = self.cache.get(redis_key)
        if value is not None:
            return value

        rooms = self.redis.smembers(redis_key)
        if rooms is not None and len(rooms) > 0:
            rooms = [str(room, 'utf-8') for room in rooms]
            self.cache.set(redis_key, rooms, ttl=FIVE_MINUTES)
            return rooms
        return None

    def get_black_list(self) -> set:
        cache_key = RedisKeys.black_list()
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        values = self.redis.smembers(cache_key)
        if value is not None:
            decoded = {str(v, 'utf-8') for v in values}
            self.cache.set(cache_key, decoded, ttl=TEN_MINUTES)
            return decoded
        return None

    def reset_black_list(self) -> None:
        cache_key = RedisKeys.black_list()
        self.cache.delete(cache_key)
        self.redis.delete(cache_key)

    def set_black_list(self, the_list: set) -> None:
        cache_key = RedisKeys.black_list()
        self.cache.set(cache_key, the_list, ttl=TEN_MINUTES)
        self.redis.delete(cache_key)
        self.redis.sadd(cache_key, *the_list)

    def remove_from_black_list(self, word: str) -> None:
        cache_key = RedisKeys.black_list()
        the_cached_list = self.cache.get(cache_key)
        the_cached_list.remove(word)
        self.cache.set(cache_key, the_cached_list, ttl=60*10)
        self.redis.srem(cache_key, word)

    def add_to_black_list(self, word: str) -> None:
        cache_key = RedisKeys.black_list()
        the_cached_list = self.cache.get(cache_key)
        the_cached_list.add(word)
        self.cache.set(cache_key, the_cached_list, ttl=60*10)
        self.redis.sadd(cache_key, word)

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

    def get_user_roles(self, user_id: str) -> None:
        key = RedisKeys.user_roles()
        cache_key = '%s-%s' % (key, user_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        value = self.redis.hget(key, user_id)
        if value is not None:
            value = json.loads(str(value, 'utf-8'))
            self.cache.set(cache_key, value, ttl=TEN_MINUTES + random.random()*FIVE_MINUTES)
        return value

    def set_user_roles(self, user_id: str, roles: dict) -> None:
        key = RedisKeys.user_roles()
        cache_key = '%s-%s' % (key, user_id)
        self.redis.hset(key, user_id, json.dumps(roles))
        self.cache.set(cache_key, roles, ttl=TEN_MINUTES + random.random()*FIVE_MINUTES)

    def reset_user_roles(self, user_id: str) -> None:
        key = RedisKeys.user_roles()
        cache_key = '%s-%s' % (key, user_id)
        self.redis.hdel(key, user_id)
        self.cache.delete(cache_key)

    def get_admin_room(self) -> str:
        key = RedisKeys.admin_room()
        value = self.cache.get(key)
        if value is not None:
            return value

        room_id = self.redis.get(key)
        if room_id is None or len(str(room_id, 'utf-8').strip()) == 0:
            return None

        room_id = str(room_id, 'utf-8')
        self.cache.set(key, room_id, ttl=EIGHT_HOURS_IN_SECONDS)
        return room_id

    def set_admin_room(self, room_id: str) -> None:
        key = RedisKeys.admin_room()
        self.redis.set(key, room_id)
        self.cache.set(key, room_id, ttl=EIGHT_HOURS_IN_SECONDS)

    def remove_admin_room(self) -> None:
        key = RedisKeys.admin_room()
        self.redis.delete(key)
        self.cache.delete(key)

    def _get_ban_timestamp(self, key: str, user_id: str) -> str:
        cache_key = '%s-%s' % (key, user_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value.split('|', 2)

        ban_info = self.redis.hget(key, user_id)
        if ban_info is None:
            return None, None, None

        ban_info = str(ban_info, 'utf-8')
        return ban_info.split('|', 2)

    def get_global_ban_timestamp(self, user_id: str) -> str:
        key = RedisKeys.banned_users()
        return self._get_ban_timestamp(key, user_id)

    def reset_rooms_for_channel(self, channel_id: str) -> None:
        key = RedisKeys.rooms_for_channel_with_info(channel_id)
        self.cache.delete(key)

    def get_rooms_for_channel(self, channel_id: str) -> dict:
        key = RedisKeys.rooms_for_channel_with_info(channel_id)
        return self.cache.get(key)

    def set_rooms_for_channel(self, channel_id: str, rooms_info: dict) -> None:
        key = RedisKeys.rooms_for_channel_with_info(channel_id)
        self.cache.set(key, rooms_info, ttl=FIVE_MINUTES)

    def get_acls_in_room_for_action(self, room_id: str, action: str) -> dict:
        key = RedisKeys.acls_in_room_for_action(room_id, action)
        return self.cache.get(key)

    def set_acls_in_room_for_action(self, room_id: str, action: str, acls: dict) -> None:
        key = RedisKeys.acls_in_room_for_action(room_id, action)
        self.cache.set(key, acls, ttl=TEN_MINUTES + random.random()*TEN_MINUTES)

    def get_acls_in_channel_for_action(self, channel_id: str, action: str) -> dict:
        key = RedisKeys.acls_in_channel_for_action(channel_id, action)
        return self.cache.get(key)

    def get_users_in_room_for_role(self, room_id: str, role: str) -> dict:
        key = RedisKeys.users_in_room_for_role(room_id, role)
        return self.cache.get(key)

    def get_users_in_room(self, room_id: str, is_super_user: bool) -> dict:
        if is_super_user:
            key = RedisKeys.users_in_room_incl_invisible(room_id)
        else:
            key = RedisKeys.users_in_room_only_visible(room_id)
        return self.cache.get(key)

    def set_users_in_room(self, room_id: str, users: dict, is_super_user: bool) -> None:
        if is_super_user:
            key = RedisKeys.users_in_room_incl_invisible(room_id)
        else:
            key = RedisKeys.users_in_room_only_visible(room_id)
        self.cache.set(key, users, ttl=TEN_SECONDS + random.random()*TEN_SECONDS)

    def set_users_in_room_for_role(self, room_id: str, role: str, users: dict) -> None:
        key = RedisKeys.users_in_room_for_role(room_id, role)
        self.cache.set(key, users, ttl=TEN_MINUTES + random.random()*TEN_MINUTES)

    def reset_users_in_room_for_role(self, room_id: str, role: str) -> None:
        key = RedisKeys.users_in_room_for_role(room_id, role)
        self.cache.delete(key)

    def get_users_in_channel_for_role(self, channel_id: str, role: str) -> dict:
        key = RedisKeys.users_in_channel_for_role(channel_id, role)
        return self.cache.get(key)

    def set_users_in_channel_for_role(self, channel_id: str, role: str, users: dict) -> None:
        key = RedisKeys.users_in_channel_for_role(channel_id, role)
        self.cache.set(key, users, ttl=TEN_MINUTES + random.random()*TEN_MINUTES)

    def reset_users_in_channel_for_role(self, channel_id: str, role: str) -> None:
        key = RedisKeys.users_in_channel_for_role(channel_id, role)
        self.cache.delete(key)

    def set_acls_in_channel_for_action(self, channel_id: str, action: str, acls: dict) -> None:
        key = RedisKeys.acls_in_channel_for_action(channel_id, action)
        self.cache.set(key, acls, ttl=FIVE_MINUTES)

    def reset_acls_in_channel_for_action(self, channel_id: str, action: str) -> None:
        key = RedisKeys.acls_in_channel_for_action(channel_id, action)
        self.cache.delete(key)

    def reset_acls_in_room_for_action(self, room_id: str, action: str) -> None:
        key = RedisKeys.acls_in_room_for_action(room_id, action)
        self.cache.delete(key)

    def reset_acls_in_channel(self, channel_id: str) -> None:
        key = RedisKeys.acls_in_channel(channel_id)
        self.cache.delete(key)

    def reset_acls_in_room(self, room_id: str) -> None:
        key = RedisKeys.acls_in_room(room_id)
        self.cache.delete(key)

    def set_all_acls_for_channel(self, channel_id: str, acls: dict) -> None:
        key = RedisKeys.acls_in_channel(channel_id)
        self.cache.set(key, acls, ttl=FIVE_MINUTES + random.random()*FIVE_MINUTES)

    def set_all_acls_for_room(self, room_id: str, acls: dict) -> None:
        key = RedisKeys.acls_in_room(room_id)
        self.cache.set(key, acls, ttl=FIVE_MINUTES + random.random()*FIVE_MINUTES)

    def get_all_acls_for_channel(self, channel_id: str) -> dict:
        key = RedisKeys.acls_in_channel(channel_id)
        return self.cache.get(key)

    def get_all_acls_for_room(self, room_id: str) -> dict:
        key = RedisKeys.acls_in_room(room_id)
        return self.cache.get(key)

    def reset_channels_with_sort(self):
        key = RedisKeys.channels_with_sort()
        self.cache.delete(key)

    def get_channels_with_sort(self):
        key = RedisKeys.channels_with_sort()
        return self.cache.get(key)

    def set_channels_with_sort(self, channels):
        key = RedisKeys.channels_with_sort()
        self.cache.set(key, channels, ttl=TEN_MINUTES)

    def get_channel_ban_timestamp(self, channel_id: str, user_id: str) -> str:
        key = RedisKeys.banned_users_channel(channel_id)
        return self._get_ban_timestamp(key, user_id)

    def get_room_ban_timestamp(self, room_id: str, user_id: str) -> str:
        key = RedisKeys.banned_users(room_id)
        return self._get_ban_timestamp(key, user_id)

    def remove_room_id_for_name(self, channel_id: str, room_name: str) -> None:
        key = RedisKeys.room_id_for_name(channel_id)
        cache_key = '%s-%s' % (key, room_name)
        self.cache.delete(cache_key)
        self.redis.hdel(key, room_name)

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
        self.redis.hset(key, user_id, user_name)
        self.cache.set(cache_key, user_name)

    def get_room_exists(self, channel_id, room_id):
        key = RedisKeys.rooms(channel_id)
        cache_key = '%s-%s' % (key, room_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return True

        exists = self.redis.hexists(key, room_id)
        if exists == 1:
            self.cache.set(cache_key, True)
            return True
        return None

    def remove_channel_exists(self, channel_id: str) -> None:
        key = RedisKeys.channel_exists()
        cache_key = '%s-%s' % (key, channel_id)
        self.redis.hdel(key, channel_id)
        self.cache.delete(cache_key)

        key = RedisKeys.channels()
        cache_key = '%s-name-%s' % (key, channel_id)
        self.cache.delete(cache_key)
        self.redis.hdel(key, channel_id)

    def remove_room_exists(self, channel_id, room_id):
        key = RedisKeys.rooms(channel_id)
        cache_key = '%s-%s' % (key, room_id)
        self.cache.set(cache_key, None)
        self.redis.hdel(key, room_id)

        key = RedisKeys.channel_for_rooms()
        cache_key = '%s-%s' % (key, room_id)
        self.cache.delete(cache_key)
        self.redis.hdel(key, room_id)

        key = RedisKeys.room_roles(room_id)
        self.redis.delete(key)

        key = RedisKeys.room_name_for_id()
        cache_key = '%s-%s-name' % (key, room_id)

        room_name = self.redis.hget(key, room_id)
        if room_name is not None:
            try:
                room_name = str(room_name, 'utf-8')
            except Exception:
                pass

        self.cache.delete(cache_key)
        self.redis.hdel(key, room_id)

        key = RedisKeys.room_id_for_name(channel_id)
        self.redis.hdel(key, room_id)

        if room_name is not None:
            cache_key = '%s-%s' % (key, room_name)
            self.cache.delete(cache_key)

        for role in RoleKeys.all_roles:
            key = RedisKeys.users_in_room_for_role(room_id, role)
            self.redis.delete(key)

    def set_room_exists(self, channel_id, room_id, room_name):
        key = RedisKeys.rooms(channel_id)
        cache_key = '%s-%s' % (key, room_id)
        self.cache.set(cache_key, room_name)
        self.redis.hset(key, room_id, room_name)

    def set_channel_exists(self, channel_id: str) -> None:
        key = RedisKeys.channel_exists()
        cache_key = '%s-%s' % (key, channel_id)
        self.redis.hset(key, channel_id, True)
        self.cache.set(cache_key, True)

    def set_channel_for_room(self, channel_id: str, room_id: str) -> None:
        key = RedisKeys.channel_for_rooms()
        cache_key = '%s-%s' % (key, room_id)
        self.redis.hset(key, room_id, channel_id)
        self.cache.set(cache_key, channel_id, ttl=EIGHT_HOURS_IN_SECONDS)

    def get_channel_exists(self, channel_id):
        key = RedisKeys.channel_exists()
        cache_key = '%s-%s' % (key, channel_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return True

        value = self.redis.hget(key, channel_id)
        if value is None:
            return None

        self.cache.set(cache_key, True)
        return True

    def set_channel_name(self, channel_id: str, channel_name: str) -> None:
        key = RedisKeys.channels()
        cache_key = '%s-name-%s' % (key, channel_id)
        self.cache.set(cache_key, channel_name)
        self.redis.hset(key, channel_id, channel_name)

    def get_channel_name(self, channel_id: str) -> str:
        key = RedisKeys.channels()
        cache_key = '%s-name-%s' % (key, channel_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        value = self.redis.hget(key, channel_id)
        if value is None:
            return None

        value = str(value, 'utf-8')
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

        value = str(value, 'utf-8')
        self.cache.set(cache_key, value)
        return value

    def set_room_name(self, room_id: str, room_name: str) -> None:
        key = RedisKeys.room_name_for_id()
        cache_key = '%s-%s-name' % (key, room_id)
        self.cache.set(cache_key, room_name, ttl=TEN_MINUTES + random.random()*FIVE_MINUTES)
        self.redis.hset(key, room_id, room_name)

    def get_channel_for_room(self, room_id):
        key = RedisKeys.channel_for_rooms()
        cache_key = '%s-%s' % (key, room_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        channel_id = self.redis.hget(key, room_id)
        if channel_id is None:
            return None

        channel_id = str(channel_id, 'utf-8')
        self.cache.set(cache_key, channel_id)
        return channel_id

    def get_user_status(self, user_id: str):
        key = RedisKeys.user_status(user_id)
        value = self.cache.get(key)
        if value is not None:
            return value

        status = self.redis.get(key)
        if status is None or status == '':
            return None

        user_status = str(status, 'utf-8')
        self.cache.set(key, user_status)
        return user_status

    def set_user_status(self, user_id: str, status: str) -> None:
        key = RedisKeys.user_status(user_id)
        self.redis.set(key, status)
        self.cache.set(key, status, ttl=FIVE_MINUTES + random.random()*FIVE_MINUTES)

    def get_user_info(self, user_id: str) -> dict:
        key = RedisKeys.auth_key(user_id)
        return self.cache.get(key)

    def set_user_info(self, user_id: str, info: dict) -> None:
        key = RedisKeys.auth_key(user_id)
        self.cache.set(key, info, ttl=ONE_HOUR)

    def reset_user_info(self, user_id: str) -> None:
        key = RedisKeys.auth_key(user_id)
        self.cache.delete(key)

    def user_check_status(self, user_id, other_status):
        return self.get_user_status(user_id) == other_status

    def user_is_offline(self, user_id):
        return self.user_check_status(user_id, UserKeys.STATUS_UNAVAILABLE)

    def user_is_online(self, user_id):
        return self.user_check_status(user_id, UserKeys.STATUS_AVAILABLE)

    def user_is_invisible(self, user_id):
        return self.user_check_status(user_id, UserKeys.STATUS_INVISIBLE)

    def set_user_offline(self, user_id: str) -> None:
        try:
            self.cache.set(RedisKeys.user_status(user_id), UserKeys.STATUS_UNAVAILABLE)
            self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 0)
            self.redis.srem(RedisKeys.online_set(), int(user_id))
            self.redis.srem(RedisKeys.users_multi_cast(), user_id)
            self.redis.set(RedisKeys.user_status(user_id), UserKeys.STATUS_UNAVAILABLE)
        except Exception as e:
            logger.error('could not set_user_offline(): %s' % str(e))
            logger.exception(traceback.format_exc())

    def set_user_online(self, user_id: str) -> None:
        try:
            self.cache.set(RedisKeys.user_status(user_id), UserKeys.STATUS_AVAILABLE)
            self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 1)
            self.redis.sadd(RedisKeys.online_set(), int(user_id))
            self.redis.sadd(RedisKeys.users_multi_cast(), user_id)
            self.redis.set(RedisKeys.user_status(user_id), UserKeys.STATUS_AVAILABLE)
        except Exception as e:
            logger.error('could not set_user_online(): %s' % str(e))
            logger.exception(traceback.format_exc())

    def set_user_invisible(self, user_id: str) -> None:
        try:
            self.cache.set(RedisKeys.user_status(user_id), UserKeys.STATUS_INVISIBLE)
            self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 0)
            self.redis.srem(RedisKeys.online_set(), int(user_id))
            self.redis.sadd(RedisKeys.users_multi_cast(), user_id)
            self.redis.set(RedisKeys.user_status(user_id), UserKeys.STATUS_INVISIBLE)
        except Exception as e:
            logger.error('could not set_user_invisible(): %s' % str(e))
            logger.exception(traceback.format_exc())
