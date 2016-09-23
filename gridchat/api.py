import activitystreams as as_parser
import time

from flask_socketio import send, emit
from datetime import datetime
from pprint import pprint
from typing import Union

from gridchat.utils import *
from gridchat.validator import *
from gridchat.env import env, ConfigKeys

redis = env.config.get(ConfigKeys.REDIS)

__author__ = 'Oscar Eriksson <oscar@thenetcircle.com>'


def user_connection(data: dict) -> (int, str):
    """
    event sent directly after a connection has successfully been made, to get the user_id for this connection

    example activity with required parameters:

    {
        actor: {
            id: '1234',
            summary: 'joe',
            image: {
                url: 'http://some-url.com/image.jpg',
                width: '120px',
                height: '120px'
            }
            attachments: [
                {
                    object_type: 'gender',
                    content: 'm'
                },
                {
                    object_type: 'age',
                    content: '28'
                },
                {
                    object_type: 'membership',
                    content: '1'
                },
                {
                    object_type: 'fake_checked',
                    content: 'yes'
                },
                {
                    object_type: 'has_webcam',
                    content: 'no'
                },
                {
                    object_type: 'country',
                    content: 'Germany'
                },
                {
                    object_type: 'city',
                    content: 'Berlin'
                },
                {
                    object_type: 'token',
                    content: '66968fad-2336-40c9-bc6d-0ecbcd91f4da'
                }
            ]
        },
        verb: 'login'
    }

    :param data: activity streams format, needs actor.id (user id) and actor.summary (user name)
    :return: json if ok, {'status_code': 200, 'data': 'Connected'}
    """
    # todo: check redis if any queued notifications, then emit and clear?

    activity = as_parser.parse(data)
    user_id = activity.actor.id

    session['user_id'] = user_id
    session['user_name'] = activity.actor.summary

    if activity.actor.image is not None:
        session['image'] = activity.actor.image.url

    if activity.actor.attachments is not None:
        for attachment in activity.actor.attachments:
            session[attachment.object_type] = attachment.content

    is_valid, error_msg = validate()

    if not is_valid:
        return 400, error_msg

    join_room(user_id)
    return 200, 'Connected'


def on_message(data):
    """
    send any kind of message/event to a target user/group

    :param data: activity streams format, bust include at least target.id (room/user id)
    :return: json if ok, {'status_code': 200, 'data': 'Sent'}
    """
    pprint(data)
    data['published'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%SZ')
    activity = as_parser.parse(data)

    is_valid, error_msg = validate_request(activity)
    if not is_valid:
        return 400, error_msg

    target = activity.target.id
    send(data, json=True, room=target)

    # todo: use activity streams, say which message was delivered successfully
    return 200, data


def on_set_acl(data: dict) -> (int, str):
    """
    change ACL of a room; only allowed if the user is the owner of the room

    :param data: activity streams, acls as attachments to object with object_type as acl name and content as acl value
    :return (int, str): (status_code, error_message/None)
    """
    activity = as_parser.parse(data)
    user_id = activity.actor.id
    room_id = activity.target.id

    is_valid, error_msg = validate_request(activity)
    if not is_valid:
        return 400, error_msg

    if not redis.sismember(rkeys.room_owners(room_id), user_id):
        return 400, 'user not a owner of room'

    # validate all acls before actually changing anything
    acls = activity.object.attachments
    for acl in acls:
        if acl.object_type not in Validator.USER_KEYS.keys():
            return 400, 'invalid acl type "%s"' % acl.object_type
        if not is_acl_valid(acl.object_type, acl.content):
            return 400, 'invalid acl value "%s" for type "%s"' % (acl.content, acl.object_type)

    acl_dict = dict()
    for acl in acls:
        # if the content is None, it means we're removing this ACL
        if acl.content is None:
            redis.hdel(rkeys.room_acl(room_id), acl.object_type)
            continue

        acl_dict[acl.object_type] = acl.content

    # might have only removed acls, so could be size 0
    if len(acl_dict) > 0:
        redis.hmset(rkeys.room_acl(room_id), acl_dict)

    return 200, None


def on_get_acl(data: dict) -> (int, Union[str, dict]):
    """
    change ACL of a room; only allowed if the user is the owner of the room

    :param data:
    :return:
    """
    activity = as_parser.parse(data)
    room_id = activity.target.id
    activity.target.display_name = get_room_name(redis, room_id)

    is_valid, error_msg = validate_request(activity)
    if not is_valid:
        return 400, error_msg

    values = redis.hgetall(rkeys.room_acl(room_id))
    return 200, activity_for_get_acl(activity, values)


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
    :return: json if ok, {'status_code': 200}
    """
    # todo: leave rooms on invisible/offline?

    activity = as_parser.parse(data)
    user_id = activity.actor.id
    user_name = activity.actor.summary
    status = activity.verb

    is_valid, error_msg = validate_request(activity)
    if not is_valid:
        return 400, error_msg

    if status == 'online':
        set_user_online(redis, user_id)
        emit('gn_user_connected', activity_for_connect(user_id, user_name), broadcast=True, include_self=False)

    elif status == 'invisible':
        set_user_invisible(redis, user_id)
        emit('gn_user_disconnected', activity_for_disconnect(user_id, user_name), broadcast=True, include_self=False)

    elif status == 'offline':
        set_user_offline(redis, user_id)
        emit('gn_user_disconnected', activity_for_disconnect(user_id, user_name), broadcast=True, include_self=False)

    else:
        # ignore
        pass

    return 200, None


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
    :return: json if okay, {'status_code': 200, 'users': <users in the room, format: 'user_id:user_name'>}
    """
    # todo: how to deal with invisibility here?

    pprint(data)
    activity = as_parser.parse(data)
    room_id = activity.target.id
    user_id = activity.actor.id
    user_name = activity.actor.summary
    image = session.get('image', '')

    is_valid, error_msg = validate_request(activity)
    if not is_valid:
        return 400, error_msg

    room_name = get_room_name(redis, room_id)
    join_the_room(redis, user_id, user_name, room_id, room_name)

    emit('gn_user_joined', activity_for_join(user_id, user_name, room_id, room_name, image),
         room=room_id, broadcast=True, include_self=False)

    return 200, None


def on_users_in_room(data: dict) -> (int, Union[dict, str]):
    """
    get a list of users in a room

    :param data: activity streams format, need target.id (room id)
    :return: json if ok, {'status_code': 200, 'users': <users in the room, format: 'user_id:user_name'>}
    """
    activity = as_parser.parse(data)
    room_id = activity.target.id

    is_valid, error_msg = validate_request(activity)
    if not is_valid:
        return 400, error_msg

    users_in_room = redis.smembers(rkeys.users_in_room(room_id))
    users = list()
    for user in users_in_room:
        users.append(str(user.decode('utf-8')))

    # todo: use activity streams
    return 200, users


def on_list_rooms(data: dict) -> (int, Union[dict, str]):
    """
    get a list of rooms

    :param data: activity streams format, needs actor.id (user id), in the future should be able to specify sub-set of
    rooms, e.g. 'rooms in berlin'
    :return: json if ok, {'status_code': 200, 'rooms': <list of rooms, format: 'room_id:room_name'>}
    """
    activity = as_parser.parse(data)

    is_valid, error_msg = validate_request(activity)
    if not is_valid:
        return 400, error_msg

    all_rooms = redis.smembers(rkeys.rooms())

    rooms = list()
    for room in all_rooms:
        rooms.append(str(room.decode('utf-8')))

    # todo: user activity streams
    return 200, rooms


def on_leave(data: dict) -> (int, Union[str, None]):
    """
    leave a room

    :param data: activity streams format, needs actor.id (user id), actor.summary (user name), target.id (room id)
    :return: json if ok, {'status_code': 200, 'data': 'Left'}
    """
    #  todo: should handle invisibility here? don't broadcast leaving a room if invisible

    activity = as_parser.parse(data)
    user_id = activity.actor.id
    user_name = activity.actor.summary
    room_id = activity.target.id

    is_valid, error_msg = validate_request(activity)
    if not is_valid:
        return 400, error_msg

    if room_id is None:
        return 400, 'warning: room_id is None when trying to leave room'

    room_name = get_room_name(redis, room_id)
    remove_user_from_room(redis, user_id, user_name, room_id)

    activity_left = activity_for_leave(user_id, user_name, room_id, room_name)
    emit('gn_user_left', activity_left, room=room_id, broadcast=True, include_self=False)

    return 200, None


def on_disconnect() -> (int, None):
    """
    when a client disconnects or the server no longer gets a ping response from the client

    :return json if ok, {'status_code': 200, 'data': 'Disconnected'}
    """
    # todo: only broadcast 'offline' status if current status is 'online' (i.e. don't broadcast if e.g. 'invisible')

    user_id = session['user_id']
    user_name = session['user_name']
    leave_room(user_id)

    rooms = redis.smembers(rkeys.rooms_for_user(user_id))
    for room in rooms:
        room_id, room_name = room.decode('utf-8').split(':', 1)
        remove_user_from_room(redis, user_id, user_name, room_id)
        send(activity_for_leave(user_id, user_name, room_id, room_name), room=room_name)

    redis.delete(rkeys.rooms_for_user(user_id))
    set_user_offline(redis, user_id)

    emit('gn_user_disconnected', activity_for_disconnect(user_id, user_name), broadcast=True, include_self=False)
    return 200, None
