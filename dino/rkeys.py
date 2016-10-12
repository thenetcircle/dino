__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

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

REDIS_STATUS_AVAILABLE = '1'
# REDIS_STATUS_CHAT = '2'
REDIS_STATUS_INVISIBLE = '3'
REDIS_STATUS_UNAVAILABLE = '4'
# REDIS_STATUS_UNKNOWN = '5'


def rooms_for_user(user_id: str) -> str:
    return RKEY_ROOMS_FOR_USER % user_id


def users_in_room(room_id: str) -> str:
    return RKEY_USERS_IN_ROOM % room_id


def rooms() -> str:
    return RKEY_ROOMS


def room_name_for_id(room_id: str) -> str:
    return RKEY_ROOM_NAME % room_id


def online_bitmap() -> str:
    return RKEY_ONLINE_BITMAP


def online_set() -> str:
    return RKEY_ONLINE_SET


def users_multi_cast() -> str:
    return RKEY_MULTI_CAST


def user_status(user_id: str) -> str:
    return RKEY_USER_STATUS % user_id


def room_history(room_id: str) -> str:
    return RKEY_ROOM_HISTORY % room_id


def room_acl(room_id: str) -> dict:
    return RKEY_ROOM_ACL % room_id


def room_owners(room_id: str) -> str:
    return RKEY_ROOM_OWNERS % room_id


def auth_key(user_id: str) -> str:
    return RKEY_AUTH % user_id