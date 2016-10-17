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

from enum import Enum

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


# TODO: session keys should be configurable, and config should also contain whether or not they're required
class SessionKeys(Enum):
    user_id = 'user_id'
    user_name = 'user_name'
    age = 'age'
    gender = 'gender'
    membership = 'membership'
    group = 'group'
    country = 'country'
    city = 'city'
    image = 'image'
    has_webcam = 'has_webcam'
    fake_checked = 'fake_checked'
    token = 'token'

    requires_session_keys = {
        user_id,
        user_name,
        token
    }


class ConfigKeys(object):
    LOG_LEVEL = 'log_level'
    LOG_FORMAT = 'log_format'
    DEBUG = 'debug'
    QUEUE = 'queue'
    TESTING = 'testing'
    STORAGE = 'storage'
    AUTH_SERVICE = 'auth'
    HOST = 'host'
    TYPE = 'type'
    MAX_HISTORY = 'max_history'
    STRATEGY = 'strategy'
    REPLICATION = 'replication'
    DATABASE = 'database'
    DB = 'db'

    # will be overwritten even if specified in config file
    ENVIRONMENT = '_environment'
    VERSION = '_version'
    LOGGER = '_logger'
    REDIS = '_redis'
    SESSION = '_session'

    DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)-18s - %(levelname)-7s - %(message)s"
    DEFAULT_LOG_LEVEL = 'INFO'
    DEFAULT_REDIS_HOST = 'localhost'


class RedisKeys(object):
    RKEY_ROOMS_FOR_USER = 'user:rooms:%s'  # user:rooms:user_id
    RKEY_USERS_IN_ROOM = 'room:%s'  # room:room_id
    RKEY_ROOMS = 'rooms'
    RKEY_ONLINE_BITMAP = 'users:online:bitmap'
    RKEY_ONLINE_SET = 'users:online:set'
    RKEY_MULTI_CAST = 'users:multicat'
    RKEY_USER_STATUS = 'user:status:%s'  # user:status:user_id
    RKEY_ROOM_NAME = 'room:name:%s'  # room:name:room_id
    RKEY_ROOM_ACL = 'room:acl:%s'  # room:acl:room_id
    RKEY_ROOM_OWNERS = 'room:owners:%s'  # room:owners:room_id
    RKEY_ROOM_HISTORY = 'room:history:%s'  # room:history:room_id
    RKEY_AUTH = 'user:auth:%s'  # user:auth:user_id
    RKEY_USER_ROLES = 'user:roles:%s'  # user:roles:user_id

    REDIS_STATUS_AVAILABLE = '1'
    # REDIS_STATUS_CHAT = '2'
    REDIS_STATUS_INVISIBLE = '3'
    REDIS_STATUS_UNAVAILABLE = '4'

    # REDIS_STATUS_UNKNOWN = '5'

    @staticmethod
    def rooms_for_user(user_id: str) -> str:
        return RedisKeys.RKEY_ROOMS_FOR_USER % user_id

    @staticmethod
    def users_in_room(room_id: str) -> str:
        return RedisKeys.RKEY_USERS_IN_ROOM % room_id

    @staticmethod
    def rooms() -> str:
        return RedisKeys.RKEY_ROOMS

    @staticmethod
    def room_name_for_id(room_id: str) -> str:
        return RedisKeys.RKEY_ROOM_NAME % room_id

    @staticmethod
    def online_bitmap() -> str:
        return RedisKeys.RKEY_ONLINE_BITMAP

    @staticmethod
    def online_set() -> str:
        return RedisKeys.RKEY_ONLINE_SET

    @staticmethod
    def users_multi_cast() -> str:
        return RedisKeys.RKEY_MULTI_CAST

    @staticmethod
    def user_status(user_id: str) -> str:
        return RedisKeys.RKEY_USER_STATUS % user_id

    @staticmethod
    def room_history(room_id: str) -> str:
        return RedisKeys.RKEY_ROOM_HISTORY % room_id

    @staticmethod
    def room_acl(room_id: str) -> dict:
        return RedisKeys.RKEY_ROOM_ACL % room_id

    @staticmethod
    def room_owners(room_id: str) -> str:
        return RedisKeys.RKEY_ROOM_OWNERS % room_id

    @staticmethod
    def auth_key(user_id: str) -> str:
        return RedisKeys.RKEY_AUTH % user_id

    @staticmethod
    def user_roles(user_id: str) -> str:
        return RedisKeys.RKEY_USER_ROLES % user_id
