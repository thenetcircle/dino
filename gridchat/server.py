import activitystreams as as_parser
from flask import Flask, redirect, url_for, request, render_template
from flask_socketio import SocketIO, send
from datetime import datetime
from pprint import pprint
import time

from gridchat.utils import *
from gridchat.forms import LoginForm

__author__ = 'Oscar Eriksson <oscar@thenetcircle.com>'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!fdsa'
socketio = SocketIO(app, message_queue='redis://')
redis = Redis('localhost')


@app.route('/', methods=['GET', 'POST'])
def index():
    form = LoginForm()
    if form.validate_on_submit():
        # temporary until we get ID from community
        session['user_name'] = form.user_id.data
        session['user_id'] = int(float(''.join([str(ord(x)) for x in form.user_id.data])) % 1000000)
        return redirect(url_for('.chat'))
    elif request.method == 'GET':
        form.user_id.data = session.get('user_id', '')
    return render_template('index.html', form=form)


@app.route('/chat')
def chat():
    user_id = session.get('user_id', '')
    user_name = session.get('user_name', '')
    if user_id == '':
        return redirect(url_for('.index'))
    return render_template('chat.html', name=user_id, room=user_id, user_id=user_id, user_name=user_name)


@socketio.on('connect', namespace='/chat')
@respond_with('gn_connect')
def connect() -> (int, None):
    """
    connect to the server

    :return: json if ok, {'status_code': 200}
    """
    return 200, None


@socketio.on('user_info', namespace='/chat')
@respond_with('gn_user_info')
def user_connection(data: dict) -> (int, str):
    """
    event sent directly after a connection has successfully been made, to get the user_id for this connection

    todo: check redis if any queued notifications, then emit and clear

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


@socketio.on('message', namespace='/chat')
@respond_with('gn_message')
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


@socketio.on('set_acl', namespace='/chat')
@respond_with('gn_set_acl')
def on_acl(data: dict) -> (int, str):
    """
    change ACL of a room; only allowed if the user is the owner of the room

    :param data:
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
    for acl_type in acls:
        if acl_type.object_type not in USER_KEYS:
            return 400, 'invalid acl type "%s"' % acl_type

    for acl in acls:
        redis.set(rkeys.room_acl(acl.object_type, room_id), acl.content)

    return 200, None


@socketio.on('get_acl', namespace='/chat')
@respond_with('gn_get_acl')
def on_acl(data: dict) -> (int, Union[str, dict]):
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

    acl_values = list()
    for acl in USER_KEYS:
        value = redis.get(rkeys.room_acl(acl.object_type, room_id))
        if value is None or value == '':
            continue
        acl_values.append((acl, str(value.decode('utf-8'))))

    return 200, activity_for_get_acl(activity, acl_values)


@socketio.on('status', namespace='/chat')
@respond_with('gn_status')
def on_status(data: dict) -> (int, Union[str, None]):
    """
    change online status
    todo: leave rooms on invisible/offline?

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


@socketio.on('join', namespace='/chat')
@respond_with('gn_join')
def on_join(data: dict) -> (int, Union[str, None]):
    """
    todo: how to deal with invisibility here?

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

    emit('user_joined', activity_for_join(user_id, user_name, room_id, room_name, image),
         room=room_id, broadcast=True, include_self=False)

    return 200, None


@socketio.on('users_in_room', namespace='/chat')
@respond_with('gn_users_in_room')
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


@socketio.on('list_rooms', namespace='/chat')
@respond_with('gn_list_rooms')
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


@socketio.on('leave', namespace='/chat')
@respond_with('gn_leave')
def on_leave(data: dict) -> (int, Union[str, None]):
    """
    todo: should handle invisibility here? don't broadcast leaving a room if invisible

    :param data: activity streams format, needs actor.id (user id), actor.summary (user name), target.id (room id)
    :return: json if ok, {'status_code': 200, 'data': 'Left'}
    """
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
    emit('user_left', activity_left, room=room_id, broadcast=True, include_self=False)

    return 200, None


@socketio.on('disconnect', namespace='/chat')
@respond_with('gn_disconnect')
def disconnect() -> (int, None):
    """
    todo: only broadcast 'offline' status if current status is 'online' (i.e. don't broadcast if e.g. 'invisible')

    :return json if ok, {'status_code': 200, 'data': 'Disconnected'}
    """
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

    emit('user_disconnected', activity_for_disconnect(user_id, user_name), broadcast=True, include_self=False)
    return 200, None
