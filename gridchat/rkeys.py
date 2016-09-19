__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

RKEY_ROOMS_FOR_USER = 'user:rooms:%s'
RKEY_USERS_IN_ROOM = 'room:%s'
RKEY_ROOMS = 'rooms'
RKEY_ONLINE_BITMAP = 'users:online:bitmap'
RKEY_ONLINE_SET = 'users:online:set'
RKEY_MULTI_CAST = 'users:multicat'
RKEY_USER_STATUS = 'user:status:%s'

REDIS_STATUS_AVAILABLE = '1'
# REDIS_STATUS_CHAT = '2'
REDIS_STATUS_INVISIBLE = '3'
REDIS_STATUS_UNAVAILABLE = '4'
# REDIS_STATUS_UNKNOWN = '5'


def rooms_for_user(user_id):
    return RKEY_ROOMS_FOR_USER % user_id


def users_in_room(room_id):
    return RKEY_USERS_IN_ROOM % room_id


def rooms():
    return RKEY_ROOMS


def online_bitmap():
    return RKEY_ONLINE_BITMAP


def online_set():
    return RKEY_ONLINE_SET


def users_multi_cast():
    return RKEY_MULTI_CAST


def user_status(user_id):
    return RKEY_USER_STATUS % str(user_id)
