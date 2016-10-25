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
from dino.config import SessionKeys
from dino.config import RedisKeys
from dino.config import RoleKeys
from dino.config import UserKeys
from dino import environ

from dino.environ import GNEnvironment
from dino.exceptions import NoSuchChannelException
from dino.exceptions import ChannelExistsException
from dino.exceptions import NoSuchRoomException
from dino.exceptions import RoomExistsException
from dino.exceptions import UserExistsException
from dino.exceptions import NoChannelFoundException
from dino.exceptions import NoRoomNameException
from dino.exceptions import NoSuchUserException
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

    def _has_global_role(self, role: str, user_id: str) -> bool:
        roles = self.redis.hget(RedisKeys.global_roles(), user_id)
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
        roles = self.redis.hget(RedisKeys.room_roles(room_id), user_id)
        if roles is None:
            roles = role
        else:
            roles = set(str(roles, 'utf-8').split(','))
            roles.add(role)
            roles = ','.join(roles)
        self.redis.hset(RedisKeys.room_roles(room_id), user_id, roles)

    def _add_global_role(self, role: str, user_id: str):
        key = RedisKeys.global_roles()
        roles = self.redis.hget(key, user_id)
        if roles is None:
            roles = role
        else:
            roles = set(str(roles, 'utf-8').split(','))
            roles.add(role)
            roles = ','.join(roles)
        self.redis.hset(key, user_id, roles)

    def _remove_global_role(self, role: str, user_id: str):
        key = RedisKeys.global_roles()
        roles = self.redis.hget(key, user_id)
        if roles is None:
            return

        new_roles = set()
        roles = set(str(roles, 'utf-8').split(','))
        if role not in roles:
            return

        for old_role in roles:
            if old_role == role:
                continue
            new_roles.add(old_role)

        roles = ','.join(new_roles)
        self.redis.hset(key, user_id, roles)

    def get_super_users(self) -> dict:
        users = self.redis.hgetall(RedisKeys.global_roles())
        super_users = dict()
        for user_id in users.keys():
            super_users[user_id] = self.get_user_name(user_id)
        return super_users

    def set_super_user(self, user_id: str) -> None:
        self._add_global_role(user_id, RoleKeys.SUPER_USER)

    def remove_super_user(self, user_id: str) -> None:
        self._remove_global_role(user_id, RoleKeys.SUPER_USER)

    def is_super_user(self, user_id: str) -> bool:
        self._has_global_role(user_id, RoleKeys.SUPER_USER)

    def is_admin(self, channel_id: str, user_id: str) -> bool:
        return self._has_role_in_channel(RoleKeys.ADMIN, channel_id, user_id)

    def is_moderator(self, room_id: str, user_id: str) -> bool:
        return self._has_role_in_room(RoleKeys.MODERATOR, room_id, user_id)

    def is_owner(self, room_id: str, user_id: str) -> bool:
        return self._has_role_in_room(RoleKeys.OWNER, room_id, user_id)

    def is_owner_channel(self, channel_id: str, user_id: str) -> bool:
        return self._has_role_in_channel(RoleKeys.OWNER, channel_id, user_id)

    def set_admin(self, channel_id: str, user_id: str):
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)
        self._add_channel_role(RoleKeys.ADMIN, channel_id, user_id)

    def set_moderator(self, room_id: str, user_id: str):
        if self.channel_for_room(room_id) is None:
            raise NoSuchRoomException(room_id)
        self._add_room_role(RoleKeys.MODERATOR, room_id, user_id)

    def set_owner(self, room_id: str, user_id: str):
        if self.channel_for_room(room_id) is None:
            raise NoSuchRoomException(room_id)
        self._add_room_role(RoleKeys.OWNER, room_id, user_id)

    def set_owner_channel(self, channel_id: str, user_id: str):
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)
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
            if room_name is None:
                raise NoRoomNameException(room_id)
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

    def create_user(self, user_id: str, user_name: str) -> None:
        try:
            self.get_user_name(user_id)
            raise UserExistsException(user_id)
        except NoSuchUserException:
            pass

        key = RedisKeys.auth_key(user_id)
        self.redis.hset(key, SessionKeys.user_id.value, user_id)
        self.redis.hset(key, SessionKeys.user_name.value, user_name)

    def room_contains(self, room_id: str, user_id: str) -> bool:
        return self.redis.hexists(RedisKeys.users_in_room(room_id), user_id)

    def users_in_room(self, room_id: str) -> dict:
        if self.channel_for_room(room_id) is None:
            raise NoSuchRoomException(room_id)

        users = self.redis.hgetall(RedisKeys.users_in_room(room_id))
        cleaned_users = dict()
        for user_id, user_name in users.items():
            cleaned_users[str(user_id, 'utf-8')] = str(user_name, 'utf-8')
        return cleaned_users

    def leave_room(self, user_id: str, room_id: str) -> None:
        self.redis.hdel(RedisKeys.users_in_room(room_id), user_id)
        self.redis.hdel(RedisKeys.rooms_for_user(user_id), room_id)

    def delete_acl(self, room_id: str, acl_type: str) -> None:
        if self.channel_for_room(room_id) is None:
            raise NoSuchRoomException(room_id)

        self.redis.hdel(RedisKeys.room_acl(room_id), acl_type)

    def add_acls_channel(self, channel_id: str, acls: dict) -> None:
        if self.channel_for_channel(channel_id) is None:
            raise NoSuchRoomException(channel_id)

        self.redis.hmset(RedisKeys.channel_acl(channel_id), acls)

    def add_acls(self, room_id: str, acls: dict) -> None:
        if self.channel_for_room(room_id) is None:
            raise NoSuchRoomException(room_id)

        self.redis.hmset(RedisKeys.room_acl(room_id), acls)

    def get_acls_channel(self, channel_id: str) -> dict:
        if not self.channel_exists(channel_id) is None:
            raise NoSuchChannelException(channel_id)

        acls = self.redis.hgetall(RedisKeys.channel_acl(channel_id))
        acls_cleaned = dict()

        for acl_type, acl_value in acls.items():
            acls_cleaned[str(acl_type, 'utf-8')] = str(acl_value, 'utf-8')

        return acls_cleaned

    def get_acls(self, room_id: str) -> dict:
        try:
            if self.channel_for_room(room_id) is None:
                raise NoSuchRoomException(room_id)
        except NoChannelFoundException:
            raise NoSuchRoomException(room_id)

        acls = self.redis.hgetall(RedisKeys.room_acl(room_id))
        acls_cleaned = dict()

        for acl_type, acl_value in acls.items():
            acls_cleaned[str(acl_type, 'utf-8')] = str(acl_value, 'utf-8')

        return acls_cleaned

    def room_allows_cross_group_messaging(self, room_uuid: str) -> bool:
        acls = self.get_acls(room_uuid)
        if SessionKeys.crossgroup.value not in acls.keys():
            return False
        return acls[SessionKeys.crossgroup.value] == 'y'

    def channel_for_room(self, room_id: str) -> str:
        if room_id is None or len(room_id.strip()) == 0:
            raise NoSuchRoomException

        value = self.env.cache.get_channel_for_room(room_id)
        if value is not None:
            return value

        channel_id = self.redis.hget(RedisKeys.channel_for_rooms(), room_id)
        if channel_id is None:
            raise NoChannelFoundException(room_id)
        self.env.cache.set_channel_for_room(channel_id, room_id)
        return channel_id

    def set_user_name(self, user_id: str, user_name: str) -> None:
        key = RedisKeys.auth_key(user_id)
        self.redis.hset(key, SessionKeys.user_name.value, user_name)

    def get_user_name(self, user_id: str) -> str:
        key = RedisKeys.user_names()
        name = self.redis.hget(key, user_id)
        if name is None:
            raise NoSuchUserException(user_id)
        return str(name, 'utf-8')

    def _get_users_with_role(self, roles: dict, role_key: str):
        if roles is None or len(roles) == 0:
            return dict()

        cleaned = dict()
        for user_id, user_roles in roles.items():
            user_id = str(user_id, 'utf-8')
            user_roles = str(user_roles, 'utf-8')
            if role_key not in user_roles.split(','):
                continue
            cleaned[user_id] = self.get_user_name(user_id)
        return cleaned

    def _get_users_with_role_in_channel(self, channel_id: str, role_key: str):
        roles = self.redis.hgetall(RedisKeys.channel_roles(channel_id))
        return self._get_users_with_role(roles, role_key)

    def _get_users_with_role_in_room(self, room_id: str, role_key: str):
        roles = self.redis.hgetall(RedisKeys.room_roles(room_id))
        return self._get_users_with_role(roles, role_key)

    def get_admins_channel(self, channel_id: str) -> dict:
        return self._get_users_with_role_in_channel(channel_id, RoleKeys.ADMIN)

    def get_owners_channel(self, channel_id: str) -> dict:
        return self._get_users_with_role_in_channel(channel_id, RoleKeys.OWNER)

    def get_owners_room(self, room_id: str) -> dict:
        return self._get_users_with_role_in_room(room_id, RoleKeys.OWNER)

    def get_moderators_room(self, room_id: str) -> dict:
        return self._get_users_with_role_in_room(room_id, RoleKeys.MODERATOR)

    def remove_current_rooms_for_user(self, user_id: str) -> None:
        self.redis.delete(RedisKeys.rooms_for_user(user_id))

    def get_room_name(self, room_id: str) -> str:
        room_name = self.redis.get(RedisKeys.room_name_for_id(room_id))
        if room_name is None:
            raise NoSuchRoomException(room_id)
        return room_name.decode('utf-8')

    def get_channel_name(self, channel_id: str) -> str:
        channel_name = self.redis.hget(RedisKeys.channels(), channel_id)
        if channel_name is None:
            raise NoSuchChannelException(channel_id)
        return channel_name.decode('utf-8')

    def rooms_for_user(self, user_id: str) -> dict:
        clean_rooms = dict()

        rooms = self.redis.hgetall(RedisKeys.rooms_for_user(user_id))
        for room_id, room_name in rooms.items():
            room_id, room_name = str(room_id, 'utf-8'), str(room_name, 'utf-8')
            clean_rooms[room_id] = room_name
        return clean_rooms

    def join_room(self, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
        self.redis.hset(RedisKeys.rooms_for_user(user_id), room_id, room_name)
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
        self.redis.hset(RedisKeys.channel_for_rooms(), room_id, channel_id)

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

    def update_last_read_for(self, users: str, room_id: str, time_stamp: int) -> None:
        redis_key = RedisKeys.last_read(room_id)
        for user_id in users:
            self.redis.hset(redis_key, user_id, time_stamp)

    def get_last_read_timestamp(self, room_id: str, user_id: str) -> int:
        return self.redis.hget(RedisKeys.last_read(room_id), user_id)
