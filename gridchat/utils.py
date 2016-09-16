from flask_socketio import emit, join_room, leave_room
from uuid import uuid4 as uuid


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
            'display_name': user_name
        },
        'verb': 'disconnect'
    }


def remove_user_from_room(redis, user_id, room_id):
    leave_room(room_id)
    redis.srem('room:' + room_id, user_id)
    redis.srem('user:rooms:' + user_id, room_id)


def get_room_name(redis, room_id):
    room_id = redis.get('room:name:%s' % room_id)
    if room_id is None:
        room_id = str(uuid())
        redis.set('room:name:%s' % room_id, room_id)
    else:
        room_id = room_id.decode('utf-8')
    return room_id


def join_the_room(redis, user_id, room_id, room_name):
    redis.sadd('user:rooms:%s' % user_id, '%s:%s' % (room_id, room_name))
    redis.sadd('room:%s' % room_id, user_id)
    redis.sadd('rooms', room_id)
    join_room(room_id)
