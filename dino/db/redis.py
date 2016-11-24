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
from datetime import datetime
from typing import Union
from uuid import uuid4 as uuid
import logging

from dino.db import IDatabase
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.config import RedisKeys
from dino.config import RoleKeys
from dino.config import UserKeys
from dino.config import ApiActions
from dino import environ

from dino.environ import GNEnvironment
from dino.validation.acl import AclValidator
from dino.exceptions import NoSuchChannelException
from dino.exceptions import ChannelExistsException
from dino.exceptions import NoSuchRoomException
from dino.exceptions import RoomExistsException
from dino.exceptions import UserExistsException
from dino.exceptions import NoChannelFoundException
from dino.exceptions import NoRoomNameException
from dino.exceptions import NoSuchUserException
from dino.exceptions import RoomNameExistsForChannelException
from dino.exceptions import EmptyChannelNameException
from dino.exceptions import EmptyRoomNameException
from dino.exceptions import InvalidAclTypeException
from dino.exceptions import InvalidAclValueException
from dino.exceptions import AclValueNotFoundException
from dino.exceptions import InvalidApiActionException
from dino.exceptions import ValidationException

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


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
        self.acl_validator = AclValidator()

    def create_admin_room_for(self, channel_id: str) -> str:
        room_id = str(uuid())
        self.redis.hset(RedisKeys.admin_room_for_channel(), channel_id, room_id)
        self.redis.hset(RedisKeys.room_name_for_id, room_id, 'Admins')
        self.redis.hset(RedisKeys.rooms(channel_id), room_id, 'Admins')
        self.redis.hset(RedisKeys.channel_for_rooms(), room_id, channel_id)

        acls = {
            RoleKeys.ADMIN: '',
            RoleKeys.SUPER_USER: ''
        }
        samechannel = {
            'samechannel': ''
        }

        self.add_acls_in_room_for_action(room_id, ApiActions.JOIN, acls)
        self.add_acls_in_room_for_action(room_id, ApiActions.LIST, acls)
        self.add_acls_in_room_for_action(room_id, ApiActions.CROSSROOM, samechannel)
        return room_id

    def admin_room_for_channel(self, channel_id: str) -> str:
        room_id = self.redis.hget(RedisKeys.admin_room_for_channel(), channel_id)
        if room_id is None or len(str(room_id, 'utf-8').strip()) == 0:
            return None
        return str(room_id, 'utf-8')

    def is_room_private(self, room_id: str) -> bool:
        channel_id = self.redis.hget(RedisKeys.private_channel_for_prefix(), room_id[:2])
        return channel_id is not None and len(str(channel_id, 'utf-8').strip()) > 0

    def get_private_room(self, user_id: str) -> (str, str):
        room_id = self.redis.hget(RedisKeys.private_rooms(), user_id)
        if room_id is None:
            room_id = str(uuid())
            channel_prefix = room_id[:2]

            channel_id = self.get_private_channel_for_room(room_id)
            if channel_id is None:
                channel_id = self.create_private_channel_for_room(room_id)

            self.redis.hset(RedisKeys.private_rooms_in_channel(channel_prefix), channel_id, room_id)
            self.redis.hset(RedisKeys.private_rooms(), user_id, room_id)
            self.redis.hset(RedisKeys.user_for_private_room(), room_id, user_id)
        else:
            room_id = str(room_id, 'utf-8')
            channel_id = self.get_private_channel_for_room(room_id)
        return room_id, channel_id

    def get_private_channel_for_room(self, room_id: str) -> str:
        return self.get_private_channel_for_prefix(room_id[:2])

    def get_private_channel_for_prefix(self, channel_prefix):
        channel_id = self.redis.hget(RedisKeys.private_channel_for_prefix(), channel_prefix)
        if channel_id is None:
            return self.create_private_channel_for_prefix(channel_prefix)
        return str(channel_id, 'utf-8')

    def create_private_channel_for_room(self, room_id):
        return self.create_private_channel_for_prefix(room_id[:2])

    def create_private_channel_for_prefix(self, channel_prefix):
        channel_id = str(uuid())
        self.redis.hset(RedisKeys.private_channel_for_prefix(), channel_prefix, channel_id)
        return channel_id

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

    def _has_global_role(self, user_id: str, role: str) -> bool:
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

    def _add_global_role(self, user_id: str, role: str):
        key = RedisKeys.global_roles()
        roles = self.redis.hget(key, user_id)
        if roles is None:
            roles = role
        else:
            roles = set(str(roles, 'utf-8').split(','))
            roles.add(role)
            roles = ','.join(roles)
        self.redis.hset(key, user_id, roles)

    def _remove_channel_role(self, role: str, channel_id: str, user_id: str):
        roles = self.redis.hget(RedisKeys.channel_roles(channel_id), user_id)
        if roles is None:
            return

        roles = set(str(roles, 'utf-8').split(','))
        if role not in roles:
            return

        roles.remove(role)
        roles = ','.join(roles)
        self.redis.hset(RedisKeys.channel_roles(channel_id), user_id, roles)

    def _remove_room_role(self, role: str, room_id: str, user_id: str):
        roles = self.redis.hget(RedisKeys.room_roles(room_id), user_id)
        if roles is None:
            return

        roles = set(str(roles, 'utf-8').split(','))
        if role not in roles:
            return

        roles.remove(role)
        roles = ','.join(roles)
        self.redis.hset(RedisKeys.room_roles(room_id), user_id, roles)

    def _remove_global_role(self, user_id: str, role: str):
        key = RedisKeys.global_roles()
        roles = self.redis.hget(key, user_id)
        if roles is None:
            return

        roles = set(str(roles, 'utf-8').split(','))
        if role not in roles:
            return

        roles.remove(role)
        roles = ','.join(roles)
        self.redis.hset(key, user_id, roles)

    def get_super_users(self) -> dict:
        users = self.redis.hgetall(RedisKeys.global_roles())
        super_users = dict()
        for user_id in users.keys():
            user_id = str(user_id, 'utf-8')
            super_users[user_id] = self.get_user_name(user_id)
        return super_users

    def set_super_user(self, user_id: str) -> None:
        self._add_global_role(user_id, RoleKeys.SUPER_USER)

    def remove_super_user(self, user_id: str) -> None:
        self._remove_global_role(user_id, RoleKeys.SUPER_USER)

    def is_super_user(self, user_id: str) -> bool:
        return self._has_global_role(user_id, RoleKeys.SUPER_USER)

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

    def remove_admin(self, channel_id: str, user_id: str) -> None:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)
        self._remove_channel_role(RoleKeys.ADMIN, channel_id, user_id)

    def remove_owner_channel(self, channel_id: str, user_id: str) -> None:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)
        self._remove_channel_role(RoleKeys.OWNER, channel_id, user_id)

    def remove_moderator(self, room_id: str, user_id: str) -> None:
        self.get_room_name(room_id)
        if not self.channel_for_room(room_id):
            raise NoChannelFoundException(room_id)
        self._remove_room_role(RoleKeys.MODERATOR, room_id, user_id)

    def remove_owner(self, room_id: str, user_id: str) -> None:
        if not self.channel_for_room(room_id):
            raise NoSuchRoomException(room_id)
        self._remove_room_role(RoleKeys.OWNER, room_id, user_id)

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

    def channel_name_exists(self, channel_name: str) -> bool:
        cleaned = set()
        for candidate in self.redis.hvals(RedisKeys.channels()):
            cleaned.add(str(candidate, 'utf-8').lower())

        if type(channel_name) == bytes:
            channel_name = str(channel_name, 'utf-8')

        return channel_name.lower() in cleaned

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
        self.redis.hset(RedisKeys.user_names(), user_id, user_name)
        self.get_private_room(user_id)

    def room_contains(self, room_id: str, user_id: str) -> bool:
        return self.redis.hexists(RedisKeys.users_in_room(room_id), user_id)

    def users_in_room(self, room_id: str) -> dict:
        self.channel_for_room(room_id)

        users = self.redis.hgetall(RedisKeys.users_in_room(room_id))
        cleaned_users = dict()
        for user_id, user_name in users.items():
            user_id = str(user_id, 'utf-8')
            private_room_id = self.get_private_room(user_id)[0]
            cleaned_users[private_room_id] = str(user_name, 'utf-8')
        return cleaned_users

    def leave_room(self, user_id: str, room_id: str) -> None:
        self.redis.hdel(RedisKeys.users_in_room(room_id), user_id)
        self.redis.hdel(RedisKeys.rooms_for_user(user_id), room_id)

    def delete_acl_in_room_for_action(self, room_id: str, acl_type: str, action: str) -> None:
        self.get_room_name(room_id)
        self.channel_for_room(room_id)

        key = '%s|%s' % (action, acl_type)
        self.redis.hdel(RedisKeys.room_acl(room_id), key)

    def delete_acl_in_channel_for_action(self, channel_id: str, acl_type: str, action: str) -> None:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)

        key = '%s|%s' % (action, acl_type)
        self.redis.hdel(RedisKeys.channel_acl(channel_id), key)

    def update_acl_in_room_for_action(self, channel_id: str, room_id: str, action: str, acl_type: str, acl_value: str) -> None:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)
        if not self.room_exists(channel_id, room_id):
            raise NoSuchRoomException(room_id)

        self.add_acls_in_room_for_action(room_id, action, {acl_type: acl_value})

    def update_acl_in_channel_for_action(self, channel_id: str, action: str, acl_type: str, acl_value: str) -> None:
        self.add_acls_in_channel_for_action(channel_id, action, {acl_type: acl_value})

    def add_acls_in_channel_for_action(self, channel_id: str, action: str, acls: dict) -> None:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)

        if action not in ApiActions.all_api_actions:
            raise InvalidApiActionException(action)

        new_acls = dict()
        acl_configs = environ.env.config.get(ConfigKeys.ACL)

        for acl_type, acl_value in acls.items():
            if acl_type not in acl_configs['available']['acls']:
                raise InvalidAclTypeException(acl_type)
            try:
                acl_configs['validation'][acl_type]['value'].validate_new_acl(acl_value)
            except ValidationException:
                raise InvalidAclValueException(acl_type, acl_value)

            key = '%s|%s' % (action, acl_type)
            new_acls[key] = acl_value

        self.redis.hmset(RedisKeys.channel_acl(channel_id), new_acls)

    def add_acls_in_room_for_action(self, room_id: str, action: str, acls: dict) -> None:
        if self.channel_for_room(room_id) is None:
            raise NoSuchRoomException(room_id)

        if action not in ApiActions.all_api_actions:
            raise InvalidApiActionException(action)

        acl_configs = environ.env.config.get(ConfigKeys.ACL)

        if action not in ApiActions.all_api_actions:
            raise InvalidApiActionException(action)

        new_acls = dict()
        for acl_type, acl_value in acls.items():
            if acl_type not in acl_configs['available']['acls']:
                raise InvalidAclTypeException(acl_type)
            try:
                acl_configs['validation'][acl_type]['value'].validate_new_acl(acl_value)
            except ValidationException:
                raise InvalidAclValueException(acl_type, acl_value)

            key = '%s|%s' % (action, acl_type)
            new_acls[key] = acl_value

        self.redis.hmset(RedisKeys.room_acl(room_id), new_acls)

    def _is_banned(self, ban):
        time = None
        if ban is not None:
            ban = str(ban, 'utf-8')
            time = ban.split('|', 2)[1]
        return time is not None, time

    def is_banned_globally(self, user_id: str) -> (bool, Union[str, None]):
        ban = self.redis.hget(RedisKeys.banned_users(), user_id)
        is_banned, time = self._is_banned(ban)
        if not is_banned:
            return False, None

        now = datetime.utcnow()
        end = datetime.strptime(time, ConfigKeys.DEFAULT_DATE_FORMAT)
        if now > end:
            self.redis.hdel(RedisKeys.banned_users(), user_id)
            return False, None
        return True, time

    def is_banned_from_channel(self, channel_id: str, user_id: str) -> (bool, Union[str, None]):
        ban = self.redis.hget(RedisKeys.banned_users_channel(channel_id), user_id)
        return self._is_banned(ban)

    def is_banned_from_room(self, room_id: str, user_id: str) -> (bool, Union[str, None]):
        ban = self.redis.hget(RedisKeys.banned_users(room_id), user_id)
        return self._is_banned(ban)

    def remove_global_ban(self, user_id: str) -> str:
        self.redis.hdel(RedisKeys.banned_users(), user_id)

    def remove_channel_ban(self, channel_id: str, user_id: str) -> str:
        self.redis.hdel(RedisKeys.banned_users_channel(channel_id), user_id)

    def remove_room_ban(self, room_id: str, user_id: str) -> str:
        self.redis.hdel(RedisKeys.banned_users(room_id), user_id)

    def get_user_ban_status(self, room_id: str, user_id: str) -> dict:
        channel_id = self.channel_for_room(room_id)
        global_ban = self.redis.hget(RedisKeys.banned_users(), user_id)
        channel_ban = self.redis.hget(RedisKeys.banned_users_channel(channel_id), user_id)
        room_ban = self.redis.hget(RedisKeys.banned_users(room_id), user_id)

        global_timestamp = ''
        channel_timestamp = ''
        room_timestamp = ''

        if global_ban is not None:
            global_ban = str(global_ban, 'utf-8')
            global_timestamp = global_ban.split('|', 2)[1]
        if channel_ban is not None:
            channel_ban = str(channel_ban, 'utf-8')
            channel_timestamp = channel_ban.split('|', 2)[1]
        if room_ban is not None:
            room_ban = str(room_ban, 'utf-8')
            room_timestamp = room_ban.split('|', 2)[1]

        return {
            'global': global_timestamp,
            'channel': channel_timestamp,
            'room': room_timestamp
        }

    # TODO: use @lru_cache?
    def get_banned_users_global(self) -> dict:
        now = datetime.utcnow()
        output = dict()

        def for_global_ban(user_id, ban_info):
            ban_duration, ban_timestamp, username = ban_info.split('|', 2)
            if datetime.fromtimestamp(int(ban_timestamp)) > now:
                self.redis.hdel(RedisKeys.banned_users(), user_id)
                return

            output[user_id] = {
                'name': self.get_user_name(user_id),
                'duration': ban_duration,
                'timestamp': datetime.fromtimestamp(int(ban_timestamp)).strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
            }

        global_bans = self.redis.hgetall(RedisKeys.banned_users())
        for user_id, ban_info in global_bans.items():
            user_id = str(user_id, 'utf-8')
            ban_info = str(ban_info, 'utf-8')
            for_global_ban(user_id, ban_info)

        return output

    # TODO: use @lru_cache?
    def get_banned_users_for_channel(self, channel_id):
        now = datetime.utcnow()
        output = dict()

        def for_local_ban_channel(user_id, channel_id, ban_info):
            ban_duration, ban_timestamp, username = ban_info.split('|', 2)
            if datetime.fromtimestamp(int(ban_timestamp)) > now:
                self.redis.hdel(RedisKeys.banned_users_channel(channel_id), user_id)
                return

            output[user_id] = {
                'duration': ban_duration,
                'timestamp': datetime.fromtimestamp(int(ban_timestamp)).strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
            }

        channel_bans = self.redis.hgetall(RedisKeys.banned_users_channel(channel_id))
        for user_id, ban_info in channel_bans.items():
            user_id = str(user_id, 'utf-8')
            ban_info = str(ban_info, 'utf-8')
            for_local_ban_channel(user_id, channel_id, ban_info)

        return output

    # TODO: use @lru_cache?
    def get_banned_users_for_room(self, room_id) -> dict:
        now = datetime.utcnow()
        output = dict()

        def for_local_ban(user_id, room_id, ban_info):
            ban_duration, ban_timestamp, username = ban_info.split('|', 2)
            if datetime.fromtimestamp(int(ban_timestamp)) > now:
                self.redis.hdel(RedisKeys.banned_users(room_id), user_id)
                return

            if user_id not in output:
                output[user_id] = dict()

            output[user_id] = {
                'duration': ban_duration,
                'timestamp': datetime.fromtimestamp(int(ban_timestamp)).strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
            }

        local_bans = self.redis.hgetall(RedisKeys.banned_users(room_id))
        for user_id, ban_info in local_bans.items():
            user_id = str(user_id, 'utf-8')
            ban_info = str(ban_info, 'utf-8')
            for_local_ban(user_id, room_id, ban_info)

        return output

    def get_banned_users(self) -> dict:
        all_channels = self.redis.hgetall(RedisKeys.channels())

        def get_banned_users_all_channels() -> dict:
            output = dict()
            for channel_id, _ in all_channels.items():
                channel_id = str(channel_id, 'utf-8')
                output[channel_id] = {
                    'name': self.get_channel_name(channel_id),
                    'users': self.get_banned_users_for_channel(channel_id)
                }
            return output

        def get_banned_users_all_rooms(self, all_channels) -> dict:
            output = dict()
            for channel_id, _ in all_channels.items():
                channel_id = str(channel_id, 'utf-8')
                rooms_for_channel = self.redis.hgetall(RedisKeys.rooms(channel_id))
                for room_id, _ in rooms_for_channel.items():
                    room_id = str(room_id, 'utf-8')
                    output[room_id] = {
                        'name': self.get_room_name(room_id),
                        'users': self.get_banned_users_for_room(room_id)
                    }
            return output

        return {
            'global': self.get_banned_users_global(),
            'channels': self.get_banned_users_all_channels(all_channels),
            'rooms': self.get_banned_users_all_rooms(all_channels)
        }

    def kick_user(self, room_id: str, user_id: str) -> None:
        self.leave_room(user_id, room_id)

    def _get_ban_timestamp(self, ban) -> (str, str, str):
        if ban is None:
            return None, None, None
        ban = str(ban, 'utf-8')
        return ban.split('|', 2)

    def get_global_ban_timestamp(self, user_id: str) -> (str, str, str):
        ban = self.redis.hset(RedisKeys.banned_users(), user_id)
        return self._get_ban_timestamp(ban)

    def get_channel_ban_timestamp(self, channel_id: str, user_id: str) -> (str, str, str):
        ban = self.redis.hset(RedisKeys.banned_users_channel(channel_id), user_id)
        return self._get_ban_timestamp(ban)

    def get_room_ban_timestamp(self, room_id: str, user_id: str) -> (str, str, str):
        ban = self.redis.hset(RedisKeys.banned_users(room_id), user_id)
        return self._get_ban_timestamp(ban)

    def ban_user_global(self, user_id: str, ban_timestamp: str, ban_duration: str):
        user_name = ''
        try:
            user_name = self.get_user_name(user_id)
        except NoSuchUserException:
            pass
        self.redis.hset(RedisKeys.banned_users(), user_id, '%s|%s|%s' % (ban_duration, ban_timestamp, user_name))

    def ban_user_room(self, user_id: str, ban_timestamp: str, ban_duration: str, room_id: str):
        user_name = ''
        try:
            user_name = self.get_user_name(user_id)
        except NoSuchUserException:
            pass
        self.redis.hset(RedisKeys.banned_users(room_id), user_id, '%s|%s|%s' % (ban_duration, ban_timestamp, user_name))

    def ban_user_channel(self, user_id: str, ban_timestamp: str, ban_duration: str, channel_id: str):
        user_name = ''
        try:
            user_name = self.get_user_name(user_id)
        except NoSuchUserException:
            pass
        self.redis.hset(RedisKeys.banned_users_channel(channel_id), user_id, '%s|%s|%s' % (ban_duration, ban_timestamp, user_name))

    def get_acl_validation_value(self, acl_type: str, validation_method) -> str:
        value = self.redis.hget(RedisKeys.acl_validations(acl_type), validation_method)
        if value is None:
            raise AclValueNotFoundException(acl_type, validation_method)
        value = str(value, 'utf-8')
        if len(value.strip()) == 0:
            raise AclValueNotFoundException(acl_type, validation_method)
        return value

    def get_acls_in_room_for_action(self, room_id: str, action: str) -> dict:
        try:
            if self.channel_for_room(room_id) is None:
                raise NoSuchRoomException(room_id)
        except NoChannelFoundException:
            raise NoSuchRoomException(room_id)

        acls = self.redis.hgetall(RedisKeys.room_acl(room_id))
        acls_cleaned = dict()

        for acl_key, acl_value in acls.items():
            acl_action, acl_type = str(acl_key, 'utf-8').split('|', 1)
            if acl_action != action:
                continue
            acls_cleaned[acl_type] = str(acl_value, 'utf-8')

        return acls_cleaned

    def get_acls_in_channel_for_action(self, channel_id: str, action: str) -> dict:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)

        acls = self.redis.hgetall(RedisKeys.channel_acl(channel_id))
        acls_cleaned = dict()

        for acl_key, acl_value in acls.items():
            acl_action, acl_type = str(acl_key, 'utf-8').split('|', 1)
            if acl_action != action:
                continue
            acls_cleaned[acl_type] = str(acl_value, 'utf-8')

        return acls_cleaned

    def get_all_acls_channel(self, channel_id: str) -> dict:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)

        acls = self.redis.hgetall(RedisKeys.channel_acl(channel_id))
        acls_cleaned = dict()

        for acl_key, acl_value in acls.items():
            acl_action, acl_type = str(acl_key, 'utf-8').split('|', 1)
            if acl_action not in acls_cleaned:
                acls_cleaned[acl_action] = dict()
            acls_cleaned[acl_action][acl_type] = str(acl_value, 'utf-8')

        return acls_cleaned

    def get_all_acls_room(self, room_id: str) -> dict:
        try:
            if self.channel_for_room(room_id) is None:
                raise NoSuchRoomException(room_id)
        except NoChannelFoundException:
            raise NoSuchRoomException(room_id)

        acls = self.redis.hgetall(RedisKeys.room_acl(room_id))
        acls_cleaned = dict()

        for acl_key, acl_value in acls.items():
            acl_action, acl_type = str(acl_key, 'utf-8').split('|', 1)
            if acl_action not in acls_cleaned:
                acls_cleaned[acl_action] = dict()
            acls_cleaned[acl_action][acl_type] = str(acl_value, 'utf-8')

        return acls_cleaned

    def channel_for_room(self, room_id: str) -> str:
        if room_id is None or len(room_id.strip()) == 0:
            raise NoSuchRoomException(room_id)

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
            try:
                cleaned[user_id] = self.get_user_name(user_id)
            except NoSuchUserException:
                logger.error('no username found for user_id %s' % user_id)
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
        room_name = self.redis.hget(RedisKeys.room_name_for_id(), room_id)
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

    def get_user_for_private_room(self, room_id: str) -> str:
        room_id = self.redis.hget(RedisKeys.user_for_private_room(), room_id)
        if room_id is None:
            return None
        return str(room_id, 'utf-8')

    def join_private_room(self, user_id: str, user_name: str, room_id: str) -> None:
        self.redis.hset(RedisKeys.private_rooms(), user_id, room_id)
        channel_id = self.get_private_channel_for_room(room_id)
        self.redis.hset(RedisKeys.private_rooms_in_channel(room_id[:2]), channel_id, room_id)

    def join_room(self, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
        self.redis.hset(RedisKeys.rooms_for_user(user_id), room_id, room_name)
        self.redis.hset(RedisKeys.users_in_room(room_id), user_id, user_name)

    def create_channel(self, channel_name, channel_id, user_id) -> None:
        if self.channel_exists(channel_id):
            raise ChannelExistsException(channel_id)

        self.env.cache.set_channel_exists(channel_id)
        self.redis.hset(RedisKeys.channels(), channel_id, channel_name)
        self.set_owner_channel(channel_id, user_id)

    def create_room(self, room_name: str, room_id: str, channel_id: str, user_id: str, user_name) -> None:
        if self.env.cache.get_channel_exists(channel_id) is None:
            if not self.channel_exists(channel_id):
                raise NoSuchChannelException(channel_id)

        if room_name is None or len(room_name.strip()) == 0:
            raise EmptyRoomNameException(room_id)

        if self.room_exists(channel_id, room_id):
            raise RoomExistsException(room_id)

        if self.room_name_exists(channel_id, room_name):
            raise RoomNameExistsForChannelException(channel_id, room_name)

        self.redis.hset(RedisKeys.room_name_for_id(), room_id, room_name)
        self.redis.hset(RedisKeys.rooms(channel_id), room_id, room_name)
        self.redis.hset(RedisKeys.channel_for_rooms(), room_id, channel_id)
        self.redis.hset(RedisKeys.user_names(), user_id, user_name)
        self.set_owner(room_id, user_id)

    def rename_channel(self, channel_id: str, channel_name: str) -> None:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)

        if channel_name is None or len(channel_name.strip()) == 0:
            raise EmptyChannelNameException(channel_id)

        self.redis.hset(RedisKeys.channels(), channel_id, channel_name)

    def rename_room(self, channel_id: str, room_id: str, room_name: str) -> None:
        if self.env.cache.get_channel_exists(channel_id) is None:
            if not self.channel_exists(channel_id):
                raise NoSuchChannelException(channel_id)

        if room_name is None or len(room_name.strip()) == 0:
            raise EmptyRoomNameException(channel_id)

        if not self.room_exists(channel_id, room_id):
            raise NoSuchRoomException(room_id)

        if self.room_name_exists(channel_id, room_name):
            raise RoomNameExistsForChannelException(channel_id, room_name)

        self.redis.hset(RedisKeys.room_name_for_id, room_id, room_name)
        self.redis.hset(RedisKeys.rooms(channel_id), room_id, room_name)

    def remove_room(self, channel_id: str, room_id: str) -> None:
        if self.env.cache.get_channel_exists(channel_id) is None:
            if not self.channel_exists(channel_id):
                raise NoSuchChannelException(channel_id)

        if not self.room_exists(channel_id, room_id):
            raise RoomExistsException(room_id)

        self.redis.hdel(RedisKeys.room_name_for_id(), room_id)
        self.redis.delete(RedisKeys.room_roles(room_id))
        self.redis.hdel(RedisKeys.rooms(channel_id), room_id)
        self.redis.delete(RedisKeys.channel_for_rooms(), room_id)

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
