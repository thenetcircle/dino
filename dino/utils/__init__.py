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
from activitystreams import parse as as_parser
from typing import Union
from uuid import uuid4 as uuid

import logging
import traceback
import sys

from dino.config import ConfigKeys
from dino import environ
from dino.validation.duration import DurationValidator
from dino.validation.generic import GenericValidator
from dino import validation
from dino.config import UserKeys
from dino.config import ApiActions
from dino.config import ApiTargets
from dino.config import SessionKeys
from dino.utils.decorators import timeit
from dino.utils.blacklist import BlackListChecker
from datetime import timedelta
from datetime import datetime
from base64 import b64encode
from base64 import b64decode

from dino.exceptions import NoOriginRoomException
from dino.exceptions import NoTargetRoomException
from dino.exceptions import UserExistsException
from dino.exceptions import NoSuchUserException
from dino.exceptions import NoSuchRoomException

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)

ADMIN_B64 = 'QWRtaW4='


def b64d(s: str) -> str:
    if s is None:
        return ''

    s = s.strip()
    if len(s) == 0:
        return ''

    try:
        return str(b64decode(bytes(s, 'utf-8')), 'utf-8')
    except Exception as e:
        logger.error('could not b64decode because: %s, value was: \n%s' % (str(e), str(s)))
    return ''


def b64e(s: str) -> str:
    if s is None:
        return ''

    s = s.strip()
    if len(s) == 0:
        return ''

    try:
        return str(b64encode(bytes(s, 'utf-8')), 'utf-8')
    except Exception as e:
        logger.error('could not b64encode because: %s, value was: \n%s' % (str(e), str(s)))
    return ''


def is_base64(s):
    if s is None or len(s.strip()) == 0:
        return False
    try:
        str(b64decode(bytes(s, 'utf-8')), 'utf-8')
    except Exception as e:
        logger.warning('invalid message content, could not decode base64: %s' % str(e))
        logger.exception(traceback.format_exc())
        return False
    return True


def used_blacklisted_word(activity: Activity):
    return environ.env.blacklist.contains_blacklisted_word(activity)


def activity_for_msg_status(activity: Activity, statuses: dict) -> dict:
    act = {
        'object': {
            'objectType': 'statuses',
            'attachments': list()
        },
        'target': {
            'id': activity.target.id,
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'check',
        'id': str(uuid())
    }

    for msg_id, status in statuses.items():
        act['object']['attachments'].append({
            'id': msg_id,
            'content': status
        })

    return act


def activity_for_leave(user_id: str, user_name: str, room_id: str, room_name: str) -> dict:
    return {
        'actor': {
            'id': user_id,
            'displayName': b64e(user_name)
        },
        'target': {
            'id': room_id,
            'displayName': b64e(room_name)
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'leave',
        'id': str(uuid())
    }


def activity_for_user_joined_invisibly(user_id: str, user_name: str, room_id: str, room_name: str, image_url: str) -> dict:
    act = activity_for_user_joined(user_id, user_name, room_id, room_name, image_url)
    act['actor']['objectType'] = 'invisible'
    return act


def activity_for_going_invisible(user_id: str) -> dict:
    return {
        'actor': {
            'id': user_id
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'invisible',
        'id': str(uuid())
    }


def activity_for_going_visible(user_id: str) -> dict:
    return {
        'actor': {
            'id': user_id
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'visible',
        'id': str(uuid())
    }


def activity_for_user_joined(user_id: str, user_name: str, room_id: str, room_name: str, image_url: str) -> dict:
    user_roles = environ.env.db.get_user_roles_in_room(user_id, room_id)
    return {
        'actor': {
            'id': user_id,
            'displayName': b64e(user_name),
            'image': {
                'url': image_url
            },
            'attachments': get_user_info_attachments_for(user_id),
            'content': ','.join(user_roles)
        },
        'target': {
            'id': room_id,
            'displayName': b64e(room_name)
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'join',
        'id': str(uuid())
    }


def activity_for_already_banned(seconds_left: str, reason: str, scope: str='global', target_id: str=None, target_name: str=None) -> dict:
    activity_json = {
        'verb': 'ban',
        'object': {
            'content': '',
            'summary': seconds_left
        },
        'target': {
            'objectType': scope
        },
        'id': str(uuid()),
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
    }

    if reason is not None and len(reason.strip()) > 0:
        activity_json['object']['content'] = b64e(reason)

    if target_id is not None and len(target_id.strip()) > 0:
        activity_json['target']['id'] = target_id
        activity_json['target']['displayName'] = b64e(target_name)

    return activity_json


def activity_for_user_banned(
        banner_id: str, banner_name: str, banned_id: str, banned_name: str, room_id: str, room_name: str, reason=None) -> dict:
    activity_json = {
        'actor': {
            'id': banner_id,
            'displayName': b64e(banner_name)
        },
        'object': {
            'id': banned_id,
            'displayName': b64e(banned_name)
        },
        'target': {
            'id': room_id,
            'displayName': b64e(room_name)
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'ban',
        'id': str(uuid())
    }

    if reason is not None:
        if is_base64(reason):
            activity_json['object']['content'] = reason
        else:
            logger.warn('ignoring reason for kick activity, not base64')
            logger.debug('request with non-base64 reason: %s' % activity_json)

    return activity_json


def activity_for_report(activity: Activity) -> dict:
    return {
        'actor': {
            'id': activity.actor.id,  # user id of the one reporting
            'displayName': b64e(activity.actor.display_name)
        },
        'object': {
            'summary': activity.object.summary,  # free-text reason for reporting
            'content': activity.object.content,  # the reported message
            'id': activity.object.id  # id of the reported message
        },
        'target': {
            'id': activity.target.id,  # user id of user who sent to reported message
            'displayName': activity.target.display_name
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'report',
        'id': str(uuid())
    }


def activity_for_user_kicked(
        kicker_id: str, kicker_name: str, kicked_id: str, kicked_name: str, room_id: str, room_name: str, reason=None) -> dict:
    activity = {
        'actor': {
            'id': kicker_id,
            'displayName': b64e(kicker_name)
        },
        'object': {
            'id': kicked_id
        },
        'target': {
            'id': room_id,
            'displayName': b64e(room_name)
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'kick',
        'id': str(uuid())
    }

    if not is_base64(kicked_name):
        kicked_name = b64e(kicked_name)

    activity['object']['displayName'] = kicked_name

    if reason is not None:
        if is_base64(reason):
            activity['object']['content'] = reason
        else:
            logger.warn('ignoring reason for kick activity, not base64')
            logger.debug('request with non-base64 reason: %s' % activity)

    return activity


def activity_for_request_admin(user_id: str, user_name: str, room_id: str, room_name: str, message: str, admin_room_id: str):
    return {
        'actor': {
            'id': user_id,
            'displayName': b64e(user_name),
            'attachments': get_user_info_attachments_for(user_id)
        },
        'verb': 'request',
        'object': {
            'content': message
        },
        'target': {
            'id': admin_room_id,
            'displayName': b64e('Admins')
        },
        'generator': {
            'id': room_id,
            'displayName': b64e(room_name)
        },
        'id': str(uuid()),
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
    }


def activity_for_disconnect(user_id: str, user_name: str) -> dict:
    return {
        'actor': {
            'id': user_id,
            'displayName': b64e(user_name)
        },
        'verb': 'disconnect',
        'id': str(uuid()),
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
    }


def activity_for_message(user_id: str, user_name: str) -> dict:
    """
    user for sending event to other system to do statistics for how active a user is
    :param user_id: the id of the user
    :param user_name: the name of the user
    :return: an activity streams dict
    """
    return {
        'actor': {
            'id': user_id,
            'displayName': b64e(user_name)
        },
        'verb': 'send',
        'id': str(uuid()),
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
    }


def activity_for_blacklisted_word(activity: Activity, blacklisted_word: str) -> dict:
    return {
        'actor': {
            'id': activity.actor.id,
            'displayName': activity.actor.display_name
        },
        'object': {
            'content': activity.object.content,
            'summary': b64e(blacklisted_word)
        },
        'target': {
            'id': activity.target.id,
            'displayName': b64e(activity.target.display_name)
        },
        'verb': 'blacklisted',
        'id': str(uuid()),
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
    }


def activity_for_login(user_id: str, user_name: str, include_unread_history: bool=False) -> dict:
    response = {
        'actor': {
            'id': user_id,
            'displayName': b64e(user_name),
            'attachments': get_user_info_attachments_for(user_id)
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'login',
        'id': str(uuid())
    }

    if include_unread_history:
        messages = get_unacked_messages(user_id)
        if len(messages) > 0:
            history_activity = activity_for_history(as_parser(response), messages)
            response['object'] = {
                'objectType': 'history',
                'attachments': history_activity['object']['attachments']
            }

    return response


def get_unacked_messages(user_id: str) -> list:
    return environ.env.storage.get_unacked_history(user_id)


def activity_for_connect(user_id: str, user_name: str) -> dict:
    return {
        'actor': {
            'id': user_id,
            'displayName': b64e(user_name),
            'attachments': get_user_info_attachments_for(user_id)
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'connect',
        'id': str(uuid())
    }


def activity_for_create_room(data: dict, activity: Activity) -> dict:
    response = {
        'actor': {
            'id': activity.actor.id,
            'displayName': b64e(activity.actor.display_name),
            'attachments': get_user_info_attachments_for(activity.actor.id)
        },
        'object': {
            'url': activity.object.url
        },
        'target': {
            'id': activity.target.id,
            'displayName': activity.target.display_name,
            'objectType': 'temporary'  # all rooms created using the api are temporary
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'create',
        'id': str(uuid())
    }

    if 'object' in data and 'attachments' in data['object']:
        response['object']['attachments'] = data['object']['attachments']

    return response


@timeit(logger, 'on_activity_for_history')
def activity_for_history(activity: Activity, messages: list) -> dict:
    response = {
        'object': {
            'objectType': 'messages'
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'id': str(uuid()),
        'verb': 'history'
    }

    if hasattr(activity, 'target') and hasattr(activity.target, 'id'):
        try:
            room_name = b64e(get_room_name(activity.target.id))
        except NoSuchRoomException as e:
            logger.exception('could not find room name for room id %s: %s' % (activity.target.id, str(e)))
            room_name = ''
        response['target'] = {
            'id': activity.target.id,
            'displayName': room_name
        }

    response['object']['attachments'] = list()
    for message in messages:
        response['object']['attachments'].append({
            'author': {
                'id': message['from_user_id'],
                'displayName': b64e(message['from_user_name'])
            },
            'summary': message['target_id'],
            'id': message['message_id'],
            'content': b64e(message['body']),
            'published': message['timestamp']
        })
    return response


def activity_for_join(activity: Activity, acls: dict, messages: list, owners: dict, users: dict) -> dict:
    response = {
        'object': {
            'objectType': 'room',
            'attachments': list()
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'join',
        'target': {
            'id': activity.target.id,
            'displayName': b64e(get_room_name(activity.target.id))
        },
        'id': str(uuid())
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


def check_if_should_remove_room(data, activity):
    room_id = activity.target.id
    room_name = get_room_name(room_id)

    logger.info('checking whether to remove room "%s" (%s) or not' % (room_name, room_id))

    check_if_remove_room_empty(activity)


def remove_room(channel_id, room_id, user_id, user_name, room_name):
    logger.info('removing room %s (%s), last owner has left/disconnected' % (room_id, room_name))
    environ.env.db.remove_room(channel_id, room_id)
    remove_activity = activity_for_remove_room(user_id, user_name, room_id, room_name)
    environ.env.emit('gn_room_removed', remove_activity, broadcast=True, include_self=True, namespace='/ws')


def check_if_remove_room_empty(activity: Activity):
    user_id = activity.actor.id
    user_name = environ.env.session.get(SessionKeys.user_name.value)
    room_id = activity.target.id
    room_name = get_room_name(room_id)
    channel_id = get_channel_for_room(room_id)

    if not environ.env.db.is_room_ephemeral(room_id):
        logger.info('room %s (%s) is not ephemeral, not considering removal' % (room_name, room_id))
        return

    users_in_room = get_users_in_room(room_id)

    if user_id in users_in_room:
        del users_in_room[user_id]
    if len(users_in_room) > 0:
        return
    remove_room(channel_id, room_id, user_id, user_name, room_name)


# currently not used, rooms are removed if empty, not if owner leaves
def check_if_remove_room_owner(activity: Activity):
    user_id = activity.actor.id
    user_name = environ.env.session.get(SessionKeys.user_name.value)
    room_id = activity.target.id
    room_name = get_room_name(room_id)
    channel_id = get_channel_for_room(room_id)

    if not environ.env.db.is_room_ephemeral(room_id):
        logger.info('room %s (%s) is not ephemeral, not considering removal' % (room_name, room_id))
        return

    owners = get_owners_for_room(room_id)
    users_in_room = get_users_in_room(room_id)

    if user_id in users_in_room:
        del users_in_room[user_id]

    for owner_id, owner_name in owners.items():
        if owner_id in users_in_room:
            logger.info('owner %s (%s) is still in room %s (%s), not considering removal' %
                        (owner_name, owner_id, room_name, room_id))
            return

    for user_id_still_in_room, user_name_still_in_room in users_in_room.items():
        kick_activity = {
            'actor': {
                'id': user_id,
                'displayName': b64e(user_name)
            },
            'verb': 'kick',
            'object': {
                'id': user_id_still_in_room,
                'displayName': b64e(user_name_still_in_room),
                'content': b64e('All owners have left the room')
            },
            'target': {
                'url': environ.env.request.namespace,
                'id': room_id,
                'displayName': b64e(room_name)
            }
        }
        environ.env.publish(kick_activity)

    remove_room(channel_id, room_id, user_id, user_name, room_name)


def activity_for_owners(activity: Activity, owners: dict) -> dict:
    response = {
        'object': {
            'objectType': 'owner'
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'target': {
            'id': activity.target.id,
            'displayName': b64e(activity.target.display_name)
        },
        'verb': 'list',
        'id': str(uuid())
    }

    response['object']['attachments'] = list()
    for user_id, user_name in owners.items():
        response['object']['attachments'].append({
            'id': user_id,
            'displayName': b64e(user_name)
        })

    return response


def is_channel_static_or_temporary_or_mix(channel_id: str) -> str:
    return environ.env.db.type_of_rooms_in_channel(channel_id)


def activity_for_list_channels(activity: Activity, channels: dict) -> dict:
    response = {
        'object': {
            'objectType': 'channels'
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'list'
    }

    response['object']['attachments'] = list()
    for channel_id, (channel_name, sort_order) in channels.items():
        object_type = is_channel_static_or_temporary_or_mix(channel_id)

        response['object']['attachments'].append({
            'id': channel_id,
            'url': sort_order,
            'displayName': b64e(channel_name),
            'objectType': object_type
        })
        response['object']['attachments'] = sorted(response['object']['attachments'], key=lambda k: k['url'])

    return response


def activity_for_invite(
        inviter_id: str, inviter_name: str, room_id: str, room_name: str,
        channel_id: str, channel_name: str) -> dict:
    return {
        'actor': {
            'id': inviter_id,
            'displayName': b64e(inviter_name),
            'attachments': get_user_info_attachments_for(inviter_id)
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'invite',
        'object': {
            'url': channel_id,
            'displayName': b64e(channel_name)
        },
        'target': {
            'id': room_id,
            'displayName': b64e(room_name)
        },
        'id': str(uuid())
    }


def activity_for_whisper(
        message: str, whisperer_id: str, whisperer_name: str, room_id: str, room_name: str,
        channel_id: str, channel_name: str) -> dict:
    return {
        'actor': {
            'id': whisperer_id,
            'displayName': b64e(whisperer_name)
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'whisper',
        'object': {
            'content': message,
            'url': channel_id,
            'displayName': b64e(channel_name)
        },
        'target': {
            'id': room_id,
            'displayName': b64e(room_name)
        },
        'id': str(uuid())
    }


def activity_for_broadcast(body: str, verb: str='broadcast') -> dict:
    return {
        'actor': {
            'displayName': ADMIN_B64,  # 'Admin' in base64
            'id': '0'
        },
        'content': body,
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': verb,
        'id': str(uuid())
    }


def activity_for_list_rooms(activity: Activity, rooms: dict) -> dict:
    response = {
        'object': {
            'url': activity.object.url,
            'objectType': 'rooms'
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'list',
        'id': str(uuid())
    }

    response['object']['attachments'] = list()
    for room_id, room_details in rooms.items():
        room_name = room_details['name']
        nr_users_in_room = room_details['users']

        object_type = 'static'
        if 'ephemeral' in room_details and room_details['ephemeral']:
            object_type = 'temporary'

        response['object']['attachments'].append({
            'id': room_id,
            'url': room_details['sort_order'],
            'displayName': b64e(room_name),
            'summary': nr_users_in_room,
            'objectType': object_type,
            'content': room_details['roles']
        })

    return response


@timeit(logger, 'on_activity_for_users_in_room')
def activity_for_users_in_room(activity: Activity, users_orig: dict) -> dict:
    users = users_orig.copy()
    response = {
        'target': {
            'id': activity.target.id,
            'displayName': b64e(activity.target.display_name)
        },
        'object': {
            'objectType': 'users'
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'list',
        'id': str(uuid())
    }

    response['object']['attachments'] = list()
    this_user_id = environ.env.session.get(SessionKeys.user_id.value)
    this_user_is_super_user = is_super_user(this_user_id) or is_global_moderator(this_user_id)

    for user_id, user_name in users.items():
        user_info = get_user_info_attachments_for(user_id)
        if this_user_is_super_user:
            user_ip = ''
            try:
                user_ip = environ.env.request.remote_addr
            except Exception as e:
                logger.error('could not get remote address of user %s: %s' % (user_info, str(e)))
                logger.exception(traceback.format_exc())
                environ.env.capture_exception(sys.exc_info())

            user_info.append({
                'objectType': 'ip',
                'content': b64e(user_ip)
            })

        # temporary fix for avoiding dead users
        if len(user_info) == 0:
            environ.env.db.leave_room(user_id, activity.target.id)
            continue

        user_roles = environ.env.db.get_user_roles_in_room(user_id, activity.target.id)
        user_attachment = {
            'id': user_id,
            'displayName': b64e(user_name),
            'attachments': user_info,
            'content': ','.join(user_roles),
            'objectType': 'user'
        }
        if this_user_is_super_user and user_is_invisible(user_id):
            user_attachment['objectType'] = 'invisible'

        response['object']['attachments'].append(user_attachment)

    return response


def activity_for_room_removed(activity: Activity, room_name: str, reason: str=None) -> dict:
    act = {
        'target': {
            'id': activity.target.id,
            'displayName': b64e(room_name),
            'objectType': 'room'
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'removed',
        'id': str(uuid())
    }

    if reason is not None and len(reason.strip()) > 0:
        act['object'] = {
            'content': b64e(reason)
        }

    return act


def activity_for_remove_room(user_id: str, user_name: str, room_id: str, room_name: str, reason: str=None) -> dict:
    act = {
        'actor': {
            'id': user_id,
            'displayName': b64e(user_name)
        },
        'target': {
            'id': room_id,
            'displayName': b64e(room_name)
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'remove',
        'id': str(uuid())
    }

    if reason is not None and len(reason.strip()) > 0:
        act['object'] = {
            'content': b64e(reason)
        }

    return act


def get_user_info_attachments_for(user_id: str) -> list:
    attachments = list()
    for info_key, info_val in environ.env.auth.get_user_info(user_id).items():
        attachments.append({
            'objectType': info_key,
            'content': b64e(info_val)
        })

    return attachments


def activity_for_get_acl(activity: Activity, acl_values: dict) -> dict:
    response = {
        'object': {
            'objectType': 'acl'
        },
        'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
        'verb': 'get',
        'id': str(uuid())
    }

    if hasattr(activity, 'target') and hasattr(activity.target, 'id'):
        response['target'] = {'id': activity.target.id}

    response['object']['attachments'] = list()
    for api_action, acls in acl_values.items():
        for acl_type, acl_value in acls.items():
            response['object']['attachments'].append({
                'objectType': acl_type,
                'content': acl_value,
                'summary': api_action
            })

    return response


def is_user_in_room(user_id, room_id):
    if room_id is None or len(room_id.strip()) == 0:
        return False
    return environ.env.db.room_contains(room_id, user_id)


def set_name_for_user_id(user_id: str, user_name: str) -> None:
    environ.env.db.set_user_name(user_id, user_name)


def add_sid_for_user_id(user_id: str, sid: str) -> None:
    if sid is None or len(sid.strip()) == 0:
        logger.error('empty sid when adding sid')
        return
    environ.env.db.add_sid_for_user(user_id, sid)


def get_sids_for_user_id(user_id: str) -> Union[list, None]:
    return environ.env.db.get_sids_for_user(user_id)


def create_or_update_user(user_id: str, user_name: str) -> bool:
    try:
        environ.env.db.create_user(user_id, user_name)
        return
    except UserExistsException:
        pass
    environ.env.db.set_user_name(user_id, user_name)


def is_banned_globally(user_id: str) -> (bool, Union[str, None]):
    user_is_banned, timestamp = environ.env.db.is_banned_globally(user_id)
    if not user_is_banned or timestamp is None or timestamp == '':
        return False, None

    now = datetime.utcnow()
    end = datetime.fromtimestamp(float(timestamp))
    return True, (end - now).seconds


def reason_for_ban(user_id: str, scope: str=None, target_id: str=None) -> str:
    if scope is None or len(scope.strip()) == 0 or scope == 'global':
        return environ.env.db.get_reason_for_ban_global(user_id)
    elif scope == 'channel':
        return environ.env.db.get_reason_for_ban_channel(user_id, target_id)
    elif scope == 'room':
        return environ.env.db.get_reason_for_ban_room(user_id, target_id)
    raise KeyError('scope not in [channel,room,global] but "%s"' % str(scope))


def is_banned(user_id: str, room_id: str) -> (bool, Union[str, None]):
    bans = environ.env.db.get_user_ban_status(room_id, user_id)

    global_time = bans['global']
    channel_time = bans['channel']
    room_time = bans['room']
    now = datetime.utcnow()

    if global_time != '':
        end = datetime.fromtimestamp(int(global_time))
        seconds = str((end - now).seconds)
        logger.debug('user %s is banned globally for another %s seconds' %
                     (user_id, str((end - now).seconds)))
        return True, {'scope': 'global', 'seconds': seconds, 'id': ''}

    if channel_time != '':
        end = datetime.fromtimestamp(int(channel_time))
        seconds = str((end - now).seconds)
        channel_id = get_channel_for_room(room_id)
        logger.debug('user %s is banned in channel %s for another %s seconds' %
                     (user_id, channel_id, str((end - now).seconds)))
        return True, {'scope': 'channel', 'seconds': seconds, 'id': channel_id}

    if room_time != '':
        end = datetime.fromtimestamp(int(float(room_time)))
        seconds = str((end - now).seconds)
        logger.debug('user %s is banned in room %s for another %s seconds' %
                     (user_id, room_id, str((end - now).seconds)))
        return True, {'scope': 'room', 'seconds': seconds, 'id': room_id}

    return False, None


def kick_user(room_id: str, user_id: str) -> None:
    environ.env.db.kick_user(room_id, user_id)


def ban_user(room_id: str, user_id: str, ban_duration: str) -> None:
    if user_id is None or len(user_id.strip()) == 0:
        raise NoSuchUserException(user_id)
    ban_timestamp = ban_duration_to_timestamp(ban_duration)
    environ.env.db.ban_user_room(user_id, ban_timestamp, ban_duration, room_id)


def ban_duration_to_timestamp(ban_duration: str) -> str:
    return datetime_to_timestamp(ban_duration_to_datetime(ban_duration))


def ban_duration_to_datetime(ban_duration: str) -> datetime:
    DurationValidator(ban_duration)

    days = 0
    hours = 0
    seconds = 0
    duration_unit = ban_duration[-1]
    ban_duration = ban_duration[:-1]

    if duration_unit == 'd' and GenericValidator.is_digit(ban_duration):
        days = int(ban_duration)
    elif duration_unit == 'h' and GenericValidator.is_digit(ban_duration):
        hours = int(ban_duration)
    elif duration_unit == 'm' and GenericValidator.is_digit(ban_duration):
        seconds = int(ban_duration) * 60
    elif duration_unit == 's' and GenericValidator.is_digit(ban_duration):
        seconds = int(ban_duration)

    now = datetime.utcnow()
    ban_time = timedelta(days=days, hours=hours, seconds=seconds)
    end_date = now + ban_time

    return end_date


def datetime_to_timestamp(some_date: datetime) -> str:
    return str(int(some_date.timestamp()))


def is_super_user(user_id: str) -> bool:
    return environ.env.db.is_super_user(user_id)


def is_owner(room_id: str, user_id: str) -> bool:
    return environ.env.db.is_owner(room_id, user_id)


def is_owner_channel(channel_id: str, user_id: str) -> bool:
    return environ.env.db.is_owner_channel(channel_id, user_id)


def is_global_moderator(user_id: str) -> bool:
    return environ.env.db.is_global_moderator(user_id)


def is_moderator(room_id: str, user_id: str) -> bool:
    return environ.env.db.is_moderator(room_id, user_id)


def is_admin(channel_id: str, user_id: str) -> bool:
    return environ.env.db.is_admin(channel_id, user_id)


def is_room_ephemeral(room_id: str) -> bool:
    return environ.env.db.is_room_ephemeral(room_id)


def get_users_in_room(room_id: str, user_id: str=None, skip_cache: bool=False) -> dict:
    """
    get a dict of user_id => user_name for users in this room

    :param room_id: the uuid of the room
    :param user_id: if specified, will check if super user, and if so will also include invisible users
    :param skip_cache: if True, check db directly, used for gn_join to get correct user list when joining; when listing
    rooms it is not necessary to have exact list; cache is 10-20s (random) per room
    :param this_user_id: the id of the user making the request; if admin the response included more information
    :return: a list of users in the room
    """
    return environ.env.db.users_in_room(room_id, this_user_id=user_id, skip_cache=skip_cache)


def get_acls_in_room_for_action(room_id: str, action: str) -> dict:
    return environ.env.db.get_acls_in_room_for_action(room_id, action)


def get_acls_in_channel_for_action(channel_id: str, action: str) -> dict:
    return environ.env.db.get_acls_in_channel_for_action(channel_id, action)


def get_acls_for_room(room_id: str) -> dict:
    return environ.env.db.get_all_acls_room(room_id)


def get_acls_for_channel(channel_id: str) -> dict:
    return environ.env.db.get_all_acls_channel(channel_id)


def get_owners_for_room(room_id: str) -> dict:
    return environ.env.db.get_owners_room(room_id)


def channel_exists(channel_id: str) -> bool:
    return environ.env.db.channel_exists(channel_id)


def get_user_name_for(user_id: str) -> str:
    return environ.env.db.get_user_name(user_id)


def get_channel_name(channel_id: str) -> str:
    return environ.env.db.get_channel_name(channel_id)


def get_room_name(room_id: str) -> str:
    return environ.env.db.get_room_name(room_id)


def get_room_id(room_name: str) -> str:
    return environ.env.db.get_room_id_for_name(room_name)


def room_exists(channel_id: str, room_id: str) -> bool:
    return environ.env.db.room_exists(channel_id, room_id)


def room_name_restricted(room_name: str):
    return room_name.strip().lower() in ['admins', 'admin']


def get_user_roles(user_id: str):
    return environ.env.db.get_user_roles(user_id)


def rooms_for_user(user_id: str):
    rooms = environ.env.db.rooms_for_user(user_id)
    if rooms is None or len(rooms) == 0:
        return set()
    return set(rooms.keys())


def can_send_cross_room(activity: Activity, from_room_uuid: str, to_room_uuid: str) -> bool:
    if from_room_uuid is None:
        raise NoOriginRoomException()
    if to_room_uuid is None:
        raise NoTargetRoomException()

    if from_room_uuid == to_room_uuid:
        return True

    from_channel_id = None
    to_channel_id = None

    if hasattr(activity, 'provider') and hasattr(activity.provider, 'url'):
        from_channel_id = activity.object.url
    if hasattr(activity, 'object') and hasattr(activity.object, 'url'):
        to_channel_id = activity.object.url

    if from_channel_id is None or len(from_channel_id.strip()) == 0:
        from_channel_id = get_channel_for_room(from_room_uuid)
    if to_channel_id is None or len(to_channel_id.strip()) == 0:
        to_channel_id = get_channel_for_room(to_room_uuid)

    # can not send between channels
    if from_channel_id != to_channel_id:
        return False

    channel_acls = get_acls_in_channel_for_action(to_channel_id, ApiActions.CROSSROOM)
    is_valid, msg = validation.acl.validate_acl_for_action(
        activity, ApiTargets.CHANNEL, ApiActions.CROSSROOM, channel_acls or dict())
    if not is_valid:
        logger.debug('not allowed to send crossroom in channel: %s' % msg)
        return False

    try:
        room_acls = get_acls_in_room_for_action(to_room_uuid, ApiActions.CROSSROOM)
    except NoSuchRoomException:
        logger.warning('room %s does not exist, maybe deleted before cache updated' % to_room_uuid)
        return False

    is_valid, msg = validation.acl.validate_acl_for_action(
        activity, ApiTargets.ROOM, ApiActions.CROSSROOM, room_acls or dict())
    if not is_valid:
        logger.debug('not allowed to send crossroom in room: %s' % msg)
        return False

    return is_valid


def get_admin_room() -> str:
    return environ.env.db.get_admin_room()


def get_channel_for_room(room_id: str) -> str:
    return environ.env.db.channel_for_room(room_id)


def get_sender_for_message(message_id: str) -> Union[str, None]:
    message = environ.env.storage.get_message(message_id)
    if message is None:
        return None
    return message.get('from_user_id', None)


def user_is_allowed_to_delete_message(room_id: str, user_id: str) -> bool:
    channel_id = get_channel_for_room(room_id)
    if is_owner(room_id, user_id):
        return True
    if is_moderator(room_id, user_id):
        return True
    if is_owner_channel(channel_id, user_id):
        return True
    if is_admin(channel_id, user_id):
        return True
    if is_super_user(user_id):
        return True
    if is_global_moderator(user_id):
        return True

    return False


@timeit(logger, 'on_get_history_for_room')
def get_history_for_room(room_id: str, user_id: str, last_read: str = None) -> list:
    history = environ.env.config.get(
            ConfigKeys.TYPE,
            domain=ConfigKeys.HISTORY,
            default=ConfigKeys.DEFAULT_HISTORY_STRATEGY)

    limit = environ.env.config.get(
            ConfigKeys.LIMIT,
            domain=ConfigKeys.HISTORY,
            default=ConfigKeys.DEFAULT_HISTORY_LIMIT)

    def _history(_last_read: str = None):
        if history == 'top':
            return environ.env.storage.get_history(room_id, limit)

        if _last_read is None:
            _last_read = get_last_read_for(room_id, user_id)
            if _last_read is None:
                return list()

        return environ.env.storage.get_unread_history(room_id, _last_read)
    return _history(last_read)


def remove_user_from_room(user_id: str, user_name: str, room_id: str) -> None:
    environ.env.leave_room(room_id)
    environ.env.db.leave_room(user_id, room_id)


def join_the_room(user_id: str, user_name: str, room_id: str, room_name: str) -> None:
    environ.env.db.join_room(user_id, user_name, room_id, room_name)
    environ.env.join_room(room_id)
    logger.debug('user %s (%s) is joining %s (%s)' % (user_id, user_name, room_id, room_name))


def user_is_online(user_id: str) -> bool:
    if user_id is None or len(user_id.strip()) == 0:
        logger.warn('can not check user online status, user_id was blank!')
        return False

    return get_user_status(user_id) in {
        UserKeys.STATUS_AVAILABLE,
        UserKeys.STATUS_CHAT,
        UserKeys.STATUS_INVISIBLE
    }


def user_is_invisible(user_id: str) -> bool:
    if user_id is None or len(user_id.strip()) == 0:
        logger.warn('can not check user online status, user_id was blank!')
        return False
    return get_user_status(user_id) == UserKeys.STATUS_INVISIBLE


def get_user_status(user_id: str) -> str:
    return environ.env.db.get_user_status(user_id)


def get_last_read_for(room_id: str, user_id: str) -> str:
    return environ.env.db.get_last_read_timestamp(room_id, user_id)


def update_last_reads_private(user_id: str) -> None:
    status = get_user_status(user_id)
    if status in [None, UserKeys.STATUS_UNAVAILABLE, UserKeys.STATUS_UNKNOWN]:
        return
    time_stamp = int(datetime.utcnow().strftime('%s'))
    environ.env.db.update_last_read_for({user_id}, user_id, time_stamp)


def update_last_reads(room_id: str) -> None:
    users_in_room = get_users_in_room(room_id)
    online_users_in_room = set()

    for user_id, _ in users_in_room.items():
        status = get_user_status(user_id)
        if status in [None, UserKeys.STATUS_UNAVAILABLE, UserKeys.STATUS_UNKNOWN]:
            continue

        online_users_in_room.add(user_id)

    time_stamp = int(datetime.utcnow().strftime('%s'))
    environ.env.db.update_last_read_for(online_users_in_room, room_id, time_stamp)
