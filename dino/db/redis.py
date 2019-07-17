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
from activitystreams import Activity
from zope.interface import implementer
from datetime import datetime
from typing import Union, Dict
from uuid import uuid4 as uuid
import logging

from dino.db import IDatabase
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.config import RedisKeys
from dino.config import RoleKeys
from dino.config import UserKeys
from dino.config import ApiActions
from dino.utils import b64e
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
from dino.exceptions import EmptyUserNameException
from dino.exceptions import EmptyUserIdException
from dino.exceptions import InvalidAclTypeException
from dino.exceptions import InvalidAclValueException
from dino.exceptions import ChannelNameExistsException
from dino.exceptions import InvalidApiActionException
from dino.exceptions import ValidationException
from dino.exceptions import AclValueNotFoundException

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
        
    def get_all_permanent_rooms(self):
        pass

    def get_room_acls_for_action(self, action) -> Dict[str, Dict[str, str]]:
        pass

    def get_rooms_with_sid(self, user_id: str):
        pass

    def remove_sid_for_user_in_room(self, user_id, room_id, sid_to_remove):
        pass

    def sids_for_user_in_room(self, user_id, room_id):
        pass

    def get_rooms_with_sid(self, user_id: str):
        pass

    def remove_sid_for_user_in_room(self, user_id, room_id, sid_to_remove):
        pass

    def sids_for_user_in_room(self, user_id, room_id):
        return []

    def get_user_for_sid(self, sid: str) -> str:
        return None

    def update_spam_config(self, enabled, max_length, min_length, should_delete, should_save) -> None:
        return

    def set_spam_min_length(self, min_length: int) -> None:
        return

    def set_spam_max_length(self, max_length: int) -> None:
        return

    def enable_spam_delete(self) -> None:
        return

    def disable_spam_delete(self) -> None:
        return

    def enable_spam_save(self) -> None:
        return

    def disable_spam_save(self) -> None:
        return

    def mark_spam_deleted_if_exists(self, message_id: str) -> None:
        return

    def mark_spam_not_deleted_if_exists(self, message_id: str) -> None:
        return

    def get_latest_spam(self, limit: int) -> list:
        return list()

    def get_spam(self, spam_id: int) -> dict:
        return dict()

    def get_spam_for_time_slice(self, room_id, user_id, from_time_int, to_time_int) -> list:
        return list()

    def get_spam_from(self, user_id: str) -> list:
        return list()

    def init_config(self) -> None:
        return

    def get_service_config(self, session=None) -> dict:
        return dict()

    def enable_spam_classifier(self) -> None:
        return

    def disable_spam_classifier(self) -> None:
        return

    def set_spam_correct_or_not(self, spam_id: int, correct: bool):
        pass  # not supported

    def save_spam_prediction(self, activity: Activity, message, y_hats: tuple):
        pass  # not supported

    def set_ephemeral_room(self, room_id: str):
        self.redis.srem(RedisKeys.non_ephemeral_rooms(), room_id)

    def unset_ephemeral_room(self, room_id: str):
        self.redis.sadd(RedisKeys.non_ephemeral_rooms(), room_id)

    def is_room_ephemeral(self, room_id: str) -> bool:
        return not self.redis.sismember(RedisKeys.non_ephemeral_rooms(), room_id)

    def add_words_to_blacklist(self, words: list) -> None:
        self.redis.sadd(RedisKeys.black_list(), words)

    def get_users_roles(self, user_ids: list) -> None:
        raise NotImplementedError('not available in redis implementation of db interface')

    def get_all_user_ids(self) -> list:
        raise NotImplementedError('not available in redis implementation of db interface')

    def remove_word_from_blacklist(self, word_id) -> None:
        raise NotImplementedError('not available in redis implementation of db interface')

    def remove_matching_word_from_blacklist(self, word: str) -> None:
        raise NotImplementedError('not available in redis implementation of db interface')

    def get_black_list_with_ids(self, session=None) -> list:
        raise NotImplementedError('not available in redis implementation of db interface')

    def get_black_list(self) -> set:
        values = self.redis.smembers(RedisKeys.black_list())
        return {str(value, 'utf-8') for value in values}

    def search_for_users(self, query: str) -> list:
        raise NotImplementedError('not implemented in redis db backend')

    def get_user_roles_in_room(self, user_id: str, room_id: str) -> list:
        roles = self.get_user_roles(user_id)
        if room_id in roles['room']:
            return roles['room'][room_id]
        return list()

    def get_user_roles(self, user_id: str) -> dict:
        output = {
            'global': list(),
            'channel': dict(),
            'room': dict()
        }

        checked_channels = set()
        rooms = self.redis.hgetall(RedisKeys.rooms_for_user(user_id))

        global_roles = self.redis.hget(RedisKeys.global_roles(), user_id)
        if global_roles is not None:
            global_roles = str(global_roles, 'utf-8')
            output['global'] = [a for a in global_roles.split(',')]

        for room_id, _ in rooms.items():
            room_id = str(room_id, 'utf-8')
            channel_id = self.channel_for_room(room_id)
            room_roles = self.redis.hget(RedisKeys.room_roles(room_id), user_id)

            if channel_id not in checked_channels:
                checked_channels.add(channel_id)
                channel_roles = self.redis.hget(RedisKeys.channel_roles(channel_id), user_id)
                if channel_roles is not None:
                    channel_roles = str(channel_roles, 'utf-8')
                    output['channel'][channel_id] = [a for a in channel_roles.split(',')]

            if room_roles is not None:
                room_roles = str(room_roles, 'utf-8')
                output['room'][room_id] = [a for a in room_roles.split(',')]
        return output

    def get_admins_in_room(self, room_id: str):
        return list()

    def get_online_admins(self) -> list:
        admins = self.get_super_users()
        return [
            user_id for user_id, status in zip(
                    admins.keys(),
                    [self.get_user_status(user_id) for user_id in admins.keys()]
            )
            if status in [
                UserKeys.STATUS_AVAILABLE,
                UserKeys.STATUS_CHAT,
                UserKeys.STATUS_INVISIBLE
            ]]

    def unset_admin_room(self, room_uuid: str) -> None:
        self.redis.delete(RedisKeys.admin_room())

    def set_admin_room(self, room_uuid: str) -> None:
        self.redis.set(RedisKeys.admin_room(), room_uuid)

    def create_admin_room(self) -> str:
        admin_room_id = self.get_admin_room()
        if admin_room_id is not None:
            return admin_room_id

        try:
            self.create_user('0', 'Admin')
        except UserExistsException:
            pass

        channel_id = str(uuid())
        room_id = str(uuid())

        self.create_channel('Admins', channel_id, '0')

        self.redis.set(RedisKeys.admin_room(), room_id)
        self.redis.hset(RedisKeys.room_name_for_id(), room_id, 'Admins')
        self.redis.hset(RedisKeys.rooms(channel_id), room_id, 'Admins')
        self.redis.hset(RedisKeys.channel_for_rooms(), room_id, channel_id)
        self.redis.sadd(RedisKeys.non_ephemeral_rooms(), room_id)

        acls = {
            RoleKeys.ADMIN: '',
            RoleKeys.SUPER_USER: ''
        }
        samechannel = {
            'samechannel': ''
        }

        self.add_acls_in_channel_for_action(channel_id, ApiActions.LIST, acls)
        self.add_acls_in_channel_for_action(channel_id, ApiActions.JOIN, acls)
        self.add_acls_in_room_for_action(room_id, ApiActions.JOIN, acls)
        self.add_acls_in_room_for_action(room_id, ApiActions.LIST, acls)
        self.add_acls_in_room_for_action(room_id, ApiActions.CROSSROOM, samechannel)
        return room_id

    def get_admin_room(self) -> str:
        room_id = self.redis.get(RedisKeys.admin_room())
        if room_id is None or len(str(room_id, 'utf-8').strip()) == 0:
            return None
        return str(room_id, 'utf-8')

    def get_reason_for_ban_global(self, user_id: str) -> str:
        return ''

    def get_reason_for_ban_channel(self, user_id: str, channel_uuid: str) -> str:
        return ''

    def get_reason_for_ban_room(self, user_id: str, room_uuid: str) -> str:
        return ''

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
        self.get_channel_name(channel_id)
        roles = self.redis.hget(RedisKeys.channel_roles(channel_id), user_id)
        if roles is None:
            roles = role
        else:
            roles = set(str(roles, 'utf-8').split(','))
            roles.add(role)
            roles = ','.join(roles)
        self.redis.hset(RedisKeys.channel_roles(channel_id), user_id, roles)

    def _add_room_role(self, role: str, room_id: str, user_id: str):
        self.get_room_name(room_id)
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

    def is_super_user(self, user_id: str) -> bool:
        return self._has_global_role(user_id, RoleKeys.SUPER_USER)

    def is_admin(self, channel_id: str, user_id: str) -> bool:
        return self._has_role_in_channel(RoleKeys.ADMIN, channel_id, user_id)

    def is_moderator(self, room_id: str, user_id: str) -> bool:
        return self._has_role_in_room(RoleKeys.MODERATOR, room_id, user_id)

    def is_global_moderator(self, user_id: str) -> bool:
        return self._has_global_role(RoleKeys.GLOBAL_MODERATOR, user_id)

    def is_owner(self, room_id: str, user_id: str) -> bool:
        return self._has_role_in_room(RoleKeys.OWNER, room_id, user_id)

    def is_owner_channel(self, channel_id: str, user_id: str) -> bool:
        return self._has_role_in_channel(RoleKeys.OWNER, channel_id, user_id)

    def set_admin(self, channel_id: str, user_id: str):
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)
        self._add_channel_role(RoleKeys.ADMIN, channel_id, user_id)

    def set_moderator(self, room_id: str, user_id: str):
        self._add_room_role(RoleKeys.MODERATOR, room_id, user_id)

    def set_global_moderator(self, room_id: str, user_id: str):
        self._add_global_role(user_id, RoleKeys.GLOBAL_MODERATOR)

    def set_owner(self, room_id: str, user_id: str):
        self._add_room_role(RoleKeys.OWNER, room_id, user_id)

    def set_owner_channel(self, channel_id: str, user_id: str):
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

    def remove_super_user(self, user_id: str) -> None:
        self._remove_global_role(user_id, RoleKeys.SUPER_USER)

    def remove_global_moderator(self, user_id: str) -> None:
        self._remove_global_role(user_id, RoleKeys.GLOBAL_MODERATOR)

    def remove_owner(self, room_id: str, user_id: str) -> None:
        if not self.channel_for_room(room_id):
            raise NoSuchRoomException(room_id)
        self._remove_room_role(RoleKeys.OWNER, room_id, user_id)

    def get_channels(self) -> dict:
        all_channels = self.redis.hgetall(RedisKeys.channels())
        clean = dict()

        for channel_id, channel_name in all_channels.items():
            # second argument in tuple is sort order, but it's not supported with redis db
            clean[str(channel_id, 'utf-8')] = (str(channel_name, 'utf-8'), 1, 'normal')
        return clean

    def update_room_sort_order(self, room_uuid: str, sort_order: int) -> None:
        # not supported in redis db
        pass

    def update_channel_sort_order(self, channel_uuid: str, sort: int) -> None:
        # not supported in redis db
        pass

    def rooms_for_channel_without_info(self, channel_id: str) -> dict:
        rooms = self.rooms_for_channel(channel_id)
        return {
            room_id: {
                'name': room['name'],
                'ephemeral': room['ephemeral']
            } for room_id, room in rooms.items()
        }

    def rooms_for_channel(self, channel_id) -> dict:
        all_rooms = self.redis.hgetall(RedisKeys.rooms(channel_id))
        clean = dict()

        for room_id, room_name in all_rooms.items():
            if room_name is None:
                raise NoRoomNameException(room_id)

            room_id = str(room_id, 'utf-8')
            clean[room_id] = {
                'name': str(room_name, 'utf-8'),
                'sort_order': 1,
                'ephemeral': self.is_room_ephemeral(room_id),
                'users': len(self.users_in_room(room_id))
            }
        return clean

    def room_exists(self, channel_id: str, room_id: str) -> bool:
        return self.redis.hexists(RedisKeys.rooms(channel_id), room_id)

    def get_room_id_for_name(self, room_name: str) -> str:
        raise NotImplementedError('redis db does not support getting room id from name')

    def room_name_exists(self, channel_id, room_name: str) -> bool:
        cleaned = set()
        for existing_room_name in self.redis.hvals(RedisKeys.rooms(channel_id)):
            cleaned.add(str(existing_room_name, 'utf-8').lower())

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
        if user_name is None or len(user_name.strip()) == 0:
            raise EmptyUserNameException(user_id)

        if user_id is None or len(user_id.strip()) == 0:
            raise EmptyUserIdException()

        try:
            self.get_user_name(user_id)
            raise UserExistsException(user_id)
        except NoSuchUserException:
            pass

        key = RedisKeys.auth_key(user_id)
        self.redis.hset(key, SessionKeys.user_id.value, user_id)
        self.redis.hset(key, SessionKeys.user_name.value, user_name)
        self.redis.hset(RedisKeys.user_names(), user_id, user_name)

    def get_avatars_for(self, user_ids: set) -> dict:
        return dict()

    def room_contains(self, room_id: str, user_id: str) -> bool:
        self.get_room_name(room_id)
        self.channel_for_room(room_id)
        return self.redis.hexists(RedisKeys.users_in_room(room_id), user_id)

    def users_in_room(self, room_id: str, this_user_id: str=None, skip_cache: bool=False) -> dict:
        try:
            self.get_room_name(room_id)
        except NoSuchRoomException:
            return dict()

        self.channel_for_room(room_id)

        users = self.redis.hgetall(RedisKeys.users_in_room(room_id))
        cleaned_users = dict()
        for user_id, user_name in users.items():
            user_id = str(user_id, 'utf-8')
            cleaned_users[user_id] = str(user_name, 'utf-8')
        return cleaned_users

    def leave_room(self, user_id: str, room_id: str) -> None:
        self.get_room_name(room_id)
        self.redis.hdel(RedisKeys.users_in_room(room_id), user_id)
        self.redis.hdel(RedisKeys.rooms_for_user(user_id), room_id)

    def delete_acl_in_room_for_action(self, room_id: str, acl_type: str, action: str) -> None:
        self.get_room_name(room_id)
        self.channel_for_room(room_id)

        if action not in ApiActions.all_api_actions:
            raise InvalidApiActionException(action)

        key = '%s|%s' % (action, acl_type)
        self.redis.hdel(RedisKeys.room_acl(room_id), key)

    def add_default_room(self, room_id: str) -> None:
        self.redis.sadd(RedisKeys.default_rooms(), room_id)

    def remove_default_room(self, room_id: str) -> None:
        self.redis.srem(RedisKeys.default_rooms(), room_id)

    def get_default_rooms(self) -> list:
        self.redis.smembers(RedisKeys.default_rooms())

    def delete_acl_in_channel_for_action(self, channel_id: str, acl_type: str, action: str) -> None:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)

        if action not in ApiActions.all_api_actions:
            raise InvalidApiActionException(action)

        key = '%s|%s' % (action, acl_type)
        self.redis.hdel(RedisKeys.channel_acl(channel_id), key)

    def get_temp_rooms_user_is_owner_for(self, user_id: str) -> None:
        return list()

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

            acl_configs['validation'][acl_type]['value'].validate_new_acl(acl_value)
            key = '%s|%s' % (action, acl_type)
            new_acls[key] = acl_value

        if len(new_acls) == 0:
            return
        self.redis.hmset(RedisKeys.channel_acl(channel_id), new_acls)

    def add_acls_in_room_for_action(self, room_id: str, action: str, acls: dict) -> None:
        if self.channel_for_room(room_id) is None:
            raise NoSuchRoomException(room_id)

        if action not in ApiActions.all_api_actions:
            raise InvalidApiActionException(action)

        acl_configs = environ.env.config.get(ConfigKeys.ACL)

        new_acls = dict()
        for acl_type, acl_value in acls.items():
            if acl_type not in acl_configs['available']['acls']:
                raise InvalidAclTypeException(acl_type)

            acl_configs['validation'][acl_type]['value'].validate_new_acl(acl_value)
            key = '%s|%s' % (action, acl_type)
            new_acls[key] = acl_value

        if len(new_acls) == 0:
            return
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
        end = datetime.fromtimestamp(float(time))
        if now > end:
            self.redis.hdel(RedisKeys.banned_users(), user_id)
            return False, None
        return True, time

    def is_banned_from_channel(self, channel_id: str, user_id: str) -> (bool, Union[str, None]):
        ban = self.redis.hget(RedisKeys.banned_users_channel(channel_id), user_id)
        is_banned, time = self._is_banned(ban)
        if not is_banned:
            return False, None

        now = datetime.utcnow()
        end = datetime.fromtimestamp(float(time))
        if now > end:
            self.redis.hdel(RedisKeys.banned_users(), user_id)
            return False, None
        return True, time

    def is_banned_from_room(self, room_id: str, user_id: str) -> (bool, Union[str, None]):
        ban = self.redis.hget(RedisKeys.banned_users(room_id), user_id)
        is_banned, time = self._is_banned(ban)
        if not is_banned:
            return False, None

        now = datetime.utcnow()
        end = datetime.fromtimestamp(float(time))
        if now > end:
            self.redis.hdel(RedisKeys.banned_users(), user_id)
            return False, None
        return True, time

    def remove_global_ban(self, user_id: str) -> str:
        self.redis.hdel(RedisKeys.banned_users(), user_id)

    def remove_channel_ban(self, channel_id: str, user_id: str) -> str:
        self.redis.hdel(RedisKeys.banned_users_channel(channel_id), user_id)

    def remove_channel(self, channel_id: str) -> None:
        self.redis.hdel(RedisKeys.channels(), channel_id)
        self.redis.hdel(RedisKeys.banned_users_channel(channel_id))
        self.redis.hdel(RedisKeys.channel_acl(channel_id))

    def remove_room_ban(self, room_id: str, user_id: str) -> str:
        self.redis.hdel(RedisKeys.banned_users(room_id), user_id)

    def get_bans_for_user(self, user_id: str, session=None) -> dict:
        def _to_date(_timestamp):
            return datetime.fromtimestamp(int(_timestamp)).strftime(ConfigKeys.DEFAULT_DATE_FORMAT)

        now = datetime.utcnow()
        all_channels = self.redis.hgetall(RedisKeys.channels())
        channel_ids = list()
        room_ids = list()

        output = {
            'global': dict(),
            'room': dict(),
            'channel': dict()
        }

        for channel_id, _ in all_channels.items():
            channel_ids.append(str(channel_id, 'utf-8'))

        for channel_id in channel_ids:
            all_rooms = self.redis.hgetall(RedisKeys.rooms(channel_id))

            for room_id, _ in all_rooms.items():
                room_ids.append(str(room_id, 'utf-8'))

        for channel_id in channel_ids:
            r_key = RedisKeys.banned_users_channel(channel_id)
            if not self.redis.hexists(r_key, user_id):
                continue

            ban_info = self.redis.hget(RedisKeys, r_key)
            ban_duration, ban_timestamp, _ = ban_info.split('|', 2)
            if datetime.fromtimestamp(int(ban_timestamp)) < now:
                self.redis.hdel(r_key, user_id)
                continue

            output['channel'][channel_id] = {
                'name': b64e(self.get_channel_name(channel_id)),
                'duration': ban_duration,
                'timestamp': _to_date(ban_timestamp)
            }

        for room_id in room_ids:
            r_key = RedisKeys.banned_users(room_id)
            if not self.redis.hexists(r_key, user_id):
                continue

            ban_info = self.redis.hget(RedisKeys, r_key)
            ban_duration, ban_timestamp, _ = ban_info.split('|', 2)
            if datetime.fromtimestamp(int(ban_timestamp)) < now:
                self.redis.hdel(r_key, user_id)
                continue

            output['room'][room_id] = {
                'name': b64e(self.get_room_name(room_id)),
                'duration': ban_duration,
                'timestamp': _to_date(ban_timestamp)
            }

        r_key = RedisKeys.banned_users()
        if self.redis.hexists(r_key, user_id):
            ban_info = self.redis.hget(RedisKeys.banned_users(), user_id)
            ban_duration, ban_timestamp, _ = ban_info.split('|', 2)
            if datetime.fromtimestamp(int(ban_timestamp)) < now:
                self.redis.hdel(r_key, user_id)
            else:
                output['global'] = {
                    'duration': ban_duration,
                    'timestamp': _to_date(ban_timestamp)
                }
        return output

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

    def get_banned_users_global(self) -> dict:
        now = datetime.utcnow()
        output = dict()

        def for_global_ban(_user_id, _ban_info):
            ban_duration, ban_timestamp, username = _ban_info.split('|', 2)
            if datetime.fromtimestamp(int(ban_timestamp)) < now:
                self.redis.hdel(RedisKeys.banned_users(), _user_id)
                return

            output[_user_id] = {
                'name': b64e(self.get_user_name(_user_id)),
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

        def for_local_ban_channel(_user_id, _channel_id, _ban_info):
            ban_duration, ban_timestamp, username = _ban_info.split('|', 2)
            if datetime.fromtimestamp(int(ban_timestamp)) < now:
                self.redis.hdel(RedisKeys.banned_users_channel(_channel_id), _user_id)
                return

            output[_user_id] = {
                'name': b64e(self.get_user_name(_user_id)),
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

        def for_local_ban(_user_id, _room_id, _ban_info):
            ban_duration, ban_timestamp, username = _ban_info.split('|', 2)
            if datetime.fromtimestamp(int(ban_timestamp)) < now:
                self.redis.hdel(RedisKeys.banned_users(_room_id), _user_id)
                return

            output[_user_id] = {
                'name': b64e(self.get_user_name(_user_id)),
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
                bans = {
                    'name': b64e(self.get_channel_name(channel_id)),
                    'users': self.get_banned_users_for_channel(channel_id)
                }
                if len(bans['users']) > 0:
                    output[channel_id] = bans
            return output

        def get_banned_users_all_rooms() -> dict:
            output = dict()
            for channel_id, _ in all_channels.items():
                channel_id = str(channel_id, 'utf-8')
                rooms_for_channel = self.redis.hgetall(RedisKeys.rooms(channel_id))
                for room_id, _ in rooms_for_channel.items():
                    room_id = str(room_id, 'utf-8')
                    bans = {
                        'name': b64e(self.get_room_name(room_id)),
                        'users': self.get_banned_users_for_room(room_id)
                    }
                    if len(bans['users']) > 0:
                        output[room_id] = bans
            return output

        return {
            'global': self.get_banned_users_global(),
            'channels': get_banned_users_all_channels(),
            'rooms': get_banned_users_all_rooms()
        }

    def kick_user(self, room_id: str, user_id: str) -> None:
        self.leave_room(user_id, room_id)

    def _get_ban_timestamp(self, ban) -> (str, str, str):
        if ban is None:
            return None, None, None
        ban = str(ban, 'utf-8')
        return ban.split('|', 2)

    def get_global_ban_timestamp(self, user_id: str) -> (str, str, str):
        ban = self.redis.hget(RedisKeys.banned_users(), user_id)
        return self._get_ban_timestamp(ban)

    def get_channel_ban_timestamp(self, channel_id: str, user_id: str) -> (str, str, str):
        ban = self.redis.hget(RedisKeys.banned_users_channel(channel_id), user_id)
        return self._get_ban_timestamp(ban)

    def get_room_ban_timestamp(self, room_id: str, user_id: str) -> (str, str, str):
        ban = self.redis.hget(RedisKeys.banned_users(room_id), user_id)
        return self._get_ban_timestamp(ban)

    def ban_user_global(self, user_id: str, ban_timestamp: str, ban_duration: str, reason: str=None, banner_id: str=None):
        user_name = ''
        try:
            user_name = self.get_user_name(user_id)
        except NoSuchUserException:
            pass
        self.redis.hset(RedisKeys.banned_users(), user_id, '%s|%s|%s' % (ban_duration, ban_timestamp, user_name))

    def ban_user_room(self, user_id: str, ban_timestamp: str, ban_duration: str, room_id: str, reason: str=None, banner_id: str=None):
        try:
            self.channel_for_room(room_id)
        except NoChannelFoundException:
            raise NoSuchRoomException(room_id)

        user_name = ''
        try:
            user_name = self.get_user_name(user_id)
        except NoSuchUserException:
            pass
        self.redis.hset(RedisKeys.banned_users(room_id), user_id, '%s|%s|%s' % (ban_duration, ban_timestamp, user_name))

    def ban_user_channel(self, user_id: str, ban_timestamp: str, ban_duration: str, channel_id: str, reason: str=None, banner_id: str=None):
        user_name = ''
        try:
            user_name = self.get_user_name(user_id)
        except NoSuchUserException:
            pass
        self.redis.hset(RedisKeys.banned_users_channel(channel_id), user_id, '%s|%s|%s' % (ban_duration, ban_timestamp, user_name))

    def get_acls_in_room_for_action(self, room_id: str, action: str) -> dict:
        self.get_room_name(room_id)
        self.channel_for_room(room_id)

        acls = self.redis.hgetall(RedisKeys.room_acl(room_id))
        acls_cleaned = dict()

        for acl_key, acl_value in acls.items():
            acl_action, acl_type = str(acl_key, 'utf-8').split('|', 1)
            if acl_action != action:
                continue
            acls_cleaned[acl_type] = str(acl_value, 'utf-8')

        return acls_cleaned

    def get_acls_in_channel_for_action(self, channel_id: str, action: str) -> dict:
        self.get_channel_name(channel_id)

        acls = self.redis.hgetall(RedisKeys.channel_acl(channel_id))
        acls_cleaned = dict()

        for acl_key, acl_value in acls.items():
            acl_action, acl_type = str(acl_key, 'utf-8').split('|', 1)
            if acl_action != action:
                continue
            acls_cleaned[acl_type] = str(acl_value, 'utf-8')

        return acls_cleaned

    def get_acl_validation_value(self, acl_type: str, validation_method: str) -> str:
        if acl_type is None or len(acl_type.strip()) == 0:
            raise InvalidAclTypeException(acl_type)

        if validation_method is None or len(validation_method.strip()) == 0:
            raise InvalidAclValueException(acl_type, validation_method)

        value = environ.env.redis.hget(RedisKeys.acl_validations(acl_type), validation_method)
        if value is None:
            raise AclValueNotFoundException(acl_type, validation_method)

        value = str(value, 'utf-8')
        if len(value.strip()) == 0:
            raise AclValueNotFoundException(acl_type, validation_method)

        return value

    def get_all_acls_channel(self, channel_id: str) -> dict:
        self.get_channel_name(channel_id)

        acls = self.redis.hgetall(RedisKeys.channel_acl(channel_id))
        acls_cleaned = dict()

        for acl_key, acl_value in acls.items():
            acl_action, acl_type = str(acl_key, 'utf-8').split('|', 1)
            if acl_action not in acls_cleaned:
                acls_cleaned[acl_action] = dict()
            acls_cleaned[acl_action][acl_type] = str(acl_value, 'utf-8')

        return acls_cleaned

    def get_all_acls_room(self, room_id: str) -> dict:
        self.get_room_name(room_id)
        self.channel_for_room(room_id)

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

        self.get_room_name(room_id)

        channel_id = self.redis.hget(RedisKeys.channel_for_rooms(), room_id)
        if channel_id is None:
            raise NoChannelFoundException(room_id)
        channel_id = str(channel_id, 'utf-8')
        self.env.cache.set_channel_for_room(channel_id, room_id)
        return channel_id

    def set_user_name(self, user_id: str, user_name: str) -> None:
        self.redis.hset(RedisKeys.auth_key(user_id), SessionKeys.user_name.value, user_name)
        self.redis.hset(RedisKeys.user_names(), user_id, user_name)

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

    def add_sid_for_user(self, user_id: str, sid: str) -> None:
        if user_id is None or len(user_id.strip()) == 0:
            raise EmptyUserIdException(user_id)
        self.redis.hset(RedisKeys.sid_for_user_id(), user_id, sid)

    def reset_sids_for_user(self, user_id: str) -> None:
        if user_id is None or len(user_id.strip()) == 0:
            raise EmptyUserIdException(user_id)
        self.redis.hdel(RedisKeys.sid_for_user_id(), user_id)

    def remove_sid_for_user(self, user_id: str, sid: str) -> None:
        self.reset_sids_for_user(user_id)

    def get_sids_for_user(self, user_id: str) -> list:
        if user_id is None or len(user_id.strip()) == 0:
            raise EmptyUserIdException(user_id)
        sid = self.redis.hget(RedisKeys.sid_for_user_id(), user_id)
        if sid is None:
            return list()
        return [str(sid, 'utf-8')]

    def _get_users_with_role_in_channel(self, channel_id: str, role_key: str):
        roles = self.redis.hgetall(RedisKeys.channel_roles(channel_id))
        return self._get_users_with_role(roles, role_key)

    def _get_users_with_role_in_room(self, room_id: str, role_key: str):
        roles = self.redis.hgetall(RedisKeys.room_roles(room_id))
        return self._get_users_with_role(roles, role_key)

    def get_admins_channel(self, channel_id: str) -> dict:
        self.get_channel_name(channel_id)
        return self._get_users_with_role_in_channel(channel_id, RoleKeys.ADMIN)

    def get_owners_channel(self, channel_id: str) -> dict:
        self.get_channel_name(channel_id)
        return self._get_users_with_role_in_channel(channel_id, RoleKeys.OWNER)

    def get_owners_room(self, room_id: str) -> dict:
        self.get_room_name(room_id)
        return self._get_users_with_role_in_room(room_id, RoleKeys.OWNER)

    def get_moderators_room(self, room_id: str) -> dict:
        self.get_room_name(room_id)
        return self._get_users_with_role_in_room(room_id, RoleKeys.MODERATOR)

    def remove_current_rooms_for_user(self, user_id: str) -> None:
        self.redis.delete(RedisKeys.rooms_for_user(user_id))

    def get_room_name(self, room_id: str) -> str:
        room_name = self.redis.hget(RedisKeys.room_name_for_id(), room_id)
        if room_name is None:
            raise NoSuchRoomException(room_id)
        return room_name.decode('utf-8')

    def get_user_infos(self, user_ids: set) -> dict:
        infos = dict()

        for user_id in user_ids:
            infos[user_id] = dict()

        return infos

    def set_user_info(self, user_id: str, user_info: dict) -> None:
        pass

    def get_channel_name(self, channel_id: str) -> str:
        channel_name = self.env.cache.get_channel_name(channel_id)
        if channel_name is not None:
            return channel_name

        channel_name = self.redis.hget(RedisKeys.channels(), channel_id)
        if channel_name is None:
            raise NoSuchChannelException(channel_id)
        channel_name = str(channel_name, 'utf-8')
        self.env.cache.set_channel_name(channel_id, channel_name)
        return channel_name

    def rooms_for_user(self, user_id: str, skip_cache: bool = False) -> dict:
        clean_rooms = dict()

        rooms = self.redis.hgetall(RedisKeys.rooms_for_user(user_id))
        for room_id, room_name in rooms.items():
            room_id, room_name = str(room_id, 'utf-8'), str(room_name, 'utf-8')
            clean_rooms[room_id] = room_name
        return clean_rooms

    def join_room(self, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
        self.redis.hset(RedisKeys.rooms_for_user(user_id), room_id, room_name)
        self.redis.hset(RedisKeys.users_in_room(room_id), user_id, user_name)

    def create_channel(self, channel_name, channel_id, user_id) -> None:
        if self.channel_exists(channel_id):
            raise ChannelExistsException(channel_id)

        if channel_name is None or len(channel_name.strip()) == 0:
            raise EmptyChannelNameException(channel_id)

        if self.channel_name_exists(channel_name):
            raise ChannelNameExistsException(channel_name)

        self.env.cache.set_channel_exists(channel_id)
        self.redis.hset(RedisKeys.channels(), channel_id, channel_name)
        self.set_owner_channel(channel_id, user_id)

    def create_room(self, room_name: str, room_id: str, channel_id: str, user_id: str, user_name: str, ephemeral: bool=True, sort_order: int=False) -> None:
        if self.env.cache.get_channel_exists(channel_id) is None:
            if not self.channel_exists(channel_id):
                raise NoSuchChannelException(channel_id)

        if room_name is None or len(room_name.strip()) == 0:
            raise EmptyRoomNameException(room_id)

        if self.room_exists(channel_id, room_id):
            raise RoomExistsException(room_id)

        if self.room_name_exists(channel_id, room_name):
            raise RoomNameExistsForChannelException(channel_id, room_name)

        if ephemeral:
            self.redis.sadd(RedisKeys.non_ephemeral_rooms(), room_id)

        self.redis.hset(RedisKeys.room_name_for_id(), room_id, room_name)
        self.redis.hset(RedisKeys.rooms(channel_id), room_id, room_name)
        self.redis.hset(RedisKeys.channel_for_rooms(), room_id, channel_id)
        self.redis.hset(RedisKeys.user_names(), user_id, user_name)
        self.set_owner(room_id, user_id)

    def rename_channel(self, channel_id: str, channel_name: str) -> None:
        self.get_channel_name(channel_id)
        if self.channel_name_exists(channel_name):
            raise ChannelNameExistsException(channel_name)

        if channel_name is None or len(channel_name.strip()) == 0:
            raise EmptyChannelNameException(channel_id)

        self.redis.hset(RedisKeys.channels(), channel_id, channel_name)
        self.env.cache.set_channel_name(channel_id, channel_name)

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

        self.redis.hset(RedisKeys.room_name_for_id(), room_id, room_name)
        self.redis.hset(RedisKeys.rooms(channel_id), room_id, room_name)

    def type_of_rooms_in_channel(self, channel_id: str) -> str:
        return 'mix'

    def remove_room(self, channel_id: str, room_id: str) -> None:
        if self.env.cache.get_channel_exists(channel_id) is None:
            if not self.channel_exists(channel_id):
                raise NoSuchChannelException(channel_id)

        if not self.room_exists(channel_id, room_id):
            raise NoSuchRoomException(room_id)

        self.redis.srem(RedisKeys.non_ephemeral_rooms(), room_id)
        self.redis.hdel(RedisKeys.room_name_for_id(), room_id)
        self.redis.delete(RedisKeys.room_roles(room_id))
        self.redis.hdel(RedisKeys.rooms(channel_id), room_id)
        self.redis.hdel(RedisKeys.channel_for_rooms(), room_id)

    def get_user_status(self, user_id: str, skip_cache: bool = False) -> str:
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
        self.redis.set(RedisKeys.user_status(user_id), UserKeys.STATUS_AVAILABLE)

    def set_user_invisible(self, user_id: str, is_offline=False) -> None:
        if is_offline:
            self.env.cache.setUser_status_invisible(user_id)
        else:
            self.env.cache.set_user_invisible(user_id)

    def update_last_read_for(self, users: set, room_id: str, time_stamp: int) -> None:
        self.get_room_name(room_id)
        redis_key = RedisKeys.last_read(room_id)
        for user_id in users:
            self.redis.hset(redis_key, user_id, time_stamp)

    def get_last_read_timestamp(self, room_id: str, user_id: str) -> int:
        timestamp = self.redis.hget(RedisKeys.last_read(room_id), user_id)
        if timestamp is None:
            return None
        return int(str(timestamp, 'utf-8'))
