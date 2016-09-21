from flask_socketio import emit, join_room, leave_room
from flask import session
from uuid import uuid4 as uuid
from activitystreams import Activity
from redis import Redis

import rkeys


USER_KEYS = [
    'gender', 'membership', 'age', 'country', 'city', 'image'
    'user_id', 'user_name', 'token', 'has_webcam', 'fake_checked'
]


def activity_for_leave(user_id: str, user_name: str, room_id: str, room_name: str) -> dict:
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


def activity_for_join(user_id: str, user_name: str, room_id: str, room_name: str, image_url: str) -> dict:
    return {
        'actor': {
            'id': user_id,
            'summary': user_name,
            'image': {
                'url': image_url
            }
        },
        'target': {
            'id': room_id,
            'display_name': room_name,
            'object_type': 'group'
        },
        'verb': 'join'
    }


def activity_for_disconnect(user_id: str, user_name: str) -> dict:
    return {
        'actor': {
            'id': user_id,
            'summary': user_name
        },
        'verb': 'disconnect'
    }


def activity_for_connect(user_id: str, user_name: str) -> dict:
    return {
        'actor': {
            'id': user_id,
            'summary': user_name
        },
        'verb': 'sconnect'
    }


def remove_user_from_room(r_server: Redis, user_id: str, user_name: str, room_id: str) -> None:
    leave_room(room_id)
    r_server.srem(rkeys.users_in_room(room_id), '%s:%s' % (user_id, user_name))
    r_server.srem(rkeys.rooms_for_user(user_id), room_id)


def get_room_name(r_server: Redis, room_id: str) -> None:
    room_name = r_server.get(rkeys.room_name_for_id(room_id))
    if room_name is None:
        room_name = str(uuid())
        print('room_name for room_id %s is None, generated new name: %s' % (room_id, room_name))
        r_server.set(rkeys.room_name_for_id(room_id), room_name)
    else:
        room_name = room_name.decode('utf-8')
        print('room_name for room_id %s is %s' % (room_id, room_name))
    return room_name


def join_the_room(r_server: Redis, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
    r_server.sadd(rkeys.rooms_for_user(user_id), '%s:%s' % (room_id, room_name))
    r_server.sadd(rkeys.users_in_room(room_id), '%s:%s' % (user_id, user_name))
    r_server.sadd(rkeys.rooms(), '%s:%s' % (room_id, room_name))
    join_room(room_id)
    print('user %s is joining room_name %s, room_id %s' % (user_id, room_name, room_id))


def set_user_offline(r_server: Redis, user_id: str) -> None:
    r_server.setbit(rkeys.online_bitmap(), int(user_id), 0)
    r_server.srem(rkeys.online_set(), int(user_id))
    r_server.srem(rkeys.users_multi_cast(), user_id)
    r_server.set(rkeys.user_status(user_id), rkeys.REDIS_STATUS_UNAVAILABLE)


def set_user_online(r_server: Redis, user_id: str):
    r_server.setbit(rkeys.online_bitmap(), int(user_id), 1)
    r_server.sadd(rkeys.online_set(), int(user_id))
    r_server.sadd(rkeys.users_multi_cast(), user_id)
    r_server.set(rkeys.user_status(user_id), rkeys.REDIS_STATUS_AVAILABLE)


def set_user_invisible(r_server: Redis, user_id: str):
    r_server.setbit(rkeys.online_bitmap(), int(user_id), 0)
    r_server.srem(rkeys.online_set(), int(user_id))
    r_server.sadd(rkeys.users_multi_cast(), user_id)
    r_server.set(rkeys.user_status(user_id), rkeys.REDIS_STATUS_INVISIBLE)


def validate() -> (bool, str):
    """
    checks whether required data was received and that it validates with community (not tampered with)

    :return: tuple(Boolean, String): (is_valid, error_message)
    """
    is_valid, error_msg = validate_session()
    if not is_valid:
        return False, error_msg

    return validate_user_data_with_community()


def validate_user_data_with_community() -> (bool, str):
    """
    todo: ask remote community if the user data is valid (could have been manually changed in js)

    :return: tuple(Boolean, String): (is_valid, error_message)
    """
    return True, None


def validate_session() -> (bool, str):
    """
    validate that all required parameters were send from the client side

    :return: tuple(Boolean, String): (is_valid, error_message)
    """

    for key in required:
        if key not in session:
            return False, '"%s" is a required parameter' % key
        val = session[key]
        if val is None or val == '':
            return False, '"%s" is a required parameter' % key
    return True, None


def validate_request(activity: Activity) -> (bool, str):
    if activity.actor.id != session['user_id']:
        return False, "user_id in session (%s) doesn't match user_id in request (%s)" % \
               (activity.actor.id, session['user_id'])
    return True, None
