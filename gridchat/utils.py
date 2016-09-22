from flask_socketio import emit, join_room, leave_room
from flask import session
from uuid import uuid4 as uuid
from activitystreams import Activity
from redis import Redis
import re

from gridchat import rkeys


class Validator:
    @staticmethod
    def is_digit(val: str):
        if val is None or not isinstance(val, str):
            return False
        if val[0] in ('-', '+'):
            return val[1:].isdigit()
        return val.isdigit()

    @staticmethod
    def _age(val: str):
        start, end = '-1', '-1'

        if val.endswith(':'):
            start = val[:-1]
        elif val.startswith(':'):
            end = val[1:]
        elif len(val.split(':')) == 2:
            start, end = val.split(':')
        else:
            return False

        if not Validator.is_digit(start):
            return False
        if not Validator.is_digit(end):
            return False

        return True

    @staticmethod
    def _true_false_all(val: str):
        return val in ['y', 'n', 'a']

    @staticmethod
    def _is_string(val: str):
        return val is not None and isinstance(val, str)

    @staticmethod
    def _chars_in_list(val: str, char_list: list):
        return len([x for x in val.split(',') if x in char_list]) == len(val.split(','))

    @staticmethod
    def _match(val: str, regex: str):
        return re.match(regex, val) is not None

    USER_KEYS = {
        'gender':
            lambda v: Validator._chars_in_list(v, ['m', 'f', 'ts']),

        'membership':
            lambda v: Validator._chars_in_list(v, ['0', '1', '2', '3', '4']),

        'age':
            lambda v: Validator._age(v),

        # 2 character country codes, no spaces
        'country':
            lambda v: Validator._match(v, '^(\w{2},)*(\w{2})+$'),

        # city names can have spaces and dashes in them
        'city':
            lambda v: Validator._match(v, '^([\w -]+,)*([\w -]+)+$'),

        'image':
            lambda v: Validator._true_false_all(v),

        'user_id':
            lambda v: Validator.is_digit(v),

        'user_name':
            lambda v: Validator._is_string(v),

        'token':
            lambda v: Validator._is_string(v),

        'has_webcam':
            lambda v: Validator._true_false_all(v),

        'fake_checked':
            lambda v: Validator._true_false_all(v),
    }


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
        'verb': 'connect'
    }


def activity_for_get_acl(activity: Activity, acl_values: dict) -> dict:
    response = {
        'target': {
            'id': activity.target.id,
            'display_name': activity.target.display_name
        },
        'object': {
            'object_type': 'acl'
        },
        'verb': 'get'
    }

    response['object']['attachments'] = list()
    for acl_type, acl_value in acl_values.items():
        response['object']['attachments'].append({
            'object_type': acl_type,
            'content': acl_value
        })

    return response


def remove_user_from_room(r_server: Redis, user_id: str, user_name: str, room_id: str) -> None:
    leave_room(room_id)
    r_server.srem(rkeys.users_in_room(room_id), '%s:%s' % (user_id, user_name))
    r_server.srem(rkeys.rooms_for_user(user_id), room_id)


def get_room_name(r_server: Redis, room_id: str) -> str:
    room_name = r_server.get(rkeys.room_name_for_id(room_id))
    if room_name is None:
        room_name = str(uuid())
        print('WARN: room_name for room_id %s is None, generated new name: %s' % (room_id, room_name))
        r_server.set(rkeys.room_name_for_id(room_id), room_name)
    else:
        room_name = room_name.decode('utf-8')
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
    for key in Validator.USER_KEYS.keys():
        if key not in session:
            return False, '"%s" is a required parameter' % key
        val = session[key]
        if val is None or val == '':
            return False, '"%s" is a required parameter' % key
    return True, None


def validate_request(activity: Activity) -> (bool, str):
    if not hasattr(activity, 'actor'):
        return False, 'no actor on activity'

    if not hasattr(activity.actor, 'id'):
        return False, 'no ID on actor'

    if activity.actor.id != session['user_id']:
        return False, "user_id in session (%s) doesn't match user_id in request (%s)" % \
               (activity.actor.id, session['user_id'])
    return True, None


def is_acl_valid(acl_type, acl_value):
    validator = Validator.USER_KEYS.get(acl_type, None)
    if validator is None:
        return False
    if not callable(validator):
        return False
    return validator(acl_value)
