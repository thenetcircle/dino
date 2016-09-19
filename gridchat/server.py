__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

from flask import Flask, render_template
from flask import session, redirect, url_for, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room, send
from redis import Redis
import activitystreams as as_parser

from gridchat.forms import LoginForm
from gridchat.utils import *
from gridchat import rkeys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!fdsa'
socketio = SocketIO(app, message_queue='redis://maggie-kafka-3')
redis = Redis('maggie-kafka-3')


@app.route('/', methods=['GET', 'POST'])
def index():
    form = LoginForm()
    if form.validate_on_submit():
        session['user_id'] = form.user_id.data
        session['user_name'] = form.user_id.data
        return redirect(url_for('.chat'))
    elif request.method == 'GET':
        form.user_id.data = session.get('user_id', '')
    return render_template('index.html', form=form)


@app.route('/chat')
def chat():
    name = session.get('user_id', '')
    if name == '':
        return redirect(url_for('.index'))
    return render_template('chat.html', name=name, room=name, user_id=name)


@socketio.on('connect', namespace='/chat')
def connect():
    """
    connect to the server

    :return: json if ok, {'status_code': 200}
    """
    emit('init', {'status_code': 200})


@socketio.on('user-info', namespace='/chat')
def user_connection(data):
    """
    todo: don't broadcast anything here, only on 'status' event, to handle invisible etc.

    :param data: activity streams format, needs actor.id (user id) and actor.summary (user name)
    :return: json if ok, {'status_code': 200, 'data': 'Connected'}
    """
    activity = as_parser.parse(data)
    user_id = activity.actor.id
    join_room(user_id)
    redis.sadd(rkeys.online_users(), user_id)

    session['user_id'] = user_id
    session['user_name'] = activity.actor.summary

    emit('user-connected', data, broadcast=True, include_self=False)
    emit('response', {'status_code': 200, 'data': 'Connected'})


@socketio.on('status', namespace='/chat')
def on_status(data):
    """
    change online status

    :param data: activity streams format, needs actor.id (user id) and verb (online/invisible/offline)
    :return: json if ok, {'status_code': 200}
    """
    activity = as_parser.parse(data)
    user_id = activity.actor.id
    status = activity.verb

    if status == 'online':
        # todo: broadcast 'online' to friends
        pass
    elif status == 'invisible':
        # todo: broadcast 'offline' to friends
        pass
    elif status == 'offline':
        # todo: broadcast 'offline' to friends
        pass
    else:
        # ignore
        pass

    emit('response', {'status_code': 200})


@socketio.on('join', namespace='/chat')
def on_join(data):
    """
    todo: how to deal with invisibility here?

    :param data: activity streams format, need actor.id (user id), target.id (user id), actor.summary (user name)
    :return: json if okay, {'status_code': 200, 'users': <users in the room, format: 'user_id:user_name'>}
    """
    activity = as_parser.parse(data)
    room_id = activity.target.id
    user_id = activity.actor.id
    user_name = activity.actor.summary

    room_name = get_room_name(redis, room_id)
    join_the_room(redis, user_id, room_id, room_name)

    users_in_room = redis.smembers(rkeys.users_in_room(room_id))
    users = list()
    for user in users_in_room:
        users.append(str(user.decode('utf-8')))

    send(activity_for_join(user_id, user_name, room_id, room_name), room=room_id)
    emit('users_in_room', {'status_code': 200, 'users': users})


@socketio.on('users-in-room', namespace='/chat')
def on_users_in_room(data):
    """
    get a list of users in a room

    :param data: activity streams format, need target.id (room id)
    :return: json if ok, {'status_code': 200, 'users': <users in the room, format: 'user_id:user_name'>}
    """
    activity = as_parser.parse(data)
    room_id = activity.target.id

    users_in_room = redis.smembers(rkeys.users_in_room(room_id))
    users = list()
    for user in users_in_room:
        users.append(str(user.decode('utf-8')))

    emit('users-in-room', {'status_code': 200, 'users': users})


@socketio.on('list-rooms', namespace='/chat')
def on_list_rooms(data):
    """
    get a list of rooms

    :param data: activity streams format, currently not used, in the future should be able to specify sub-set of rooms,
    e.g. 'rooms in berlin'
    :return: json if ok, {'status_code': 200, 'rooms': <list of rooms, format: 'room_id:room_name'>}
    """
    all_rooms = redis.smembers(rkeys.rooms())

    rooms = list()
    for room in all_rooms:
        rooms.append(str(room.decode('utf-8')))

    emit('room-list', {'status_code': 200, 'users': rooms})


@socketio.on('leave', namespace='/chat')
def on_leave(data):
    """
    todo: should handle invisibility here? don't broadcast leaving a room if invisible

    :param data: activity streams format, needs actor.id (user id), actor.summary (user name), target.id (room id)
    :return: json if ok, {'status_code': 200, 'data': 'Left'}
    """
    activity = as_parser.parse(data)
    user_id = activity.actor.id
    user_name = activity.actor.summary
    room_id = activity.target.id
    room_name = get_room_name(redis, room_id)

    remove_user_from_room(redis, user_id, room_id)

    send(activity_for_leave(user_id, user_name, room_id, room_name), room=room_id)
    emit('response', {'status_code': 200, 'data': 'Left'})


@socketio.on('disconnect', namespace='/chat')
def disconnect():
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
        remove_user_from_room(redis, user_id, room_id)
        send(activity_for_leave(user_id, user_name, room_id, room_name), room=room_name)

    redis.delete(rkeys.rooms_for_user(user_id))
    redis.srem(rkeys.online_users(), user_id)

    emit('user-disconnected', activity_for_disconnect(user_id, user_name), broadcast=True, include_self=False)
    emit('response', {'status_code': 200, 'data': 'Disconnected'})


@socketio.on('message', namespace='/chat')
def on_message(data):
    activity = as_parser.parse(data)
    target = activity.target.id
    send(data, json=True, room=target)
    emit('response', {'status_code': 200, 'data': 'Sent'})


if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, host='0.0.0.0')
