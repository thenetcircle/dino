from uuid import uuid4 as uuid
from activitystreams import Activity
from redis import Redis

from gridchat import rkeys
from gridchat.env import env


def activity_for_leave(user_id: str, user_name: str, room_id: str, room_name: str) -> dict:
    return {
        'actor': {
            'id': user_id,
            'summary': user_name
        },
        'target': {
            'id': room_id,
            'displayName': room_name
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
            'displayName': room_name,
            'objectType': 'group'
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
            'displayName': activity.target.display_name
        },
        'object': {
            'objectType': 'acl'
        },
        'verb': 'get'
    }

    response['object']['attachments'] = list()
    for acl_type, acl_value in acl_values.items():
        response['object']['attachments'].append({
            'objectType': str(acl_type, 'utf-8'),
            'content': str(acl_value, 'utf-8')
        })

    return response


def remove_user_from_room(r_server: Redis, user_id: str, user_name: str, room_id: str) -> None:
    env.leave_room(room_id)
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
    env.join_room(room_id)
    env.logger.debug('user %s (%s) is joining %s (%s)' % (user_id, user_name, room_id, room_name))


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
