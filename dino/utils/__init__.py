#!/usr/bin/env python

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from activitystreams import Activity
from typing import Union

from dino.config import SessionKeys
from dino import environ
from dino import rkeys
from dino.validator import Validator
from datetime import timedelta
from datetime import datetime

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


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


def activity_for_user_kicked(
        kicker_id: str, kicker_name: str, kicked_id: str, kicked_name: str, room_id: str, room_name: str) -> dict:
    return {
        'actor': {
            'id': kicker_id,
            'summary': kicker_name
        },
        'object': {
            'id': kicked_id,
            'summary': kicked_name
        },
        'target': {
            'id': room_id,
            'displayName': room_name,
            'objectType': 'group'
        },
        'verb': 'kick'
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


def activity_for_create_room(activity: Activity) -> dict:
    return {
        'actor': {
            'id': activity.actor.id,
            'content': activity.actor.content
        },
        'object': {
            'id': activity.object.id,
            'content': activity.object.content,
            'url': activity.object.url
        },
        'target': {
            'id': activity.target.id,
            'displayName': activity.target.display_name
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


def activity_for_list_channels(activity: Activity, channels: dict) -> dict:
    response = {
        'object': {
            'objectType': 'channels'
        },
        'verb': 'list'
    }

    response['object']['attachments'] = list()
    for channel_id, channel_name in channels.items():
        response['object']['attachments'].append({
            'id': channel_id,
            'content': channel_name
        })

    return response


def activity_for_list_rooms(activity: Activity, rooms: dict) -> dict:
    response = {
        'object': {
            'id': activity.object.id,
            'objectType': 'rooms'
        },
        'verb': 'list'
    }

    response['object']['attachments'] = list()
    for room_id, room_name in rooms.items():
        response['object']['attachments'].append({
            'id': room_id,
            'content': room_name
        })

    return response


def is_user_in_room(user_id, room_id):
    return environ.env.storage.room_contains(room_id, user_id)


def set_sid_for_user_id(user_id: str, sid: str) -> None:
    environ.env.redis.hset(rkeys.sid_for_user_id(), user_id, sid)


def get_sid_for_user_id(user_id: str) -> str:
    return environ.env.redis.hmget(rkeys.sid_for_user_id(), user_id)


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


def is_banned(user_id: str, room_id: str=None) -> (bool, Union[str, None]):
    if room_id is None or room_id == '':
        duration = environ.env.redis.hget(rkeys.banned_users(room_id), user_id)
    else:
        duration = environ.env.redis.hget(rkeys.banned_users(room_id), user_id)

    if duration is not None and duration != '':
        end = datetime.fromtimestamp(duration)
        now = datetime.now()
        diff = end - now
        if diff.seconds() > 0:
            return True, str(diff.seconds())

        if room_id is None or room_id == '':
            environ.env.redis.hdel(rkeys.banned_users(), user_id)
        else:
            environ.env.redis.hdel(rkeys.banned_users(room_id), user_id)

    return False, None


def get_current_user_role() -> str:
    if is_admin(environ.env.config.get(SessionKeys.USER_ID)):
        return 'admin'
    return 'user'


def ban_duration_to_timestamp(ban_duration: str) -> str:
    if ban_duration is None or ban_duration == '':
        raise ValueError('empty ban duration')

    if not ban_duration.endswith('s') and not ban_duration.endswith('m') and not ban_duration.endswith('d'):
        raise ValueError('invalid ban duration: %s' % ban_duration)

    if ban_duration.startswith('-'):
        raise ValueError('can not set negative ban duration: %s' % ban_duration)

    if ban_duration.startswith('+'):
        ban_duration = ban_duration[1:]

    if not Validator.is_digit(ban_duration[:-1]):
        raise ValueError('invalid ban duration, not a number: %s' % ban_duration)

    days = 0
    seconds = 0
    if ban_duration.endswith('d'):
        ban_duration = ban_duration[:-1]
        try:
            days = int(ban_duration)
        except ValueError as e:
            environ.env.logger.error('could not convert ban duration "%s" to int: %s' % (ban_duration, str(e)))
            raise ValueError('invalid ban duration, not a number: %s' % ban_duration)
    elif ban_duration.endswith('m'):
        ban_duration = ban_duration[:-1]
        try:
            seconds = int(ban_duration) * 60
        except ValueError as e:
            environ.env.logger.error('could not convert ban duration "%s" to int: %s' % (ban_duration, str(e)))
            raise ValueError('invalid ban duration, not a number: %s' % ban_duration)
    elif ban_duration.endswith('s'):
        ban_duration = ban_duration[:-1]
        try:
            seconds = int(ban_duration)
        except ValueError as e:
            environ.env.logger.error('could not convert ban duration "%s" to int: %s' % (ban_duration, str(e)))
            raise ValueError('invalid ban duration, not a number: %s' % ban_duration)
    else:
        raise ValueError('unknown ban duration: %s' % ban_duration)

    now = datetime.now()
    ban_time = timedelta(days=days, seconds=seconds)
    end_date = now + ban_time

    return str(int(end_date.timestamp()))


def ban_user(room_id: str, user_id: str, ban_duration: str) -> None:
    ban_timestamp = ban_duration_to_timestamp(ban_duration)
    is_global_ban = room_id is None or room_id == ''

    if is_global_ban:
        environ.env.redis.hset(rkeys.banned_users(), user_id, ban_timestamp)
    else:
        environ.env.redis.hset(rkeys.banned_users(room_id), user_id, ban_timestamp)


def is_owner(room_id: str, user_id: str) -> bool:
    return environ.env.db.room_owners_contain(room_id, user_id)


def is_admin(user_id: str) -> bool:
    return environ.env.db.is_admin(user_id)


def get_users_in_room(room_id: str) -> list:
    return environ.env.storage.users_in_room(room_id)


def get_acls_for_room(room_id: str) -> dict:
    return environ.env.db.get_acls(room_id)


def get_owners_for_room(room_id: str) -> dict:
    return environ.env.storage.get_owners(room_id)


def room_exists(channel_id: str, room_id: str) -> dict:
    return environ.env.db.room_exists(channel_id, room_id)


def get_history_for_room(room_id: str, limit: int = 10) -> list:
    return environ.env.storage.get_history(room_id, limit)


def remove_user_from_room(user_id: str, user_name: str, room_id: str) -> None:
    environ.env.leave_room(room_id)
    environ.env.storage.leave_room(user_id, room_id)


def join_the_room(user_id: str, user_name: str, room_id: str, room_name: str) -> None:
    environ.env.storage.join_room(user_id, user_name, room_id, room_name)
    environ.env.join_room(room_id)
    environ.env.logger.debug('user %s (%s) is joining %s (%s)' % (user_id, user_name, room_id, room_name))
