__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

from flask import Flask, render_template, jsonify
from flask import session, redirect, url_for, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room, send
from flask import Blueprint
from pprint import pprint
from uuid import uuid4 as uuid
from redis import Redis
from time import time
import activitystreams as as_parser
from datetime import datetime

from gridchat.forms import LoginForm
from gridchat.utils import *


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!fdsa'
socketio = SocketIO(app, message_queue='redis://maggie-kafka-3')

redis = Redis('maggie-kafka-3')


@app.route('/', methods=['GET', 'POST'])
def index():
    """"Login form to enter a room."""
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
    """Chat room. The user's name and room must be stored in
    the session."""
    name = session.get('user_id', '')
    print('got %s' % name)
    if name == '':
        return redirect(url_for('.index'))
    return render_template('chat.html', name=name, room=name, user_id=name)


@socketio.on('connect', namespace='/chat')
def connect():
    all_rooms = redis.smembers('rooms')
    all_users = redis.smembers('users:online')

    rooms = list()
    users = list()

    for room in all_rooms:
        rooms.append(str(room.decode('utf-8')))
    for user in all_users:
        users.append(str(user.decode('utf-8')))

    response = {
        'status_code': 200,
        'rooms': rooms,
        'users': users
    }

    emit('init', response)


@socketio.on('user_connection', namespace='/chat')
def user_connection(data):
    activity = as_parser.parse(data)
    user_id = activity.actor.id
    join_room(user_id)
    redis.sadd('users:online', user_id)

    emit('user-connected', data, broadcast=True, include_self=False)
    emit('response', {'status_code': 200, 'data': 'Connected'})


@socketio.on('join', namespace='/chat')
def on_join(data):
    activity = as_parser.parse(data)
    room_id = activity.target.id
    user_id = activity.actor.id

    room_name = get_room_name(redis, room_id)
    join_the_room(redis, user_id, room_id, room_name)

    users_in_room = redis.smembers('room:%s' % room_id)
    users = list()
    for user in users_in_room:
        users.append(str(user.decode('utf-8')))

    send(activity_for_join(user_id, room_id, room_name), room=room_id)
    emit('users_in_room', {'status_code': 200, 'users': users})


@socketio.on('leave', namespace='/chat')
def on_leave(data):
    activity = as_parser.parse(data)
    user_id = activity.actor.id
    room_id = activity.target.id
    room_name = get_room_name(redis, room_id)

    remove_user_from_room(redis, user_id, room_id)

    send(activity_for_leave(user_id, room_id, room_name), room=room_id)
    emit('response', {'status_code': 200, 'data': 'Left'})


@socketio.on('disconnect', namespace='/chat')
def disconnect():
    user_id = session['user_id']
    user_name = session['user_name']
    leave_room(user_id)

    rooms = redis.smembers('user:rooms:' + user_id)
    for room in rooms:
        room_id, room_name = room.decode('utf-8').split(':', 1)
        remove_user_from_room(redis, user_id, room_id)
        leave_room(room_id)
        send(activity_for_leave(user_id, room_id, room_name), room=room_name)

    redis.delete('user:rooms:%s' % user_id)
    redis.srem('users:online', user_id)

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
