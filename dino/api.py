import time
from datetime import datetime
from typing import Union
from uuid import uuid4 as uuid

import activitystreams as as_parser
from activitystreams.models.activity import Activity
from dino import environ
from dino import utils
from dino import validator
from dino.config import SessionKeys
from dino.validator import Validator

__author__ = 'Oscar Eriksson <oscar@thenetcircle.com>'

logger = environ.env.logger


def on_add_owner(data: dict) -> (int, Union[str, None]):
    return 200, None


def on_connect() -> (int, None):
    """
    connect to the server

    :return: {'status_code': 200}
    """
    return 200, None


def on_login(data: dict) -> (int, Union[str, None]):
    """
    event sent directly after a connection has successfully been made, to get the user_id for this connection

    example activity with required parameters:

    {
        actor: {
            id: '1234',
            summary: 'joe',
            image: {
                url: 'http://some-url.com/image.jpg',
                width: '120',
                height: '120'
            }
            attachments: [
                {
                    objectType: 'gender',
                    content: 'm'
                },
                {
                    objectType: 'age',
                    content: '28'
                },
                {
                    objectType: 'membership',
                    content: '1'
                },
                {
                    objectType: 'fake_checked',
                    content: 'y'
                },
                {
                    objectType: 'has_webcam',
                    content: 'n'
                },
                {
                    objectType: 'country',
                    content: 'de'
                },
                {
                    objectType: 'city',
                    content: 'Berlin'
                },
                {
                    objectType: 'token',
                    content: '66968fad-2336-40c9-bc6d-0ecbcd91f4da'
                }
            ]
        },
        verb: 'login'
    }

    :param data: activity streams format, needs actor.id (user id) and actor.summary (user name)
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    # todo: check environ.env.redis if any queued notifications, then environ.env.emit and clear?

    activity = as_parser.parse(data)
    user_id = activity.actor.id

    is_banned, duration = utils.is_banned(user_id)
    if is_banned:
        return 400, 'user is banned from chatting for: %ss' % duration

    environ.env.session[SessionKeys.user_id.value] = user_id

    if activity.actor.attachments is not None:
        for attachment in activity.actor.attachments:
            environ.env.session[attachment.object_type] = attachment.content

    if SessionKeys.token.value not in environ.env.session:
        return 400, 'no token in session'

    token = environ.env.session.get(SessionKeys.token.value)
    is_valid, error_msg, session = validator.validate_login(user_id, token)

    if not is_valid:
        return 400, error_msg

    for session_key, session_value in session.items():
        environ.env.session[session_key] = session_value

    if activity.actor.image is None:
        environ.env.session['image_url'] = ''
        environ.env.session[SessionKeys.image.value] = 'n'
    else:
        environ.env.session['image_url'] = activity.actor.image.url
        environ.env.session[SessionKeys.image.value] = 'y'

    utils.set_sid_for_user_id(user_id, environ.env.request.sid)

    environ.env.join_room(user_id)
    return 200, None


def on_message(data):
    """
    send any kind of message/event to a target user/group

    :param data: activity streams format, must include at least target.id (room/user id)
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<same AS as client sent, plus timestamp>'}
    """
    # let the server determine the publishing time of the event, not the client
    data['published'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%SZ')
    data['id'] = str(uuid())
    activity = as_parser.parse(data)

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    target = activity.target.id
    if target is None or target == '':
        return 400, 'no target specified when sending message'

    if not environ.env.storage.room_exists(target):
        return 400, 'room %s does not exist' % target

    # TODO: keep these in utils, make storage abstract, e.g. environ.env.storage.room_contains(room_id, some_value)
    if not utils.is_user_in_room(activity.actor.id, target):
        return 400, 'user not in room, not allowed to send'

    environ.env.storage.store_message(activity)
    environ.env.send(data, json=True, room=target, broadcast=True)

    return 200, data


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


def on_ban(data):
    """
    ban a user from a room (if user is an owner)

    target.id: the uuid of the room that the user is in
    target.displayName: the room name
    object.id: the id of the user to kick
    object.content: the name of the user to kick
    object.summary: the ban time, e.g.
    actor.id: the id of the kicker
    actor.content: the name of the kicker

    :param data:
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<error message>'}
    """
    activity = as_parser.parse(data)

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    room_id = activity.target.id
    user_id = activity.actor.id
    kicked_id = activity.object.id
    ban_duration = activity.object.summary

    is_global_ban = room_id is None or room_id == ''

    if kicked_id is None or kicked_id.strip() == '':
        return 400, 'got blank user id, can not ban'

    if not environ.env.storage.room_exists(room_id):
        return 400, 'no room with id "%s" exists' % room_id

    if not is_global_ban:
        if not utils.is_owner(room_id, user_id):
            return 400, 'only owners can ban'
    elif not utils.is_admin(user_id):
            return 400, 'only admins can do global bans'

    utils.ban_user(room_id, kicked_id, ban_duration)
    _kick_user(activity)

    return 200, None


def on_kick(data):
    """
    kick a user from a room (if user is an owner)

    target.id: the uuid of the room that the user is in
    target.displayName: the room name
    object.id: the id of the user to kick
    object.content: the name of the user to kick
    actor.id: the id of the kicker
    actor.content: the name of the kicker

    :param data:
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<error message>'}
    """
    activity = as_parser.parse(data)

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    room_id = activity.target.id
    user_id = activity.target.display_name

    if room_id is None or room_id.strip() == '':
        return 400, 'got blank room id, can not kick'

    if user_id is None or user_id.strip() == '':
        return 400, 'got blank user id, can not kick'

    if not environ.env.storage.room_exists(room_id):
        return 400, 'no room with id "%s" exists' % room_id

    if not utils.is_owner(room_id, user_id):
        return 400, 'only owners can kick'

    _kick_user(activity)

    return 200, None


def on_create(data):
    """
    create a new room

    :param data: activity streams format, must include at least target.id (room id)
    :return: if ok: {'status_code': 200, 'data': '<same AS as in the request, with addition of target.id (generated UUID
    for the new room>'}, else: {'status_code': 400, 'data': '<error message>'}
    """
    activity = as_parser.parse(data)

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    target = activity.target.display_name

    if target is None or target.strip() == '':
        return 400, 'got blank room name, can not create'

    if environ.env.storage.room_name_exists(target):
        return 400, 'a room with that name already exists'

    activity.target.id = str(uuid())
    environ.env.storage.create_room(activity)

    activity_json = utils.activity_for_create_room(activity.target.id, target)
    environ.env.emit('gn_room_created', activity_json, broadcast=True, json=True, include_self=True)

    return 200, data


def on_set_acl(data: dict) -> (int, str):
    """
    change ACL of a room; only allowed if the user is the owner of the room

    :param data: activity streams, acls as attachments to object with object_type as acl name and content as acl value
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    activity = as_parser.parse(data)
    user_id = activity.actor.id
    room_id = activity.target.id

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    if not utils.is_owner(room_id, user_id):
        return 400, 'user not a owner of room'

    # validate all acls before actually changing anything
    acls = activity.object.attachments
    for acl in acls:
        if acl.object_type not in Validator.ACL_MATCHERS.keys():
            return 400, 'invalid acl type "%s"' % acl.object_type
        if not validator.is_acl_valid(acl.object_type, acl.content):
            return 400, 'invalid acl value "%s" for type "%s"' % (acl.content, acl.object_type)

    acl_dict = dict()
    for acl in acls:
        # if the content is None, it means we're removing this ACL
        if acl.content is None:
            environ.env.storage.delete_acl(room_id, acl.object_type)
            continue

        acl_dict[acl.object_type] = acl.content

    # might have only removed acls, so could be size 0
    if len(acl_dict) > 0:
        environ.env.storage.add_acls(room_id, acl_dict)

    return 200, None


def on_get_acl(data: dict) -> (int, Union[str, dict]):
    """
    change ACL of a room; only allowed if the user is the owner of the room

    :param data:
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<AS with acl as object.attachments>'}
    """
    activity = as_parser.parse(data)
    room_id = activity.target.id
    activity.target.display_name = environ.env.storage.get_room_name(room_id)

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    acls = utils.get_acls_for_room(room_id)
    return 200, utils.activity_for_get_acl(activity, acls)


def on_status(data: dict) -> (int, Union[str, None]):
    """
    change online status

    example activity:

    {
        actor: {
            id: '1234'
        },
        verb: 'online/invisible/offline'
    }

    :param data: activity streams format, needs actor.id (user id), actor.summary (user name) and verb
    (online/invisible/offline)
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    # todo: leave rooms on invisible/offline?

    activity = as_parser.parse(data)
    user_id = activity.actor.id
    user_name = environ.env.session.get(SessionKeys.user_name.value, None)
    status = activity.verb

    if user_name is None:
        return 400, 'no user name in session'

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    if status == 'online':
        environ.env.storage.set_user_online(user_id)
        activity_json = utils.activity_for_connect(user_id, user_name)
        environ.env.emit('gn_user_connected', activity_json, broadcast=True, include_self=False)

    elif status == 'invisible':
        environ.env.storage.set_user_invisible(user_id)
        activity_json = utils.activity_for_disconnect(user_id, user_name)
        environ.env.emit('gn_user_disconnected', activity_json, broadcast=True, include_self=False)

    elif status == 'offline':
        environ.env.storage.set_user_offline(user_id)
        activity_json = utils.activity_for_disconnect(user_id, user_name)
        environ.env.emit('gn_user_disconnected', activity_json, broadcast=True, include_self=False)

    else:
        return 400, 'invalid status %s' % str(status)

    return 200, None


def on_history(data: dict) -> (int, Union[str, None]):
    """
    example activity:

    {
        actor: {
            id: '1234'
        },
        verb: 'history',
        target: {
            id: 'd69dbfd8-95a2-4dc5-b051-8ef050e2667e'
        }
    }

    :param data: activity streams format, need actor.id (user id), target.id (user id)
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """

    activity = as_parser.parse(data)
    room_id = activity.target.id

    if room_id is None or room_id.strip() == '':
        return 400, 'invalid target id'

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    is_valid, error_msg = validator.validate_acl(activity)
    if not is_valid:
        return 400, error_msg

    messages = utils.get_history_for_room(room_id, 10)
    return 200, utils.activity_for_history(activity, messages)


def on_join(data: dict) -> (int, Union[str, None]):
    """
    example activity:

    {
        actor: {
            id: '1234',
            summary: 'joe'
        },
        verb: 'join',
        target: {
            id: 'd69dbfd8-95a2-4dc5-b051-8ef050e2667e'
        }
    }

    :param data: activity streams format, need actor.id (user id), target.id (user id), actor.summary (user name)
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    # todo: how to deal with invisibility here?

    activity = as_parser.parse(data)
    room_id = activity.target.id
    user_id = activity.actor.id
    user_name = environ.env.session.get(SessionKeys.user_name.value)
    image = environ.env.session.get(SessionKeys.image.value, '')

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    is_valid, error_msg = validator.validate_acl(activity)
    if not is_valid:
        return 400, error_msg

    is_banned, duration = utils.is_banned(user_id, room_id=room_id)
    if is_banned:
        return 400, 'user is banned from joining room for: %ss' % duration

    room_name = environ.env.storage.get_room_name(room_id)
    utils.join_the_room(user_id, user_name, room_id, room_name)

    activity_json = utils.activity_for_user_joined(user_id, user_name, room_id, room_name, image)
    environ.env.emit('gn_user_joined', activity_json, room=room_id, broadcast=True, include_self=False)

    messages = utils.get_history_for_room(room_id, 10)
    owners = utils.get_owners_for_room(room_id)
    acls = utils.get_acls_for_room(room_id)
    users = utils.get_users_in_room(room_id)

    return 200, utils.activity_for_join(activity, acls, messages, owners, users)


def on_users_in_room(data: dict) -> (int, Union[dict, str]):
    """
    get a list of users in a room

    :param data: activity streams format, need target.id (room id)
    :return: if ok, {'status_code': 200, 'data': <AS with users as object.attachments>}
    """
    activity = as_parser.parse(data)
    room_id = activity.target.id

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    users = utils.get_users_in_room(room_id)

    return 200, utils.activity_for_users_in_room(activity, users)


def on_list_rooms(data: dict) -> (int, Union[dict, str]):
    """
    get a list of rooms

    :param data: activity streams format, needs actor.id (user id), in the future should be able to specify sub-set of
    rooms, e.g. 'rooms in berlin'
    :return: if ok, {'status_code': 200, 'data': <AS with rooms as object.attachments>}
    """
    activity = as_parser.parse(data)

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    all_rooms = environ.env.storage.get_all_rooms()

    rooms = list()
    for room in all_rooms:
        rooms.append((room['room_id'], room['room_name']))

    return 200, utils.activity_for_list_rooms(activity, rooms)


def on_leave(data: dict) -> (int, Union[str, None]):
    """
    leave a room

    :param data: activity streams format, needs actor.id (user id), actor.summary (user name), target.id (room id)
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    #  todo: should handle invisibility here? don't broadcast leaving a room if invisible

    activity = as_parser.parse(data)

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    if not hasattr(activity, 'target') or not hasattr(activity.target, 'id'):
        return 400, 'room_id is None when trying to leave room'

    user_id = activity.actor.id
    user_name = environ.env.session.get(SessionKeys.user_name.value)
    room_id = activity.target.id

    room_name = environ.env.storage.get_room_name(room_id)
    utils.remove_user_from_room(user_id, user_name, room_id)

    activity_left = utils.activity_for_leave(user_id, user_name, room_id, room_name)
    environ.env.emit('gn_user_left', activity_left, room=room_id, broadcast=True, include_self=False)

    return 200, None


def on_disconnect() -> (int, None):
    """
    when a client disconnects or the server no longer gets a ping response from the client

    :return json if ok, {'status_code': 200}
    """
    # todo: only broadcast 'offline' status if current status is 'online' (i.e. don't broadcast if e.g. 'invisible')
    user_id = environ.env.session.get(SessionKeys.user_id.value, None)
    user_name = environ.env.session.get(SessionKeys.user_name.value, None)

    if user_id is None or user_name is None:
        return 400, 'no user in session, not connected'

    environ.env.leave_room(user_id)
    rooms = environ.env.storage.get_all_rooms(user_id=user_id)

    for room in rooms:
        room_id, room_name = room['room_id'], room['room_name']
        utils.remove_user_from_room(user_id, user_name, room_id)
        environ.env.send(utils.activity_for_leave(user_id, user_name, room_id, room_name), room=room_name)

    environ.env.storage.remove_current_rooms_for_user(user_id)
    environ.env.storage.set_user_offline(user_id)

    activity_json = utils.activity_for_disconnect(user_id, user_name)
    environ.env.emit('gn_user_disconnected', activity_json, broadcast=True, include_self=False)
    return 200, None
