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

from typing import Union

from activitystreams.models.activity import Activity
from activitystreams.models.defobject import DefObject
from flask import request

from dino.config import ApiTargets
from dino.config import ErrorCodes as ECodes
from dino.exceptions import NoSuchRoomException
from dino.hooks import *
from dino.config import ApiActions
from dino.utils.decorators import timeit
from dino import validation

import logging
import sys

__author__ = 'Oscar Eriksson <oscar@gmail.com>'

logger = logging.getLogger(__name__)


def connect() -> (int, None):
    """
    connect to the server

    :return: {'status_code': 200}
    """
    return ECodes.OK, None


@timeit(logger, 'on_login')
def on_login(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    event sent directly after a connection has successfully been made, to get the user_id for this connection

    :param data: activity streams format, needs actor.id (user id) and actor.summary (user name)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    user_id = environ.env.session.get(SessionKeys.user_id.value)
    user_name = environ.env.session.get(SessionKeys.user_name.value)
    user_roles = utils.get_user_roles(user_id)

    response = utils.activity_for_login(user_id, user_name)
    response['actor']['attachments'] = list()

    if len(user_roles['global']) > 0:
        response['actor']['attachments'].append({
            'objectType': 'global_role',
            'content': ','.join(user_roles['global'])
        })

    for room_uuid, roles in user_roles['room'].items():
        response['actor']['attachments'].append({
            'objectType': 'room_role',
            'id': room_uuid,
            'content': ','.join(roles)
        })

    for channel_uuid, roles in user_roles['channel'].items():
        response['actor']['attachments'].append({
            'objectType': 'channel_role',
            'id': channel_uuid,
            'content': ','.join(roles)
        })

    environ.env.observer.emit('on_login', (data, activity))
    return ECodes.OK, response


@timeit(logger, 'on_delete')
def on_delete(data: dict, activity: Activity):
    environ.env.observer.emit('on_delete', (data, activity))
    return ECodes.OK, None


@timeit(logger, 'on_message')
def on_message(data, activity: Activity):
    """
    send any kind of message/event to a target user/room

    object.url: target channel_id
    target.id: target room_id
    actor.id: sender user_id
    actor.url: sender room_id

    :param data: activity streams format, must include target.id (room/user id) and object.url (channel id)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: {'status_code': ECodes.OK, 'data': '<same AS as client sent, plus timestamp>'}
    """
    room_id = activity.target.id
    from_room_id = activity.actor.url

    # only if cross-room should we broadcast the origin room id with the activity; less confusion for clients
    if from_room_id is not None and from_room_id == room_id:
        del data['actor']['url']

    channel_id = None
    if activity.target.object_type != 'room':
        if hasattr(activity, 'object') and hasattr(activity.object, 'url'):
            channel_id = activity.object.url
        if channel_id is None or len(channel_id.strip()) == 0:
            channel_id = utils.get_channel_for_room(room_id)

        channel_name = utils.get_channel_name(channel_id)
        if not hasattr(activity, 'object'):
            activity.object = DefObject(dict())

        activity.object.url = channel_id
        activity.object.display_name = channel_name

    if 'object' not in data or len(data['object']) == 0:
        data['object'] = {
            'url': activity.object.url,
            'displayName': activity.object.display_name
        }
    else:
        data['object']['url'] = activity.object.url
        data['object']['displayName'] = activity.object.display_name

    if from_room_id is not None and len(from_room_id.strip()) > 0:
        activity.provider.url = utils.get_channel_for_room(from_room_id)
        activity.provider.display_name = utils.get_channel_name(activity.provider.url)
        if 'provider' not in data or len(data['provider']) == 0:
            data['provider'] = {
                'url': activity.provider.url,
                'displayName': activity.provider.display_name
            }
        else:
            data['provider']['url'] = activity.provider.url
            data['provider']['displayName'] = activity.provider.display_name

    if activity.target.object_type == 'room':
        activity.target.display_name = utils.get_room_name(activity.target.id)
    else:
        activity.target.display_name = utils.get_user_name_for(activity.target.id)
        activity.object.display_name = ''
        activity.object.url = ''

    activity.actor.display_name = utils.b64e(environ.env.session.get(SessionKeys.user_name.value))
    data['actor']['displayName'] = activity.actor.display_name

    data['target']['displayName'] = utils.b64e(activity.target.display_name)
    data['object']['displayName'] = utils.b64e(activity.object.display_name)

    environ.env.observer.emit('on_message', (data, activity))
    return ECodes.OK, data


@timeit(logger, 'on_update_user_info')
def on_update_user_info(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    broadcast a user info update to a room, or all rooms the user is in if no target.id specified

    :param data: activity streams format, must include object.attachments (user info)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: {'status_code': ECodes.OK, 'data': '<same AS as client sent, plus timestamp>'}
    """
    activity.actor.display_name = utils.b64e(environ.env.session.get(SessionKeys.user_name.value))
    data['actor']['displayName'] = activity.actor.display_name
    environ.env.observer.emit('on_update_user_info', (data, activity))
    return ECodes.OK, data


@timeit(logger, 'on_ban')
def on_ban(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    ban a user from a room (if user is an owner/admin/moderator)

    target.id: the uuid of the room that the user is in
    target.displayName: the room name
    object.id: the id of the user to kick
    object.content: the name of the user to kick
    object.summary: the ban time, e.g.
    actor.id: the id of the kicker
    actor.content: the name of the kicker

    :param data: activity streams format
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<error message>'}
    """
    environ.env.observer.emit('on_ban', (data, activity))
    #environ.env.observer.emit('on_kick', (data, activity))
    return ECodes.OK, None


@timeit(logger, 'on_kick')
def on_kick(data: dict, activity: Activity) -> (int, None):
    """
    kick a user from a room (if user is an owner)

    target.id: the uuid of the room that the user is in
    target.displayName: the room name
    object.id: the id of the user to kick
    object.content: the name of the user to kick
    actor.id: the id of the kicker
    actor.content: the name of the kicker

    :param data: activity streams format
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<error message>'}
    """
    environ.env.observer.emit('on_kick', (data, activity))
    return ECodes.OK, None


@timeit(logger, 'on_whisper')
def on_whisper(data: dict, activity: Activity) -> (int, None):
    """
    whisper to another person in the same room, only that person will receive the event. Functions as a private message

    :param data: activity streams format
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<error message>'}
    """
    environ.env.observer.emit('on_whisper', (data, activity))
    return ECodes.OK, None


@timeit(logger, 'on_invite')
def on_invite(data: dict, activity: Activity) -> (int, None):
    """
    invite a user to the a room this user is in

    :param data: activity streams format
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<error message>'}
    """
    environ.env.observer.emit('on_invite', (data, activity))
    return ECodes.OK, None


@timeit(logger, 'on_request_admin')
def on_request_admin(data: dict, activity: Activity) -> (int, None):
    """
    request the presence of an admin in the current room

    :param data: activity streams format
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<error message>'}
    """
    online_admins = environ.env.db.get_online_admins()
    if len(online_admins) == 0:
        return ECodes.NO_ADMIN_ONLINE, 'no admin is online'

    environ.env.observer.emit('on_request_admin', (data, activity))
    return ECodes.OK, None


@timeit(logger, 'on_create')
def on_create(data: dict, activity: Activity) -> (int, dict):
    """
    create a new room

    :param data: activity streams format, must include target.display_name (room name) and object.id (channel id)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': ECodes.OK, 'data': '<same AS as in the request, with addition of target.id (generated UUID
    for the new room>'}, else: {'status_code': 400, 'data': '<error message>'}
    """
    # generate a uuid for this room
    activity.target.id = str(uuid())
    activity.target.object_type = 'room'
    data['target']['id'] = activity.target.id
    data['target']['objectType'] = activity.target.object_type

    environ.env.observer.emit('on_create', (data, activity))

    if hasattr(activity, 'object') and hasattr(activity.object, 'attachments'):
        if activity.object.attachments is not None and len(activity.object.attachments) > 0:
            environ.env.observer.emit('on_set_acl', (data, activity))

    return ECodes.OK, data


@timeit(logger, 'on_set_acl')
def on_set_acl(data: dict, activity: Activity) -> (int, str):
    """
    change ACL of a room; only allowed if the user is the owner of the room

    :param data: activity streams, acls as attachments to object with object_type as acl name and content as acl value
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    environ.env.observer.emit('on_set_acl', (data, activity))
    return ECodes.OK, None


@timeit(logger, 'on_report')
def on_report(data: dict, activity: Activity) -> (int, str):
    """
    when a user reports a user based on a message

    :param data: activity streams format dict
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    environ.env.observer.emit('on_report', (data, activity))
    return ECodes.OK, None


@timeit(logger, 'on_get_acl')
def on_get_acl(data: dict, activity: Activity) -> (int, Union[str, dict]):
    """
    change ACL of a room; only allowed if the user is the owner of the room

    :param data: activity streams format
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<AS with acl as object.attachments>'}
    """
    if activity.target.object_type == ApiTargets.CHANNEL:
        acls = utils.get_acls_for_channel(activity.target.id)
    else:
        acls = utils.get_acls_for_room(activity.target.id)

    environ.env.observer.emit('on_get_acl', (data, activity))
    return ECodes.OK, utils.activity_for_get_acl(activity, acls)


@timeit(logger, 'on_status')
def on_status(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    change online status

    :param data: activity streams format, needs actor.id (user id), actor.summary (user name) and verb
    (online/invisible/offline)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    environ.env.observer.emit('on_status', (data, activity))
    return ECodes.OK, None


@timeit(logger, 'on_history')
def on_history(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    get the history of a room

    the 'updated' field is optional, and if set history since that point will be returned (only if dino has been
    configured with the history type 'unread' instead of 'top')

    :param data: activity streams format
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    room_id = activity.target.id
    user_id = activity.actor.id
    last_read = activity.updated

    messages = utils.get_history_for_room(room_id, user_id, last_read)

    environ.env.observer.emit('on_history', (data, activity))
    return ECodes.OK, utils.activity_for_history(activity, messages)


@timeit(logger, 'on_remove_room')
def on_remove_room(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    remove a room

    :param data: json dict in activity streams format
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    room_id = activity.target.id
    room_name = utils.get_room_name(room_id)
    channel_id = utils.get_channel_for_room(room_id)

    reason = None
    if hasattr(activity.object, 'content'):
        reason = activity.object.content

    remove_activity = utils.activity_for_remove_room(
            activity.actor.id, activity.actor.display_name, room_id, room_name, reason)

    environ.env.db.remove_room(channel_id, room_id)
    environ.env.emit('gn_room_removed', remove_activity, broadcast=True, include_self=True)
    environ.env.observer.emit('on_remove_room', (data, activity))

    return ECodes.OK, utils.activity_for_room_removed(activity, room_name)


@timeit(logger, 'on_join')
def on_join(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    join a room

    :param data: activity streams format, need actor.id (user id), target.id (user id), actor.summary (user name)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    room_id = activity.target.id
    user_id = activity.actor.id
    last_read = activity.updated

    messages = utils.get_history_for_room(room_id, user_id, last_read)
    owners = utils.get_owners_for_room(room_id)
    acls = utils.get_acls_for_room(room_id)
    users = utils.get_users_in_room(room_id, user_id=user_id, skip_cache=True)

    environ.env.observer.emit('on_join', (data, activity))
    return ECodes.OK, utils.activity_for_join(activity, acls, messages, owners, users)


@timeit(logger, 'on_users_in_room')
def on_users_in_room(data: dict, activity: Activity) -> (int, Union[dict, str]):
    """
    get a list of users in a room

    :param data: activity streams format, need target.id (room id)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok, {'status_code': ECodes.OK, 'data': <AS with users as object.attachments>}
    """
    # TODO: should people not in the room be able to list users in the room?
    room_id = activity.target.id
    user_id = activity.actor.id
    users = utils.get_users_in_room(room_id, user_id, skip_cache=True)

    environ.env.observer.emit('on_users_in_room', (data, activity))
    return ECodes.OK, utils.activity_for_users_in_room(activity, users)


@timeit(logger, 'on_list_rooms')
def on_list_rooms(data: dict, activity: Activity) -> (int, Union[dict, str]):
    """
    get a list of rooms

    :param data: activity streams format, needs actor.id (user id) and object.id (channel id)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok, {'status_code': ECodes.OK, 'data': <AS with rooms as object.attachments>}
    """
    channel_id = activity.object.url
    rooms = environ.env.db.rooms_for_channel(channel_id)

    roles = utils.get_user_roles(environ.env.session.get(SessionKeys.user_id.value))
    room_roles = roles['room']

    filtered_rooms = dict()
    for room_id, room_details in rooms.items():
        try:
            acls = utils.get_acls_in_room_for_action(room_id, ApiActions.LIST)
            is_valid, err_msg = validation.acl.validate_acl_for_action(
                    activity, ApiTargets.ROOM, ApiActions.LIST, acls, target_id=room_id, object_type='room')
        except Exception as e:
            # likely the room was deleted before client cache updated
            logger.warning('could not check acls for room %s in on_list_rooms: %s' % (room_id, str(e)))
            continue

        # if not allowed to join, don't show in list
        if not is_valid:
            continue

        room_details['roles'] = ''
        if room_id in room_roles.keys():
            room_details['roles'] = ','.join(room_roles[room_id])
        filtered_rooms[room_id] = room_details

    environ.env.observer.emit('on_list_rooms', (data, activity))
    activity_json = utils.activity_for_list_rooms(activity, filtered_rooms)

    rooms_with_acls = activity_json['object']['attachments']
    for room_info in rooms_with_acls:
        try:
            acls = utils.get_acls_for_room(room_info['id'])
        except NoSuchRoomException:
            # might have been removed recently and cache hasn't updated yet
            continue

        acl_activity = utils.activity_for_get_acl(activity, acls)
        room_info['attachments'] = acl_activity['object']['attachments']

    activity_json['object']['attachments'] = rooms_with_acls
    return ECodes.OK, activity_json


@timeit(logger, 'on_list_channels')
def on_list_channels(data: dict, activity: Activity) -> (int, Union[dict, str]):
    """
    get a list of channels

    :param data: activity streams format, needs actor.id (user id)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok, {'status_code': ECodes.OK, 'data': <AS with channels as object.attachments>}
    """
    channels = environ.env.db.get_channels()

    environ.env.observer.emit('on_list_channels', (data, activity))
    activity_json = utils.activity_for_list_channels(activity, channels)
    channels_with_acls = activity_json['object']['attachments']
    filtered_channels = list()

    for channel_info in channels_with_acls:
        channel_id = channel_info['id']
        list_acls = utils.get_acls_in_channel_for_action(channel_id, ApiActions.LIST)
        activity.object.url = channel_id
        activity.target.object_type = 'channel'
        is_valid, err_msg = validation.acl.validate_acl_for_action(
                activity, ApiTargets.CHANNEL, ApiActions.LIST, list_acls, target_id=channel_id, object_type='channel')

        # not allowed to list this channel
        if not is_valid:
            continue

        acls = utils.get_acls_for_channel(channel_id)
        acl_activity = utils.activity_for_get_acl(activity, acls)
        channel_info['attachments'] = acl_activity['object']['attachments']
        filtered_channels.append(channel_info)

    activity_json['object']['attachments'] = filtered_channels
    return ECodes.OK, activity_json


@timeit(logger, 'on_leave')
def on_leave(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    leave a room

    :param data: activity streams format, needs actor.id (user id), actor.summary (user name), target.id (room id)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    environ.env.observer.emit('on_leave', (data, activity))
    return ECodes.OK, None


@timeit(logger, 'on_disconnect')
def on_disconnect() -> (int, None):
    """
    when a client disconnects or the server no longer gets a ping response from the client

    :return json if ok, {'status_code': 200}
    """
    user_id = str(environ.env.session.get(SessionKeys.user_id.value))
    data = {
        'verb': 'disconnect',
        'actor': {
            'id': user_id
        }
    }
    if not environ.env.config.get(ConfigKeys.TESTING):
        if environ.env.connected_user_ids.get(user_id) == request.sid:
            del environ.env.connected_user_ids[user_id]

    activity = as_parser(data)
    environ.env.observer.emit('on_disconnect', (data, activity))
    return ECodes.OK, None
