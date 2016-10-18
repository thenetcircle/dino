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
from activitystreams.models.activity import Activity
from uuid import uuid4 as uuid

from dino.db import IDatabase
from dino.config import ConfigKeys
from dino.config import RedisKeys
from dino.config import SessionKeys
from dino import environ

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


@implementer(IDatabase)
class DatabaseRedis(object):
    redis = None

    def __init__(self, host: str, port: int = 6379, db: int = 0):
        if environ.env.config.get(ConfigKeys.TESTING, False) or host == 'mock':
            from fakeredis import FakeStrictRedis as Redis
        else:
            from redis import Redis

        self.redis = Redis(host=host, port=port, db=db)

    def is_admin(self, user_id: str) -> bool:
        self.redis.sismember(RedisKeys.user_roles(user_id), 'admin')

    def get_channels(self) -> dict:
        all_channels = self.redis.hgetall(RedisKeys.channels())
        clean = dict()

        for channel_id, channel_name in all_channels.items():
            clean[str(channel_id, 'utf-8')] = str(channel_name, 'utf-8')
        return clean

    def rooms_for_channel(self, channel_id) -> dict:
        all_rooms = self.redis.hgetall(RedisKeys.rooms(channel_id))
        clean = dict()

        for room_id, room_name in all_rooms.items():
            clean[str(room_id, 'utf-8')] = str(room_name, 'utf-8')
        return clean

    def room_exists(self, channel_id: str, room_id: str) -> bool:
        return self.redis.hexists(RedisKeys.rooms(channel_id), room_id)

    def room_name_exists(self, channel_id, room_name: str) -> bool:
        cleaned = set()
        for room_name in self.redis.hvals(RedisKeys.rooms(channel_id)):
            cleaned.add(str(room_name, 'utf-8').lower())

        if type(room_name) == bytes:
            room_name = str(room_name, 'utf-8')

        return room_name.lower() in cleaned

    def channel_exists(self, channel_id) -> bool:
        if channel_id is None or channel_id == '':
            return False
        return self.redis.hexists(RedisKeys.channels(), channel_id)

    def room_contains(self, room_id: str, user_id: str) -> bool:
        return self.redis.hexists(RedisKeys.users_in_room(room_id), user_id)

    def room_owners_contain(self, room_id, user_id) -> bool:
        if room_id is None or room_id == '':
            return False
        if user_id is None or user_id == '':
            return False

        return self.redis.hexists(RedisKeys.room_owners(room_id), user_id)

    def users_in_room(self, room_id: str) -> dict:
        users = self.redis.hgetall(RedisKeys.users_in_room(room_id))
        cleaned_users = dict()
        for user_id, user_name in users.items():
            cleaned_users[str(user_id, 'utf-8')] = str(user_name, 'utf-8')
        return cleaned_users

    def leave_room(self, user_id: str, room_id: str) -> None:
        self.redis.hdel(RedisKeys.users_in_room(room_id), user_id)
        self.redis.srem(RedisKeys.rooms_for_user(user_id), room_id)

    def delete_acl(self, room_id: str, acl_type: str) -> None:
        self.redis.hdel(RedisKeys.room_acl(room_id), acl_type)

    def add_acls(self, room_id: str, acls: dict) -> None:
        self.redis.hmset(RedisKeys.room_acl(room_id), acls)

    def get_acls(self, room_id: str) -> list:
        acls = self.redis.hgetall(RedisKeys.room_acl(room_id))
        acls_cleaned = dict()

        for acl_type, acl_value in acls.items():
            acls_cleaned[str(acl_type, 'utf-8')] = str(acl_value, 'utf-8')

        return acls_cleaned

    def rooms_for_user(self, user_id: str = None) -> dict:
        clean_rooms = dict()

        rooms = self.redis.smembers(RedisKeys.rooms_for_user(user_id))
        for room in rooms:
            room_id, room_name = str(room, 'utf-8').split(':', 1)
            clean_rooms[room_id] = room_name
        return clean_rooms

    def get_owners(self, room_id: str) -> dict:
        owners = self.redis.hgetall(RedisKeys.room_owners(room_id))

        cleaned = dict()
        for user_id, user_name in owners.items():
            cleaned[str(user_id, 'utf-8')] = str(user_name, 'utf-8')

        return cleaned

    def remove_current_rooms_for_user(self, user_id: str) -> None:
        self.redis.delete(RedisKeys.rooms_for_user(user_id))

    def get_room_name(self, room_id: str) -> str:
        room_name = self.redis.get(RedisKeys.room_name_for_id(room_id))
        if room_name is None:
            room_name = str(uuid())
            environ.env.logger.warn(
                'WARN: room_name for room_id %s is None, generated new name: %s' % (room_id, room_name))
            self.redis.set(RedisKeys.room_name_for_id(room_id), room_name)
        else:
            room_name = room_name.decode('utf-8')
        return room_name

    def get_user_name_for(self, user_id: str) -> str:
        return self.redis.hget(RedisKeys.users(), user_id)

    def create_user(self, user_id: str, user_name: str) -> None:
        self.redis.hset(RedisKeys.users(), user_id, user_name)

    def join_room(self, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
        self.redis.sadd(RedisKeys.rooms_for_user(user_id), '%s:%s' % (room_id, room_name))
        self.redis.hset(RedisKeys.users_in_room(room_id), user_id, user_name)

    def create_room(self, room_name: str, room_id: str, channel_id: str, user_id: str, user_name) -> None:
        self.redis.set(RedisKeys.room_name_for_id(room_id), room_name)
        self.redis.hset(RedisKeys.room_owners(room_id), user_id, user_name)
        self.redis.hset(RedisKeys.rooms(channel_id), room_id, room_name)

    def set_user_offline(self, user_id: str) -> None:
        self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 0)
        self.redis.srem(RedisKeys.online_set(), int(user_id))
        self.redis.srem(RedisKeys.users_multi_cast(), user_id)
        self.redis.set(RedisKeys.user_status(user_id), RedisKeys.REDIS_STATUS_UNAVAILABLE)

    def set_user_online(self, user_id: str) -> None:
        self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 1)
        self.redis.sadd(RedisKeys.online_set(), int(user_id))
        self.redis.sadd(RedisKeys.users_multi_cast(), user_id)
        self.redis.set(RedisKeys.user_status(user_id), RedisKeys.REDIS_STATUS_AVAILABLE)

    def set_user_invisible(self, user_id: str) -> None:
        self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 0)
        self.redis.srem(RedisKeys.online_set(), int(user_id))
        self.redis.sadd(RedisKeys.users_multi_cast(), user_id)
        self.redis.set(RedisKeys.user_status(user_id), RedisKeys.REDIS_STATUS_INVISIBLE)
