from activitystreams import Activity

from dino import environ


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
            'displayName': environ.env.storage.get_room_name(activity.target.id)
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
            'displayName': environ.env.storage.get_room_name(activity.target.id)
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
            'id': user_id,
            'content': user_name
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
    return environ.env.storage.room_contains(room_id, user_id)


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
            'objectType': acl_type,
            'content': acl_value
        })

    return response


def is_owner(room_id: str, user_id: str) -> bool:
    return environ.env.storage.room_owners_contain(room_id, user_id)


def get_users_in_room(room_id: str) -> list:
    return environ.env.storage.users_in_room(room_id)


def get_acls_for_room(room_id: str) -> dict:
    return environ.env.storage.get_acls(room_id)


def get_owners_for_room(room_id: str) -> dict:
    return environ.env.storage.get_owners(room_id)


def get_history_for_room(room_id: str, limit: int = 10) -> list:
    return environ.env.storage.get_history(room_id, limit)


def remove_user_from_room(user_id: str, user_name: str, room_id: str) -> None:
    environ.env.leave_room(room_id)
    environ.env.storage.leave_room(user_id, room_id)


def join_the_room(user_id: str, user_name: str, room_id: str, room_name: str) -> None:
    environ.env.storage.join_room(user_id, user_name, room_id, room_name)
    environ.env.join_room(room_id)
    environ.env.logger.debug('user %s (%s) is joining %s (%s)' % (user_id, user_name, room_id, room_name))
