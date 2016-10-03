import activitystreams as as_parser
import time

from datetime import datetime
from typing import Union
from uuid import uuid4 as uuid

from gridchat import utils
from gridchat import validator
from gridchat.validator import Validator
from gridchat.env import env
from gridchat.env import SessionKeys
from gridchat import rkeys

__author__ = 'Oscar Eriksson <oscar@thenetcircle.com>'


def on_add_owner(data: dict) -> (int, Union[str, None]):
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
    # todo: check env.redis if any queued notifications, then env.emit and clear?

    activity = as_parser.parse(data)
    user_id = activity.actor.id

    env.session[SessionKeys.user_id.value] = user_id
    env.session[SessionKeys.user_name.value] = activity.actor.summary

    if activity.actor.image is None:
        env.session['image_url'] = ''
        env.session[SessionKeys.image.value] = 'n'
    else:
        env.session['image_url'] = activity.actor.image.url
        env.session[SessionKeys.image.value] = 'y'

    if activity.actor.attachments is not None:
        for attachment in activity.actor.attachments:
            env.session[attachment.object_type] = attachment.content

    is_valid, error_msg = validator.validate_login()

    if not is_valid:
        return 400, error_msg

    env.join_room(user_id)
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

    if not env.redis.hexists(rkeys.rooms(), target):
        return 400, 'room %s does not exist' % target

    if not utils.is_user_in_room(activity.actor.id, target):
        return 400, 'user not in room, not allowed to send'

    env.redis.lpush(rkeys.room_history(target), '%s,%s,%s,%s' % (
        activity.id, activity.published, env.session.get(SessionKeys.user_name.value), activity.object.content))
    env.redis.ltrim(rkeys.room_history(target), 0, 200)
    env.send(data, json=True, room=target, broadcast=True)

    return 200, data


def on_create(data):
    """
    create a new room

    :param data: activity streams format, must include at least target.id (room id)
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<error message>'}
    """
    # let the server determine the publishing time of the event, not the client
    activity = as_parser.parse(data)

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    target = activity.target.display_name

    if target is None or target.strip() == '':
        return 400, 'got blank room name, can not create'

    cleaned = set()
    for room_name in env.redis.hvals(rkeys.rooms()):
        cleaned.add(str(room_name, 'utf-8'))

    if target in cleaned:
        return 400, 'a room with that name already exists'

    room_id = str(uuid())
    env.redis.set(rkeys.room_name_for_id(room_id), target)
    env.redis.hset(rkeys.room_owners(room_id), activity.actor.id, env.session.get(SessionKeys.user_name.value))
    env.redis.hset(rkeys.rooms(), room_id, target)
    env.emit('gn_room_created', utils.activity_for_create_room(room_id, target), broadcast=True, json=True, include_self=True)

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
            env.redis.hdel(rkeys.room_acl(room_id), acl.object_type)
            continue

        acl_dict[acl.object_type] = acl.content

    # might have only removed acls, so could be size 0
    if len(acl_dict) > 0:
        env.redis.hmset(rkeys.room_acl(room_id), acl_dict)

    return 200, None


def on_get_acl(data: dict) -> (int, Union[str, dict]):
    """
    change ACL of a room; only allowed if the user is the owner of the room

    :param data:
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<AS with acl as object.attachments>'}
    """
    activity = as_parser.parse(data)
    room_id = activity.target.id
    activity.target.display_name = utils.get_room_name(env.redis, room_id)

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
            id: '1234',
            summary: 'joe'
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
    user_name = activity.actor.summary
    status = activity.verb

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    if status == 'online':
        utils.set_user_online(env.redis, user_id)
        env.emit('gn_user_connected', utils.activity_for_connect(user_id, user_name), broadcast=True, include_self=False)

    elif status == 'invisible':
        utils.set_user_invisible(env.redis, user_id)
        env.emit('gn_user_disconnected', utils.activity_for_disconnect(user_id, user_name), broadcast=True, include_self=False)

    elif status == 'offline':
        utils.set_user_offline(env.redis, user_id)
        env.emit('gn_user_disconnected', utils.activity_for_disconnect(user_id, user_name), broadcast=True, include_self=False)

    else:
        # ignore
        pass

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
    user_name = env.session.get(SessionKeys.user_name.value)
    image = env.session.get(SessionKeys.image.value, '')

    is_valid, error_msg = validator.validate_request(activity)
    if not is_valid:
        return 400, error_msg

    is_valid, error_msg = validator.validate_acl(activity)
    if not is_valid:
        return 400, error_msg

    room_name = utils.get_room_name(env.redis, room_id)
    utils.join_the_room(env.redis, user_id, user_name, room_id, room_name)

    env.emit('gn_user_joined', utils.activity_for_user_joined(user_id, user_name, room_id, room_name, image),
             room=room_id, broadcast=True, include_self=False)

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

    all_rooms = env.redis.hgetall(rkeys.rooms())

    rooms = list()
    for room_id, room_name in all_rooms.items():
        rooms.append((str(room_id, 'utf-8'), str(room_name, 'utf-8')))

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
    user_name = env.session.get(SessionKeys.user_name.value)
    room_id = activity.target.id

    room_name = utils.get_room_name(env.redis, room_id)
    utils.remove_user_from_room(env.redis, user_id, user_name, room_id)

    activity_left = utils.activity_for_leave(user_id, user_name, room_id, room_name)
    env.emit('gn_user_left', activity_left, room=room_id, broadcast=True, include_self=False)

    return 200, None


def on_disconnect() -> (int, None):
    """
    when a client disconnects or the server no longer gets a ping response from the client

    :return json if ok, {'status_code': 200}
    """
    # todo: only broadcast 'offline' status if current status is 'online' (i.e. don't broadcast if e.g. 'invisible')
    user_id = env.session.get(SessionKeys.user_id.value, None)
    user_name = env.session.get(SessionKeys.user_name.value, None)

    if user_id is None or user_name is None:
        return 400, 'no user in session, not connected'

    env.leave_room(user_id)
    rooms = env.redis.smembers(rkeys.rooms_for_user(user_id))

    for room in rooms:
        room_id, room_name = room.decode('utf-8').split(':', 1)
        utils.remove_user_from_room(env.redis, user_id, user_name, room_id)
        env.send(utils.activity_for_leave(user_id, user_name, room_id, room_name), room=room_name)

    env.redis.delete(rkeys.rooms_for_user(user_id))
    utils.set_user_offline(env.redis, user_id)

    env.emit('gn_user_disconnected', utils.activity_for_disconnect(user_id, user_name), broadcast=True, include_self=False)
    return 200, None
