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

import logging

from typing import Union
from uuid import uuid4 as uuid

from activitystreams.models.activity import Activity
from dino import environ
from dino import utils
from dino.config import SessionKeys
from dino.config import ApiTargets
from dino.config import ErrorCodes as ECodes
from dino.exceptions import NoSuchUserException

__author__ = 'Oscar Eriksson <oscar@thenetcircle.com>'

logger = logging.getLogger(__name__)


def connect() -> (int, None):
    """
    connect to the server

    :return: {'status_code': 200}
    """
    return ECodes.OK, None


def on_login(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    event sent directly after a connection has successfully been made, to get the user_id for this connection

    :param data: activity streams format, needs actor.id (user id) and actor.summary (user name)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    user_id = activity.actor.id
    environ.env.session[SessionKeys.user_id.value] = user_id

    if activity.actor.image is None:
        environ.env.session['image_url'] = ''
        environ.env.session[SessionKeys.image.value] = 'n'
    else:
        environ.env.session['image_url'] = activity.actor.image.url
        environ.env.session[SessionKeys.image.value] = 'y'

    utils.set_sid_for_user_id(user_id, environ.env.request.sid)
    user_name = environ.env.session.get(SessionKeys.user_name.value)
    private_room_id, _ = environ.env.db.get_private_room(user_id)

    if user_name is not None and len(user_name.strip()) > 0:
        print('setting name "%s" for user id "%s"' % (user_name, user_id))
        utils.set_name_for_user_id(user_id, user_name)

    utils.join_private_room(user_id, activity.actor.summary, private_room_id)
    return ECodes.OK, None


def on_delete(data: dict, activity: Activity):
    message_id = activity.object.id
    room_id = activity.target.id
    environ.env.storage.delete_message(message_id)
    environ.env.send(data, json=True, room=room_id, broadcast=True)
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

    environ.env.storage.store_message(activity)
    environ.env.send(data, json=True, room=room_id, broadcast=True)

    # TODO: update last reads in background thread, want to finish here as soon as possible and ack the user
    utils.update_last_reads(room_id)

    return ECodes.OK, data


def _kick_user(activity: Activity):
    kick_activity = {
        'actor': {
            'id': activity.actor.id,
            'summary': activity.actor.summary
        },
        'verb': 'kick',
        'object': {
            'id': activity.object.id,
            'summary': activity.object.summary
        },
        'target': {
            'url': environ.env.request.namespace
        }
    }

    # when banning globally, not target room is specified
    if activity.target is not None:
        kick_activity['target']['id'] = activity.target.id
        kick_activity['target']['displayName'] = activity.target.display_name

    environ.env.publish(kick_activity)


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
    room_id = activity.target.id
    kicked_id = activity.object.id
    ban_duration = activity.object.summary

    try:
        utils.ban_user(room_id, kicked_id, ban_duration)
    except NoSuchUserException as e:
        return ECodes.NO_SUCH_USER, 'could not find the specified user: %s' % str(e)

    _kick_user(activity)

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
    room_id = activity.target.id
    user_id = activity.object.id
    utils.kick_user(room_id, user_id)
    _kick_user(activity)
    return ECodes.OK, None


def on_whisper(data: dict, activity: Activity) -> (int, None):
    """
    whisper to another person in the same room, only that person will receive the event. Functions as a private message

    :param data: activity streams format
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<error message>'}
    """
    user_room = activity.target.id
    whisperer = activity.actor.id
    room_id = activity.actor.url
    channel_id = activity.object.url

    whisperer_name = utils.get_user_name_for(whisperer)
    channel_name = utils.get_channel_name(channel_id)
    room_name = utils.get_room_name(room_id)

    activity_json = utils.activity_for_whisper(whisperer, whisperer_name, room_id, room_name, channel_id, channel_name)
    environ.env.send('gn_whisper', activity_json, json=True, room=user_room)
    return ECodes.OK, None


def on_invite(data: dict, activity: Activity) -> (int, None):
    """
    invite a user to the a room this user is in

    :param data: activity streams format
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<error message>'}
    """
    user_id = activity.actor.id
    invitee = activity.target.id
    invite_room = activity.actor.url
    channel_id = activity.object.url

    channel_name = utils.get_channel_name(channel_id)
    invitee_name = utils.get_user_name_for(user_id)
    room_name = utils.get_room_name(invite_room)

    activity_json = utils.activity_for_invite(invitee, invitee_name, invite_room, room_name, channel_id, channel_name)
    environ.env.send('gn_invitation', activity_json, json=True, room=invitee)
    return ECodes.OK, None


def on_request_admin(data: dict, activity: Activity) -> (int, None):
    """
    request the presence of an admin in the current room

    :param data: activity streams format
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<error message>'}
    """
    user_id = activity.actor.id
    username = utils.get_user_name_for(user_id)
    message = activity.object.content
    room_id = activity.actor.url
    room_name = utils.get_room_name(room_id)
    channel_id = utils.get_channel_for_room(room_id)
    admin_room_id = utils.get_admin_room_for_channel(channel_id)

    if admin_room_id is None or len(admin_room_id.strip()) == 0:
        logger.error('no admin room found for channel "%s"' % channel_id)
        return ECodes.NO_ADMIN_ROOM_FOUND, 'no admin room for this channel'

    activity_json = utils.activity_for_request_admin(user_id, username, room_id, room_name, message)
    environ.env.emit('gn_request_admin', activity_json, json=True, broadcast=True, room=admin_room_id)
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

    room_name = activity.target.display_name
    room_id = activity.target.id
    channel_id = activity.object.url
    user_id = activity.actor.id

    user_name = utils.get_user_name_for(user_id)
    environ.env.db.create_room(room_name, room_id, channel_id, user_id, user_name)

    activity_json = utils.activity_for_create_room(activity)
    environ.env.emit('gn_room_created', activity_json, broadcast=True, json=True, include_self=True)

    return ECodes.OK, data


def on_set_acl(data: dict, activity: Activity) -> (int, str):
    """
    change ACL of a room; only allowed if the user is the owner of the room

    :param data: activity streams, acls as attachments to object with object_type as acl name and content as acl value
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    target_id = activity.target.id
    is_for_channel = activity.target.object_type == 'channel'

    acl_dict = dict()
    for acl in activity.object.attachments:
        # if the content is None, it means we're removing this ACL
        if acl.content is None:
            if is_for_channel:
                environ.env.db.delete_acl_in_channel_for_action(target_id, acl.object_type, acl.summary)
            else:
                environ.env.db.delete_acl_in_room_for_action(target_id, acl.object_type, acl.summary)
            continue

        if acl.summary not in acl_dict:
            acl_dict[acl.summary] = dict()
        acl_dict[acl.summary][acl.object_type] = acl.content

    # might have only removed acls, so could be size 0
    if len(acl_dict) > 0:
        for api_action, acls in acl_dict.items():
            if is_for_channel:
                environ.env.db.add_acls_in_channel_for_action(target_id, api_action, acls)
            else:
                environ.env.db.add_acls_in_room_for_action(target_id, api_action, acls)

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
    return ECodes.OK, utils.activity_for_get_acl(activity, acls)


def on_status(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    change online status

    :param data: activity streams format, needs actor.id (user id), actor.summary (user name) and verb
    (online/invisible/offline)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    # todo: leave rooms on invisible/offline?
    user_id = activity.actor.id
    user_name = environ.env.session.get(SessionKeys.user_name.value, None)
    status = activity.verb

    if status == 'online':
        environ.env.db.set_user_online(user_id)
        activity_json = utils.activity_for_connect(user_id, user_name)
        environ.env.emit('gn_user_connected', activity_json, broadcast=True, include_self=False)

    elif status == 'invisible':
        environ.env.db.set_user_invisible(user_id)
        activity_json = utils.activity_for_disconnect(user_id, user_name)
        environ.env.emit('gn_user_disconnected', activity_json, broadcast=True, include_self=False)

    elif status == 'offline':
        environ.env.db.set_user_offline(user_id)
        activity_json = utils.activity_for_disconnect(user_id, user_name)
        environ.env.emit('gn_user_disconnected', activity_json, broadcast=True, include_self=False)

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
    user_name = environ.env.session.get(SessionKeys.user_name.value)
    image = environ.env.session.get(SessionKeys.image.value, '')

    utils.set_sid_for_user_id(user_id, environ.env.request.sid)

    room_name = utils.get_room_name(room_id)
    utils.join_the_room(user_id, user_name, room_id, room_name)

    activity_json = utils.activity_for_user_joined(user_id, user_name, room_id, room_name, image)
    environ.env.emit('gn_user_joined', activity_json, room=room_id, broadcast=True, include_self=False)

    messages = utils.get_history_for_room(room_id, user_id, last_read)
    owners = utils.get_owners_for_room(room_id)
    acls = utils.get_acls_for_room(room_id)
    users = utils.get_users_in_room(room_id)

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
    return ECodes.OK, utils.activity_for_list_rooms(activity, rooms)


def on_list_channels(data: dict, activity: Activity) -> (int, Union[dict, str]):
    """
    get a list of channels

    :param data: activity streams format, needs actor.id (user id)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok, {'status_code': ECodes.OK, 'data': <AS with channels as object.attachments>}
    """
    channels = environ.env.db.get_channels()
    return ECodes.OK, utils.activity_for_list_channels(activity, channels)


def on_leave(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    leave a room

    :param data: activity streams format, needs actor.id (user id), actor.summary (user name), target.id (room id)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    #  todo: should handle invisibility here? don't broadcast leaving a room if invisible
    user_id = activity.actor.id
    user_name = environ.env.session.get(SessionKeys.user_name.value)
    room_id = activity.target.id

    room_name = utils.get_room_name(room_id)
    utils.remove_user_from_room(user_id, user_name, room_id)

    activity_left = utils.activity_for_leave(user_id, user_name, room_id, room_name)
    environ.env.emit('gn_user_left', activity_left, room=room_id, broadcast=True, include_self=False)

    return ECodes.OK, None


def on_disconnect() -> (int, None):
    """
    when a client disconnects or the server no longer gets a ping response from the client

    :return json if ok, {'status_code': 200}
    """
    # todo: only broadcast 'offline' status if current status is 'online' (i.e. don't broadcast if e.g. 'invisible')
    user_id = environ.env.session.get(SessionKeys.user_id.value)
    user_name = environ.env.session.get(SessionKeys.user_name.value)

    if user_id is None or not isinstance(user_id, str) or user_name is None:
        return ECodes.NO_USER_IN_SESSION, 'no user in session, not connected'

    private_room_id = environ.env.db.get_private_room(user_id)[0]
    environ.env.leave_room(private_room_id)
    rooms = environ.env.db.rooms_for_user(user_id)

    for room_id, room_name in rooms.items():
        utils.remove_user_from_room(user_id, user_name, room_id)
        environ.env.emit('gn_user_left', utils.activity_for_leave(user_id, user_name, room_id, room_name), room=room_id)

    environ.env.db.remove_current_rooms_for_user(user_id)
    environ.env.db.set_user_offline(user_id)

    activity_json = utils.activity_for_disconnect(user_id, user_name)
    environ.env.emit('gn_user_disconnected', activity_json, broadcast=True, include_self=False)
    return ECodes.OK, None
