from flask_socketio import emit, join_room, leave_room
from uuid import uuid4 as uuid

import rkeys


def activity_for_leave(user_id, user_name, room_id, room_name):
    return {
        'actor': {
            'id': user_id,
            'summary': user_name
        },
        'target': {
            'id': room_id,
            'display_name': room_name
        },
        'verb': 'leave'
    }


def activity_for_join(user_id, user_name, room_id, room_name):
    return {
        'actor': {
            'id': user_id,
            'summary': user_name
        },
        'target': {
            'id': room_id,
            'display_name': room_name,
            'object_type': 'group'
        },
        'verb': 'join'
    }


def activity_for_disconnect(user_id, user_name):
    return {
        'actor': {
            'id': user_id,
            'summary': user_name
        },
        'verb': 'disconnect'
    }


def activity_for_connect(user_id, user_name):
    return {
        'actor': {
            'id': user_id,
            'summary': user_name
        },
        'verb': 'sconnect'
    }


def remove_user_from_room(redis, user_id, user_name, room_id):
    leave_room(room_id)
    redis.srem(rkeys.users_in_room(room_id), '%s:%s' % (user_id, user_name))
    redis.srem(rkeys.rooms_for_user(user_id), room_id)


def get_room_name(redis, room_id):
    room_name = redis.get(rkeys.room_name_for_id(room_id))
    if room_name is None:
        room_name = str(uuid())
        print('room_name for room_id %s is None, generated new name: %s' % (room_id, room_name))
        redis.set(rkeys.room_name_for_id(room_id), room_name)
    else:
        room_name = room_name.decode('utf-8')
        print('room_name for room_id %s is %s' % (room_id, room_name))
    return room_name


def join_the_room(redis, user_id, user_name, room_id, room_name):
    redis.sadd(rkeys.rooms_for_user(user_id), '%s:%s' % (room_id, room_name))
    redis.sadd(rkeys.users_in_room(room_id), '%s:%s' % (user_id, user_name))
    redis.sadd(rkeys.rooms(), '%s:%s' % (room_id, room_name))
    join_room(room_id)
    print('user %s is joining room_name %s, room_id %s' % (user_id, room_name, room_id))


def set_user_offline(redis, user_id):
    redis.setbit(rkeys.online_bitmap(), int(user_id), 0)
    redis.srem(rkeys.online_set(), int(user_id))
    redis.srem(rkeys.users_multi_cast(), user_id)
    redis.set(rkeys.user_status(user_id), rkeys.REDIS_STATUS_UNAVAILABLE)


def set_user_online(redis, user_id):
    redis.setbit(rkeys.online_bitmap(), int(user_id), 1)
    redis.sadd(rkeys.online_set(), int(user_id))
    redis.sadd(rkeys.users_multi_cast(), user_id)
    redis.set(rkeys.user_status(user_id), rkeys.REDIS_STATUS_AVAILABLE)


def set_user_invisible(redis, user_id):
    redis.setbit(rkeys.online_bitmap(), int(user_id), 0)
    redis.srem(rkeys.online_set(), int(user_id))
    redis.sadd(rkeys.users_multi_cast(), user_id)
    redis.set(rkeys.user_status(user_id), rkeys.REDIS_STATUS_INVISIBLE)