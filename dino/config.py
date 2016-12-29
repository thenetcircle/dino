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
import base64

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
    crossgroup = 'crossgroup'  # TODO: rename to crossroom
    has_webcam = 'has_webcam'
    fake_checked = 'fake_checked'
    token = 'token'

    requires_session_keys = {
        user_id,
        user_name,
        token
    }


class ErrorCodes(object):
    OK = 200
    UNKNOWN_ERROR = 250

    NO_SUCH_USER = 300
    NO_SUCH_CHANNEL = 301
    NO_SUCH_ROOM = 302
    NO_ADMIN_ROOM_FOUND = 303
    NO_USER_IN_SESSION = 304

    EMPTY_MESSAGE = 400
    NOT_BASE64 = 401
    USER_NOT_IN_ROOM = 402
    USER_IS_BANNED = 403
    ROOM_ALREADY_EXISTS = 404
    NOT_ALLOWED = 405

    MISSING_ACTOR_ID = 500
    MISSING_OBJECT_ID = 501
    MISSING_TARGET_ID = 502
    MISSING_OBJECT_URL = 503
    MISSING_TARGET_DISPLAY_NAME = 504
    MISSING_ACTOR_URL = 505
    MISSING_OBJECT_CONTENT = 506

    INVALID_TARGET_TYPE = 600
    INVALID_ACL_TYPE = 601
    INVALID_ACL_ACTION = 602
    INVALID_ACL_VALUE = 603
    INVALID_STATUS = 604
    INVALID_OBJECT_TYPE = 605
    INVALID_BAN_DURATION = 606


class ApiTargets(object):
    ROOM = 'room'
    CHANNEL = 'channel'


class ApiActions(object):
    all_api_actions = list()

    JOIN = 'join'
    CROSSROOM = 'crossroom'
    MESSAGE = 'message'
    KICK = 'kick'
    BAN = 'ban'
    LIST = 'list'
    HISTORY = 'history'
    SETACL = 'setacl'

ApiActions.all_api_actions = \
    [getattr(ApiActions, d) for d in ApiActions.__dict__ if not d.startswith('_') and not d[0].islower()]


class RoleKeys(object):
    OWNER = 'owner'
    MODERATOR = 'moderator'
    ADMIN = 'admin'
    SUPER_USER = 'superuser'


class UserKeys(object):
    STATUS_AVAILABLE = '1'
    STATUS_CHAT = '2'
    STATUS_INVISIBLE = '3'
    STATUS_UNAVAILABLE = '4'
    STATUS_UNKNOWN = '5'


class ConfigKeys(object):
    LOG_LEVEL = 'log_level'
    LOG_FORMAT = 'log_format'
    DATE_FORMAT = 'date_format'
    DEBUG = 'debug'
    QUEUE = 'queue'
    EXTERNAL_QUEUE = 'ext_queue'
    EXCHANGE = 'exchange'
    TESTING = 'testing'
    STORAGE = 'storage'
    AUTH_SERVICE = 'auth'
    CACHE_SERVICE = 'cache'
    STATS_SERVICE = 'stats'
    HOST = 'host'
    TYPE = 'type'
    DRIVER = 'driver'
    STRATEGY = 'strategy'
    REPLICATION = 'replication'
    DATABASE = 'database'
    DB = 'db'
    PORT = 'port'
    VHOST = 'vhost'
    USER = 'user'
    PASSWORD = 'password'
    HISTORY = 'history'
    LIMIT = 'limit'
    PREFIX = 'prefix'
    INCLUDE_HOST_NAME = 'include_hostname'

    # will be overwritten even if specified in config file
    ENVIRONMENT = '_environment'
    VERSION = '_version'
    LOGGER = '_logger'
    REDIS = '_redis'
    SESSION = '_session'
    ACL = '_acl'

    DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)-18s - %(levelname)-7s - %(message)s"
    DEFAULT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
    DEFAULT_LOG_LEVEL = 'INFO'
    DEFAULT_REDIS_HOST = 'localhost'
    DEFAULT_HISTORY_LIMIT = 500
    DEFAULT_HISTORY_STRATEGY = 'top'

    HISTORY_TYPE_UNREAD = 'unread'
    HISTORY_TYPE_TOP = 'top'


class RedisKeys(object):
    RKEY_ROOMS_FOR_USER = 'user:rooms:%s'  # user:rooms:user_id
    RKEY_USERS_IN_ROOM = 'room:%s'  # room:room_id
    RKEY_ROOMS = 'rooms:%s'  # room:channel_id
    RKEY_ONLINE_BITMAP = 'users:online:bitmap'
    RKEY_ONLINE_SET = 'users:online:set'
    RKEY_MULTI_CAST = 'users:multicat'
    RKEY_USER_STATUS = 'user:status:%s'  # user:status:user_id
    RKEY_ROOM_NAME = 'room:names'
    RKEY_ROOM_ACL = 'room:acl:%s'  # room:acl:room_id
    RKEY_CHANNEL_ACL = 'channel:acl:%s'  # channel:acl:channel_id
    RKEY_ROOM_HISTORY = 'room:history:%s'  # room:history:room_id
    RKEY_AUTH = 'user:auth:%s'  # user:auth:user_id
    RKEY_CHANNELS = 'channels'
    RKEY_CHANNEL_EXISTS = 'channel:exists'
    RKEY_ROOM_ID_FOR_NAME = 'room:id:%s'  # room:id:channel_id
    RKEY_CHANNEL_ROLES = 'channel:roles:%s'  # channel:roles:channel_id
    RKEY_GLOBAL_ROLES = 'global:roles'
    RKEY_ROOM_ROLES = 'room:roles:%s'  # channel:roles:channel_id
    RKEY_CHANNEL_FOR_ROOMS = 'room:channel'
    RKEY_LAST_READ = 'room:read:%s'  # room:read:room_id
    RKEY_USER_NAMES = 'user:names'
    RKEY_ROOMS_ADMINS = 'room:admins'
    RKEY_ACL_VALIDATION = 'acl:validation:%s'  # acl:validation:acl_type (e.g. acl:validation:gender)
    RKEY_USER_ROLES = 'users:roles'

    RKEY_SID_TO_USER_ID = 'user:sid:map'
    RKEY_BANNED_USERS_GLOBAL = 'users:banned:global'
    RKEY_BANNED_USERS_ROOM = 'users:banned:room:%s'  # users:banned:room:room_id
    RKEY_BANNED_USERS_CHANNEL = 'users:banned:channel:%s'  # users:banned:channel:channel_id

    @staticmethod
    def user_roles() -> str:
        return RedisKeys.RKEY_USER_ROLES

    @staticmethod
    def acl_validations(acl_type: str) -> str:
        return RedisKeys.RKEY_ACL_VALIDATION % acl_type

    @staticmethod
    def user_names() -> str:
        return RedisKeys.RKEY_USER_NAMES

    @staticmethod
    def sid_for_user_id() -> str:
        return RedisKeys.RKEY_SID_TO_USER_ID

    @staticmethod
    def banned_users(room_id: str=None) -> str:
        if room_id is None:
            return RedisKeys.RKEY_BANNED_USERS_GLOBAL
        return RedisKeys.RKEY_BANNED_USERS_ROOM % room_id

    @staticmethod
    def banned_users_channel(channel_id: str):
        return RedisKeys.RKEY_BANNED_USERS_CHANNEL % channel_id

    @staticmethod
    def last_read(room_id: str) -> str:
        return RedisKeys.RKEY_LAST_READ % room_id

    @staticmethod
    def channel_roles(channel_id: str) -> str:
        return RedisKeys.RKEY_CHANNEL_ROLES % channel_id

    @staticmethod
    def room_roles(room_id: str) -> str:
        return RedisKeys.RKEY_ROOM_ROLES % room_id

    @staticmethod
    def global_roles() -> str:
        return RedisKeys.RKEY_GLOBAL_ROLES

    @staticmethod
    def room_id_for_name(channel_id: str) -> str:
        # separate room name/id mapping per channel
        return RedisKeys.RKEY_ROOM_ID_FOR_NAME % channel_id

    @staticmethod
    def rooms_for_user(user_id: str) -> str:
        return RedisKeys.RKEY_ROOMS_FOR_USER % user_id

    @staticmethod
    def users_in_room(room_id: str) -> str:
        return RedisKeys.RKEY_USERS_IN_ROOM % room_id

    @staticmethod
    def admin_room_for_channel() -> str:
        return RedisKeys.RKEY_ROOMS_ADMINS

    @staticmethod
    def rooms(channel_id) -> str:
        return RedisKeys.RKEY_ROOMS % channel_id

    @staticmethod
    def room_name_for_id() -> str:
        return RedisKeys.RKEY_ROOM_NAME

    @staticmethod
    def online_bitmap() -> str:
        return RedisKeys.RKEY_ONLINE_BITMAP

    @staticmethod
    def online_set() -> str:
        return RedisKeys.RKEY_ONLINE_SET

    @staticmethod
    def channels() -> str:
        return RedisKeys.RKEY_CHANNELS

    @staticmethod
    def channel_exists() -> str:
        return RedisKeys.RKEY_CHANNEL_EXISTS

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
    def channel_acl(channel_id: str) -> dict:
        return RedisKeys.RKEY_CHANNEL_ACL % channel_id

    @staticmethod
    def room_acl(room_id: str) -> dict:
        return RedisKeys.RKEY_ROOM_ACL % room_id

    @staticmethod
    def channel_for_rooms() -> str:
        return RedisKeys.RKEY_CHANNEL_FOR_ROOMS

    @staticmethod
    def auth_key(user_id: str) -> str:
        return RedisKeys.RKEY_AUTH % user_id
