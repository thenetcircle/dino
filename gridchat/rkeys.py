__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

RKEY_ROOMS_FOR_USER = 'user:rooms:%s'
RKEY_ONLINE_USERS = 'users:online'
RKEY_USERS_IN_ROOM = 'room:%s'
RKEY_ROOMS = 'rooms'


def rooms_for_user(user_id):
    return RKEY_ROOMS_FOR_USER % user_id


def online_users():
    return RKEY_ONLINE_USERS


def users_in_room(room_id):
    return RKEY_USERS_IN_ROOM % room_id


def rooms():
    return RKEY_ROOMS
