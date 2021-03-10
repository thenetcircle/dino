#!/usr/bin/env python
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


class ConfigService(object):
    def __init__(self, env):
        self.env = env
        self.counter = 0
        self._config = dict()
        self.reload()

    @property
    def config(self):
        self.counter += 1
        if self.counter > 1000:
            self.counter = 0
            self.reload()
        return self._config

    def is_spam_classifier_enabled(self):
        return self.config.get('spam_enabled', False)

    def get_spam_min_length(self):
        return self.config.get('spam_min_length', 10)

    def get_spam_threshold(self):
        return self.config.get('spam_threshold', 80)

    def get_spam_max_length(self):
        return self.config.get('spam_max_length', 250)

    def should_delete_spam(self):
        return self.config.get('spam_should_delete', False)

    def should_save_spam(self):
        return self.config.get('spam_should_save', False)

    def ignore_emoji(self):
        return self.config.get('spam_ignore_emoji', False)

    def reload(self):
        self._config = self.env.db.get_service_config()

    def get_config(self):
        return self.config.copy()


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
    is_streaming = 'is_streaming'
    spoken_language = 'spoken_language'

    avatar = 'avatar'
    app_avatar = 'app_avatar'
    app_avatar_safe = 'app_avatar_safe'
    enabled_safe = 'enabled_safe'

    user_agent = 'user_agent'
    user_agent_browser = 'user_agent_browser'
    user_agent_version = 'user_agent_version'
    user_agent_platform = 'user_agent_platform'
    user_agent_language = 'user_agent_language'

    user_agent_keys = {
        user_agent,
        user_agent_browser,
        user_agent_version,
        user_agent_platform,
        user_agent_language
    }

    temporary_keys = {
        is_streaming
    }

    requires_session_keys = {
        user_id,
        user_name,
        token
    }


class ErrorCodes(object):
    OK = 200
    UNKNOWN_ERROR = 250

    MISSING_ACTOR_ID = 500
    MISSING_OBJECT_ID = 501
    MISSING_TARGET_ID = 502
    MISSING_OBJECT_URL = 503
    MISSING_TARGET_DISPLAY_NAME = 504
    MISSING_ACTOR_URL = 505
    MISSING_OBJECT_CONTENT = 506
    MISSING_OBJECT = 507
    MISSING_OBJECT_ATTACHMENTS = 508
    MISSING_ATTACHMENT_TYPE = 509
    MISSING_ATTACHMENT_CONTENT = 510
    MISSING_VERB = 511

    INVALID_TARGET_TYPE = 600
    INVALID_ACL_TYPE = 601
    INVALID_ACL_ACTION = 602
    INVALID_ACL_VALUE = 603
    INVALID_STATUS = 604
    INVALID_OBJECT_TYPE = 605
    INVALID_BAN_DURATION = 606
    INVALID_VERB = 607

    EMPTY_MESSAGE = 700
    NOT_BASE64 = 701
    USER_NOT_IN_ROOM = 702
    USER_IS_BANNED = 703
    ROOM_ALREADY_EXISTS = 704
    NOT_ALLOWED = 705
    VALIDATION_ERROR = 706
    ROOM_FULL = 707
    NOT_ONLINE = 708
    TOO_MANY_PRIVATE_ROOMS = 709
    ROOM_NAME_TOO_LONG = 710
    ROOM_NAME_TOO_SHORT = 711
    INVALID_TOKEN = 712
    INVALID_LOGIN = 713
    MSG_TOO_LONG = 714
    MULTIPLE_ROOMS_WITH_NAME = 715
    TOO_MANY_ATTACHMENTS = 716
    NOT_ENABLED = 717
    ROOM_NAME_RESTRICTED = 718

    NOT_ALLOWED_TO_WHISPER_CHANNEL = 720
    NOT_ALLOWED_TO_WHISPER_NOT_A_CONTACT = 721
    NOT_ALLOWED_TO_WHISPER_TURNED_OFF = 722
    NOT_ALLOWED_TO_WHISPER_SELF = 723
    NOT_ALLOWED_TO_WHISPER_GENERIC_ERROR = 724
    REMOTE_ERROR = 725

    NO_SUCH_USER = 800
    NO_SUCH_CHANNEL = 801
    NO_SUCH_ROOM = 802
    NO_ADMIN_ROOM_FOUND = 803
    NO_USER_IN_SESSION = 804
    NO_ADMIN_ONLINE = 805


class ApiTargets(object):
    ROOM = 'room'
    CHANNEL = 'channel'


class ApiActions(object):
    all_api_actions = list()

    JOIN = 'join'
    AUTOJOIN = 'autojoin'
    CROSSROOM = 'crossroom'
    MESSAGE = 'message'
    KICK = 'kick'
    BAN = 'ban'
    LIST = 'list'
    HISTORY = 'history'
    SETACL = 'setacl'
    CREATE = 'create'
    WHISPER = 'whisper'

ApiActions.all_api_actions = \
    [getattr(ApiActions, d) for d in ApiActions.__dict__ if not d.startswith('_') and not d[0].islower()]


class RoleKeys(object):
    all_roles = list()

    OWNER = 'owner'
    MODERATOR = 'moderator'
    ADMIN = 'admin'
    SUPER_USER = 'superuser'
    GLOBAL_MODERATOR = 'globalmod'

RoleKeys.all_roles = [getattr(RoleKeys, d) for d in RoleKeys.__dict__ if not d.startswith('_') and not d[0].islower()]


class UserKeys(object):
    STATUS_AVAILABLE = '1'
    STATUS_CHAT = '2'
    STATUS_INVISIBLE = '3'
    STATUS_UNAVAILABLE = '4'
    STATUS_UNKNOWN = '5'


class AckStatus(object):
    NOT_ACKED = 0
    RECEIVED = 1
    READ = 2


class ConfigKeys(object):
    COUNT_CUMULATIVE_JOINS = 'count_cumulative_join'
    INVISIBLE_UNRESTRICTED = 'invisible_unrestricted'
    REQ_LOG_LOC = 'request_log_location'
    LOG_LEVEL = 'log_level'
    LOG_FORMAT = 'log_format'
    RESPONSE_FORMAT = 'response_format'
    AUTOJOIN_ENABLED = 'autojoin'
    LOGGING = 'logging'
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
    COORDINATOR = 'coordinator'
    STRATEGY = 'strategy'
    REPLICATION = 'replication'
    DSN = 'dsn'
    DATABASE = 'database'
    POOL_SIZE = 'pool_size'
    DB = 'db'
    PORT = 'port'
    VHOST = 'vhost'
    USER = 'user'
    PASSWORD = 'password'
    HISTORY = 'history'
    LIMIT = 'limit'
    PREFIX = 'prefix'
    INCLUDE_HOST_NAME = 'include_hostname'
    VALIDATION = 'validation'
    MAX_MSG_LENGTH = 'max_length'
    MAX_USERS_LOW = 'max_users_low'
    MAX_USERS_HIGH = 'max_users_high'
    MAX_USERS_EXCEPTION = 'exception'
    MAX_ROOMS = 'max_rooms'
    WEB = 'web'
    ROOT_URL = 'root_url'
    MIN_ROOM_NAME_LENGTH = 'min_length'
    MAX_ROOM_NAME_LENGTH = 'max_length'
    DISCONNECT_ON_FAILED_LOGIN = 'disconnect_on_failed_login'
    SENDER_CAN_DELETE = 'sender_can_delete'
    DELIVERY_GUARANTEE = 'delivery_guarantee'
    WARMUP_DAYS = 'warmup_days'

    ENRICH = 'enrich'
    TITLE = 'title'
    VERB = 'verb'
    SPAM_CLASSIFIER = 'spam_classifier'
    HEARTBEAT = 'heartbeat'
    TIMEOUT = 'timeout'
    INTERVAL = 'interval'

    INSECURE = 'insecure'
    OAUTH_ENABLED = 'oauth_enabled'
    OAUTH_BASE = 'base'
    OAUTH_PATH = 'path'
    SERVICE_ID = 'service_id'
    SERVICE_SECRET = 'service_secret'
    AUTH_URL = 'authorized_url'
    TOKEN_URL = 'token_url'
    CALLBACK_URL = 'callback_url'
    UNAUTH_URL = 'unauthorized_url'

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
    DEFAULT_CHANNEL_NAME = "_DEFAULT"

    HISTORY_TYPE_UNREAD = 'unread'
    HISTORY_TYPE_TOP = 'top'
    USE_FLOATING_MENU = 'use_floating_menu'
    CORS_ORIGINS = 'cors_origins'

    ENDPOINT = 'endpoint'
    PATH_CAN_WHISPER = 'path_can_whisper'
    REMOTE = 'remote'
    PRIVATE_KEY = 'private_key'
    VALIDATE_WHISPERS = 'validate_whispers'


class RedisKeys(object):
    RKEY_ALL_ROOMS = 'rooms:all'
    RKEY_USERS_IN_ROOM_FOR_ROLE = 'room:role:%s:%s'  # room:role:room_id:role_type
    RKEY_USERS_IN_CHANNEL_FOR_ROLE = 'channel:role:%s:%s'  # channel:role:room_id:role_type
    RKEY_ACLS_IN_CHANNEL = 'channel:acls:%s'  # channel:acls:channel_id
    RKEY_ACLS_IN_ROOM = 'room:acls:%s'  # room:acls:room_id
    RKEY_ACLS_IN_ROOM_FOR_ACTION = 'room:acls:%s:%s'  # room:acls:room_id:action_name
    RKEY_ACLS_IN_CHANNEL_FOR_ACTION = 'channel:acls:%s:%s'  # room:acls:channel_id:action_name
    RKEY_ROOMS_FOR_CHANNEL_WITH_INFO = 'channel:rooms:info:%s'  # channel:rooms:info:channel_id
    RKEY_ROOMS_FOR_CHANNEL_WITHOUT_INFO = 'channel:rooms:noinfo:%s'  # channel:rooms:noinfo:channel_id
    RKEY_TYPE_OF_ROOMS_IN_CHANNEL = 'channel:roomtype:%s'  # channel:roomtype:channel_id
    RKEY_ROOMS_FOR_USER = 'user:rooms:%s'  # user:rooms:user_id
    RKEY_USERS_IN_ROOM = 'room:%s'  # room:room_id
    RKEY_USERS_IN_ROOM_VISIBLE = 'room:visible:%s'  # room:visible:room_id
    RKEY_USERS_IN_ROOM_WITH_INVISIBLE = 'room:with:invisible:%s'  # room:with:invisible:room_id
    RKEY_ROOMS = 'rooms:%s'  # room:channel_id
    RKEY_ROOMS_PERMANENT = 'rooms:permanent'
    RKEY_ONLINE_BITMAP = 'users:online:bitmap'
    RKEY_ONLINE_SET = 'users:online:set'
    RKEY_MULTI_CAST = 'users:multicast'
    RKEY_USER_STATUS = 'user:status:%s'  # user:status:user_id
    RKEY_USER_LAST_ONLINE = 'user:online:last:{}'  # user:online:last:user_id
    RKEY_ROOM_NAME = 'room:names'
    RKEY_ROOM_ACL = 'room:acl:%s'  # room:acl:room_id
    RKEY_CHANNEL_ACL = 'channel:acl:%s'  # channel:acl:channel_id
    RKEY_ROOM_HISTORY = 'room:history:%s'  # room:history:room_id
    RKEY_AUTH = 'user:auth:%s'  # user:auth:user_id
    RKEY_CHANNELS = 'channels'
    RKEY_CHANNELS_SORT = 'channels:sort'
    RKEY_CHANNEL_EXISTS = 'channel:exists'
    RKEY_ROOM_ID_FOR_NAME = 'room:id:%s'  # room:id:channel_id
    RKEY_CHANNEL_ROLES = 'channel:roles:%s'  # channel:roles:channel_id
    RKEY_GLOBAL_ROLES = 'global:roles'
    RKEY_ROOM_ROLES = 'room:roles:%s'  # channel:roles:channel_id
    RKEY_CHANNEL_FOR_ROOMS = 'room:channel'
    RKEY_LAST_READ = 'room:read:%s'  # room:read:room_id
    RKEY_USER_NAMES = 'user:names'
    RKEY_USER_IDS = 'user:ids'
    RKEY_ROOM_ADMIN = 'room:admin'
    RKEY_ACL_VALIDATION = 'acl:validation:%s'  # acl:validation:acl_type (e.g. acl:validation:gender)
    RKEY_USER_ROLES = 'users:roles'
    RKEY_BLACK_LIST = 'words:blacklist'
    RKEY_NON_EPHEMERAL_ROOMS = 'rooms:nonephemeral'
    RKEY_DEFAULT_ROOMS = 'rooms:default'
    RKEY_ACKS_USER = 'acks:user:%s'
    RKEY_ACKS_ROOM = 'acks:room:%s'
    RKEY_USERS_IN_ROOM_COUNT = 'users:online:inrooms'

    RKEY_SID_TO_USER_ID = 'user:sid:map'
    RKEY_USER_ID_TO_SID = 'sid:user:map'
    RKEY_BANNED_USERS_GLOBAL = 'users:banned:global'
    RKEY_BANNED_USERS_ROOM = 'users:banned:room:%s'  # users:banned:room:room_id
    RKEY_BANNED_USERS_CHANNEL = 'users:banned:channel:%s'  # users:banned:channel:channel_id

    RKEY_HEARTBEAT = 'heartbeat:{}'
    RKEY_AVATARS = 'user:avatars'
    RKEY_SESSION_COUNT = 'session:count'
    RKEY_USER_NAMES_SET = 'user:names:set'

    RKEY_CAN_WHISPER = 'whisper:{}'  # whisper:user_id
    RKEY_ROOMS_WITH_ACL_ACTION = 'rooms:acl:{}'  # rooms:acl:<acl_action> => "room_id_1,room_id_2,..."
    RKEY_ACLS_FOR_ROOMS_HAVING_ACTION = 'rooms:acl:{}:{}'  # rooms:acl:<room_id>:<acl_action> => {acl_type: acl_value}
    RKEY_JOIN_COUNTS = 'rooms:joins:{}'  # rooms:joins:room_id
    RKEY_DEFAULT_CHANNEL_ID = 'channel:default:id'

    @staticmethod
    def default_channel_id() -> str:
        return RedisKeys.RKEY_DEFAULT_CHANNEL_ID

    @staticmethod
    def join_counts(room_id) -> str:
        return RedisKeys.RKEY_JOIN_COUNTS.format(room_id)

    @staticmethod
    def all_rooms() -> str:
        return RedisKeys.RKEY_ALL_ROOMS

    @staticmethod
    def user_names_set() -> str:
        return RedisKeys.RKEY_USER_NAMES_SET

    @staticmethod
    def can_whisper_to(user_id: str) -> str:
        return RedisKeys.RKEY_CAN_WHISPER.format(user_id)

    @staticmethod
    def session_count() -> str:
        return RedisKeys.RKEY_SESSION_COUNT

    @staticmethod
    def avatars() -> str:
        return RedisKeys.RKEY_AVATARS

    @staticmethod
    def all_permanent_rooms():
        return RedisKeys.RKEY_ROOMS_PERMANENT

    @staticmethod
    def room_acls_for_action(room_id: str, action: str) -> str:
        return RedisKeys.RKEY_ACLS_FOR_ROOMS_HAVING_ACTION.format(room_id, action)

    @staticmethod
    def rooms_with_action(action: str) -> str:
        return RedisKeys.RKEY_ROOMS_WITH_ACL_ACTION.format(action)

    @staticmethod
    def heartbeat_user(user_id: str) -> str:
        return RedisKeys.RKEY_HEARTBEAT.format(user_id)

    @staticmethod
    def ack_for_user(user_id: str) -> str:
        return RedisKeys.RKEY_ACKS_USER % user_id

    @staticmethod
    def ack_for_room(user_id: str) -> str:
        return RedisKeys.RKEY_ACKS_ROOM % user_id

    @staticmethod
    def users_in_room_incl_invisible(room_id: str) -> str:
        return RedisKeys.RKEY_USERS_IN_ROOM_WITH_INVISIBLE % room_id

    @staticmethod
    def users_in_room_only_visible(room_id: str) -> str:
        return RedisKeys.RKEY_USERS_IN_ROOM_VISIBLE % room_id

    @staticmethod
    def channels_with_sort():
        return RedisKeys.RKEY_CHANNELS_SORT

    @staticmethod
    def users_in_channel_for_role(channel_id: str, role: str) -> str:
        return RedisKeys.RKEY_USERS_IN_CHANNEL_FOR_ROLE % (channel_id, role)

    @staticmethod
    def users_in_room_for_role(room_id: str, role: str) -> str:
        return RedisKeys.RKEY_USERS_IN_ROOM_FOR_ROLE % (room_id, role)

    @staticmethod
    def acls_in_room_for_action(room_id: str, action: str) -> str:
        return RedisKeys.RKEY_ACLS_IN_ROOM_FOR_ACTION % (room_id, action)

    @staticmethod
    def acls_in_channel_for_action(channel_id: str, action: str) -> str:
        return RedisKeys.RKEY_ACLS_IN_CHANNEL_FOR_ACTION % (channel_id, action)

    @staticmethod
    def acls_in_room(room_id: str) -> str:
        return RedisKeys.RKEY_ACLS_IN_ROOM % (room_id)

    @staticmethod
    def acls_in_channel(channel_id: str) -> str:
        return RedisKeys.RKEY_ACLS_IN_CHANNEL % (channel_id)

    @staticmethod
    def rooms_for_channel_with_info(channel_id: str) -> str:
        return RedisKeys.RKEY_ROOMS_FOR_CHANNEL_WITH_INFO % channel_id

    @staticmethod
    def rooms_for_channel_without_info(channel_id: str) -> str:
        return RedisKeys.RKEY_ROOMS_FOR_CHANNEL_WITHOUT_INFO % channel_id

    @staticmethod
    def default_rooms() -> str:
        return RedisKeys.RKEY_DEFAULT_ROOMS

    @staticmethod
    def room_types_in_channel(channel_id: str) -> str:
        return RedisKeys.RKEY_TYPE_OF_ROOMS_IN_CHANNEL % channel_id

    @staticmethod
    def non_ephemeral_rooms() -> str:
        return RedisKeys.RKEY_NON_EPHEMERAL_ROOMS

    @staticmethod
    def black_list() -> str:
        return RedisKeys.RKEY_BLACK_LIST

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
    def user_ids() -> str:
        return RedisKeys.RKEY_USER_IDS

    @staticmethod
    def sid_for_user_id() -> str:
        return RedisKeys.RKEY_SID_TO_USER_ID

    @staticmethod
    def user_id_for_sid() -> str:
        return RedisKeys.RKEY_USER_ID_TO_SID

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
    def room_id_for_name(room_name: str) -> str:
        # separate room name/id mapping per channel
        return RedisKeys.RKEY_ROOM_ID_FOR_NAME % room_name

    @staticmethod
    def rooms_for_user(user_id: str) -> str:
        return RedisKeys.RKEY_ROOMS_FOR_USER % user_id

    @staticmethod
    def users_in_room(room_id: str) -> str:
        return RedisKeys.RKEY_USERS_IN_ROOM % room_id

    @staticmethod
    def admin_room() -> str:
        return RedisKeys.RKEY_ROOM_ADMIN

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
    def user_last_online(user_id: str) -> str:
        return RedisKeys.RKEY_USER_LAST_ONLINE.format(user_id)

    @staticmethod
    def room_history(room_id: str) -> str:
        return RedisKeys.RKEY_ROOM_HISTORY % room_id

    @staticmethod
    def channel_acl(channel_id: str) -> str:
        return RedisKeys.RKEY_CHANNEL_ACL % channel_id

    @staticmethod
    def room_acl(room_id: str) -> str:
        return RedisKeys.RKEY_ROOM_ACL % room_id

    @staticmethod
    def channel_for_rooms() -> str:
        return RedisKeys.RKEY_CHANNEL_FOR_ROOMS

    @staticmethod
    def auth_key(user_id: str) -> str:
        return RedisKeys.RKEY_AUTH % user_id
