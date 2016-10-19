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

from typing import Union
from zope.interface import implementer
from uuid import uuid4 as uuid

from dino.db import IDatabase
from dino.config import ConfigKeys
from dino.config import RedisKeys
from dino.config import RoleKeys
from dino.config import UserKeys
from dino import environ

from dino.environ import GNEnvironment
from dino.exceptions import NoSuchChannelException
from dino.exceptions import ChannelExistsException
from dino.exceptions import RoomExistsException
from dino.exceptions import RoomNameExistsForChannelException

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


@implementer(IDatabase)
class DatabaseRedis(object):
    redis = None

    def __init__(self, env: GNEnvironment, host: str, port: int = 6379, db: int = 0):
        if environ.env.config.get(ConfigKeys.TESTING, False) or host == 'mock':
            from fakeredis import FakeStrictRedis as Redis
        else:
            from redis import Redis

        self.env = env
        self.redis = Redis(host=host, port=port, db=db)

    def _has_role_in_room(self, role: str, room_id: str, user_id: str) -> bool:
        roles = self.redis.hget(RedisKeys.room_roles(room_id), user_id)
        if roles is None:
            return False
        return role in str(roles, 'utf-8').split(',')

    def _has_role_in_channel(self, role: str, channel_id: str, user_id: str) -> bool:
        roles = self.redis.hget(RedisKeys.channel_roles(channel_id), user_id)
        if roles is None:
            return False
        return role in str(roles, 'utf-8').split(',')

    def _add_channel_role(self, role: str, channel_id: str, user_id: str):
        roles = self.redis.hget(RedisKeys.channel_roles(channel_id), user_id)
        if roles is None:
            roles = role
        else:
            roles = set(str(roles, 'utf-8').split(','))
            roles.add(role)
            roles = ','.join(roles)
        self.redis.hset(RedisKeys.channel_roles(channel_id), user_id, roles)

    def _add_room_role(self, role: str, room_id: str, user_id: str):
        roles = self.redis.hget(RedisKeys.channel_roles(room_id), user_id)
        if roles is None:
            roles = role
        else:
            roles = set(str(roles, 'utf-8').split(','))
            roles.add(role)
            roles = ','.join(roles)
        self.redis.hset(RedisKeys.channel_roles(room_id), user_id, roles)

    def is_admin(self, channel_id: str, user_id: str) -> bool:
        return self._has_role_in_channel(RoleKeys.ADMIN, channel_id, user_id)

    def is_moderator(self, room_id: str, user_id: str) -> bool:
        return self._has_role_in_room(RoleKeys.MODERATOR, room_id, user_id)

    def is_owner(self, room_id: str, user_id: str) -> bool:
        return self._has_role_in_room(RoleKeys.OWNER, room_id, user_id)

    def set_admin(self, channel_id: str, user_id: str):
        self._add_channel_role(RoleKeys.ADMIN, channel_id, user_id)

    def set_moderator(self, room_id: str, user_id: str):
        self._add_room_role(RoleKeys.MODERATOR, room_id, user_id)

    def set_owner(self, room_id: str, user_id: str):
        self._add_room_role(RoleKeys.OWNER, room_id, user_id)

    def set_owner_channel(self, channel_id: str, user_id: str):
        self._add_channel_role(RoleKeys.OWNER, channel_id, user_id)

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

    def join_room(self, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
        self.redis.sadd(RedisKeys.rooms_for_user(user_id), '%s:%s' % (room_id, room_name))
        self.redis.hset(RedisKeys.users_in_room(room_id), user_id, user_name)

    def create_room(self, room_name: str, room_id: str, channel_id: str, user_id: str, user_name) -> None:
        if self.env.cache.get_channel_exists(channel_id) is None:
            if not self.channel_exists(channel_id):
                raise NoSuchChannelException(channel_id)

        if self.room_exists(channel_id, room_id):
            raise RoomExistsException(room_id)

        if self.room_name_exists(channel_id, room_name):
            raise RoomNameExistsForChannelException(channel_id, room_name)

        self.redis.set(RedisKeys.room_name_for_id(room_id), room_name)
        self.redis.hset(RedisKeys.room_owners(room_id), user_id, user_name)
        self.redis.hset(RedisKeys.rooms(channel_id), room_id, room_name)

    def create_channel(self, channel_name, channel_id, user_id) -> None:
        if self.channel_exists(channel_id):
            raise ChannelExistsException(channel_id)

        self.env.cache.set_channel_exists(channel_id)
        self.redis.hset(RedisKeys.channels(), channel_id, channel_name)
        self.set_owner_channel(channel_id, user_id)

    def get_user_status(self, user_id: str) -> str:
        status = self.env.cache.get_user_status(user_id)
        if status is not None:
            return status

        status = self.redis.get(RedisKeys.user_status(user_id))
        if status is None:
            return UserKeys.STATUS_UNAVAILABLE
        return str(status, 'utf-8')

    def set_user_offline(self, user_id: str) -> None:
        self.env.cache.set_user_offline(user_id)

    def set_user_online(self, user_id: str) -> None:
        self.env.cache.set_user_online(user_id)

    def set_user_invisible(self, user_id: str) -> None:
        self.env.cache.set_user_invisible(user_id)
