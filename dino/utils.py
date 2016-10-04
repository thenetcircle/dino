from uuid import uuid4 as uuid
from activitystreams import Activity
from redis import Redis

from dino import rkeys
from dino.env import env


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


def activity_for_user_joined(user_id: str, user_name: str, room_id: str, room_name: str, image_url: str) -> dict:
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


def activity_for_create_room(room_id: str, room_name: str) -> dict:
    return {
        'target': {
            'id': room_id,
            'displayName': room_name
        },
        'verb': 'create'
    }


def activity_for_history(activity: Activity, messages: list) -> dict:
    response = {
        'object': {
            'objectType': 'messages'
        },
        'verb': 'history',
        'target': {
            'id': activity.target.id,
            'displayName': get_room_name(env.redis, activity.target.id)
        }
    }

    response['object']['attachments'] = list()
    for msg_id, timestamp, user_name, msg in messages:
        response['object']['attachments'].append({
            'id': msg_id,
            'content': msg,
            'summary': user_name,
            'published': timestamp
        })

    return response


def activity_for_join(activity: Activity, acls: dict, messages: list, owners: dict, users: list) -> dict:
    response = {
        'object': {
            'objectType': 'room',
            'attachments': list()
        },
        'verb': 'join',
        'target': {
            'id': activity.target.id,
            'displayName': get_room_name(env.redis, activity.target.id)
        }
    }

    acl_activity = activity_for_get_acl(activity, acls)
    response['object']['attachments'].append({
        'objectType': 'acl',
        'attachments': acl_activity['object']['attachments']
    })

    history_activity = activity_for_history(activity, messages)
    response['object']['attachments'].append({
        'objectType': 'history',
        'attachments': history_activity['object']['attachments']
    })

    owners_activity = activity_for_owners(activity, owners)
    response['object']['attachments'].append({
        'objectType': 'owner',
        'attachments': owners_activity['object']['attachments']
    })

    users_in_room_activity = activity_for_users_in_room(activity, users)
    response['object']['attachments'].append({
        'objectType': 'user',
        'attachments': users_in_room_activity['object']['attachments']
    })

    return response


def activity_for_owners(activity: Activity, owners: dict) -> dict:
    response = {
        'object': {
            'objectType': 'owner'
        },
        'target': {
            'id': activity.target.id,
            'displayName': activity.target.display_name
        },
        'verb': 'list'
    }

    response['object']['attachments'] = list()
    for user_id, user_name in owners.items():
        response['object']['attachments'].append({
            'id': str(user_id, 'utf-8'),
            'content': str(user_name, 'utf-8')
        })

    return response


def activity_for_list_rooms(activity: Activity, rooms: list) -> dict:
    response = {
        'object': {
            'objectType': 'rooms'
        },
        'verb': 'list'
    }

    response['object']['attachments'] = list()
    for room_id, room_name in rooms:
        response['object']['attachments'].append({
            'id': room_id,
            'content': room_name
        })

    return response


def is_user_in_room(user_id, room_id):
    return env.redis.hexists(rkeys.users_in_room(room_id), user_id)


def activity_for_users_in_room(activity: Activity, users: list) -> dict:
    response = {
        'target': {
            'id': activity.target.id,
            'displayName': activity.target.display_name
        },
        'object': {
            'objectType': 'users'
        },
        'verb': 'list'
    }

    response['object']['attachments'] = list()
    for user_id, user_name in users:
        response['object']['attachments'].append({
            'id': user_id,
            'content': user_name
        })

    return response


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


def is_owner(room_id: str, user_id: str) -> bool:
    return env.redis.hexists(rkeys.room_owners(room_id), user_id)


def get_users_in_room(room_id: str) -> list:
    users_in_room = env.redis.hgetall(rkeys.users_in_room(room_id))
    users = list()
    for user_id, user_name in users_in_room.items():
        users.append((
            str(user_id.decode('utf-8')),
            str(user_name.decode('utf-8'))
        ))
    return users


def get_acls_for_room(room_id: str) -> dict:
    return env.redis.hgetall(rkeys.room_acl(room_id))


def get_owners_for_room(room_id: str) -> dict:
    return env.redis.hgetall(rkeys.room_owners(room_id))


def get_history_for_room(room_id: str, limit: int=10) -> list:
    messages = env.redis.lrange(rkeys.room_history(room_id), 0, 10)
    cleaned_messages = list()
    for message_entry in messages:
        message_entry = str(message_entry, 'utf-8')
        cleaned_messages.append(message_entry.split(',', 3))
    return cleaned_messages


def remove_user_from_room(r_server: Redis, user_id: str, user_name: str, room_id: str) -> None:
    env.leave_room(room_id)
    r_server.hdel(rkeys.users_in_room(room_id), user_id)
    r_server.srem(rkeys.rooms_for_user(user_id), room_id)


def get_room_name(r_server: Redis, room_id: str) -> str:
    room_name = r_server.get(rkeys.room_name_for_id(room_id))
    if room_name is None:
        room_name = str(uuid())
        env.logger.warn('WARN: room_name for room_id %s is None, generated new name: %s' % (room_id, room_name))
        r_server.set(rkeys.room_name_for_id(room_id), room_name)
    else:
        room_name = room_name.decode('utf-8')
    return room_name


def join_the_room(r_server: Redis, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
    r_server.sadd(rkeys.rooms_for_user(user_id), '%s:%s' % (room_id, room_name))
    r_server.hset(rkeys.users_in_room(room_id), user_id, user_name)
    r_server.hset(rkeys.rooms(), room_id, room_name)
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
