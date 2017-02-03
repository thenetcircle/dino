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
from uuid import uuid4 as uuid

from activitystreams.models.activity import Activity
from activitystreams.models.defobject import DefObject
from activitystreams import parse as as_parser
from flask import request

from dino.config import ApiTargets
from dino.config import ConfigKeys
from dino.config import ErrorCodes as ECodes
from dino.hooks import *
from dino.config import ApiActions
from dino import validation

import logging

__author__ = 'Oscar Eriksson <oscar@thenetcircle.com>'

logger = logging.getLogger(__name__)


def connect() -> (int, None):
    """
    connect to the server

    :return: {'status_code': 200}
    """
    if not environ.env.config.get(ConfigKeys.TESTING):
        if request.remote_addr in environ.env.connected_ips:
            logger.error('a connection from IP %s already exists' % request.remote_addr)
            environ.env.disconnect()
            return ECodes.NOT_ALLOWED, 'a connection from this client already exists'
        else:
            environ.env.connected_ips[request.remote_addr] = request.sid
            environ.env.observer.emit('on_connect', (None, None))
    return ECodes.OK, None


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


def on_delete(data: dict, activity: Activity):
    environ.env.observer.emit('on_delete', (data, activity))
    return ECodes.OK, None


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

    activity.actor.summary = environ.env.session.get(SessionKeys.user_name.value)
    data['target']['displayName'] = utils.b64e(activity.target.display_name)
    data['object']['displayName'] = utils.b64e(activity.object.display_name)

    environ.env.observer.emit('on_message', (data, activity))
    return ECodes.OK, data


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
    environ.env.observer.emit('on_kick', (data, activity))
    return ECodes.OK, None


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


def on_whisper(data: dict, activity: Activity) -> (int, None):
    """
    whisper to another person in the same room, only that person will receive the event. Functions as a private message

    :param data: activity streams format
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<error message>'}
    """
    environ.env.observer.emit('on_whisper', (data, activity))
    return ECodes.OK, None


def on_invite(data: dict, activity: Activity) -> (int, None):
    """
    invite a user to the a room this user is in

    :param data: activity streams format
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<error message>'}
    """
    environ.env.observer.emit('on_invite', (data, activity))
    return ECodes.OK, None


def on_request_admin(data: dict, activity: Activity) -> (int, None):
    """
    request the presence of an admin in the current room

    :param data: activity streams format
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<error message>'}
    """
    environ.env.observer.emit('on_request_admin', (data, activity))
    return ECodes.OK, None


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


def on_set_acl(data: dict, activity: Activity) -> (int, str):
    """
    change ACL of a room; only allowed if the user is the owner of the room

    :param data: activity streams, acls as attachments to object with object_type as acl name and content as acl value
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    environ.env.observer.emit('on_set_acl', (data, activity))
    return ECodes.OK, None


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


def on_join(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    join a room

    :param data: activity streams format, need actor.id (user id), target.id (user id), actor.summary (user name)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    # todo: how to deal with invisibility here?
    room_id = activity.target.id
    user_id = activity.actor.id
    last_read = activity.updated

    messages = utils.get_history_for_room(room_id, user_id, last_read)
    owners = utils.get_owners_for_room(room_id)
    acls = utils.get_acls_for_room(room_id)
    users = utils.get_users_in_room(room_id)

    environ.env.observer.emit('on_join', (data, activity))
    return ECodes.OK, utils.activity_for_join(activity, acls, messages, owners, users)


def on_users_in_room(data: dict, activity: Activity) -> (int, Union[dict, str]):
    """
    get a list of users in a room

    :param data: activity streams format, need target.id (room id)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok, {'status_code': ECodes.OK, 'data': <AS with users as object.attachments>}
    """
    # TODO: should people not in the room be able to list users in the room?
    room_id = activity.target.id
    users = utils.get_users_in_room(room_id)

    environ.env.observer.emit('on_users_in_room', (data, activity))
    return ECodes.OK, utils.activity_for_users_in_room(activity, users)


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
        acls = utils.get_acls_in_room_for_action(room_id, ApiActions.LIST)
        is_valid, err_msg = validation.acl.validate_acl_for_action(
                activity, ApiTargets.ROOM, ApiActions.LIST, acls, target_id=room_id, object_type='room')

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
        acls = utils.get_acls_for_room(room_info['id'])
        acl_activity = utils.activity_for_get_acl(activity, acls)
        room_info['attachments'] = acl_activity['object']['attachments']

    activity_json['object']['attachments'] = rooms_with_acls
    return ECodes.OK, activity_json


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

    for channel_info in channels_with_acls:
        acls = utils.get_acls_for_channel(channel_info['id'])
        acl_activity = utils.activity_for_get_acl(activity, acls)
        channel_info['attachments'] = acl_activity['object']['attachments']

    activity_json['object']['attachments'] = channels_with_acls
    return ECodes.OK, activity_json


def on_leave(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    leave a room

    :param data: activity streams format, needs actor.id (user id), actor.summary (user name), target.id (room id)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    environ.env.observer.emit('on_leave', (data, activity))
    return ECodes.OK, None


def on_disconnect() -> (int, None):
    """
    when a client disconnects or the server no longer gets a ping response from the client

    :return json if ok, {'status_code': 200}
    """
    data = {
        'verb': 'disconnect',
        'actor': {
            'id': str(environ.env.session.get(SessionKeys.user_id.value))
        }
    }
    if not environ.env.config.get(ConfigKeys.TESTING):
        if environ.env.connected_ips.get(request.remote_addr) == request.sid:
            del environ.env.connected_ips[request.remote_addr]

    activity = as_parser(data)
    environ.env.observer.emit('on_disconnect', (data, activity))
    return ECodes.OK, None
