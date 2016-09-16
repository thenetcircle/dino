__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

from flask import Flask, render_template, jsonify
from flask import session, redirect, url_for, render_template, request
from forms import LoginForm
from flask_socketio import SocketIO, emit, join_room, leave_room, send
from flask import Blueprint
from pprint import pprint
from uuid import uuid4 as uuid
from redis import Redis
from time import time
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!fdsa'
socketio = SocketIO(app, message_queue='redis://')

redis = Redis('localhost')


@app.route('/', methods=['GET', 'POST'])
def index():
    """"Login form to enter a room."""
    form = LoginForm()
    if form.validate_on_submit():
        session['user_id'] = form.user_id.data
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
    print('got user_connection')
    pprint(data)
    user_id = data['user_id']
    join_room(user_id)
    redis.sadd('users:online', user_id)

    response = {
        'action': 'user-connected',
        'target': user_id
    }

    emit('user-connected', response, broadcast=True, include_self=False)
    emit('response', {'status_code': 200, 'data': 'Connected'})


def get_room_id(room_name):
    room_id = redis.get('room:id:' + room_name)
    if room_id is None:
        room_id = str(uuid())
        redis.set('room:id:' + room_name, room_id)
    else:
        room_id = room_id.decode('utf-8')
    return room_id


@socketio.on('join', namespace='/chat')
def on_join(data):
    pprint(data)
    room_name = data['room']
    actor = data['actor']
    room_id = get_room_id(room_name)

    join_room(room_name)

    redis_key = 'user:rooms:' + actor
    redis.sadd(redis_key, room_name)

    redis_key = 'room:' + room_name
    redis.sadd(redis_key, actor)
    redis.sadd('rooms', room_name)

    users_in_room = redis.smembers(redis_key)
    users = list()
    for user in users_in_room:
        users.append(str(user.decode('utf-8')))

    response = {
        'status_code': 200,
        'action': 'user_joined',
        'actor': actor,
        'target': room_name,
        'type': 'group',
        'group_id': room_id
    }

    send(response, room=room_name)
    emit('users_in_room', {'status_code': 200, 'users': users})


@socketio.on('leave', namespace='/chat')
def on_leave(data):
    pprint(data)
    actor = data['actor']
    room_name = data['room']
    room_id = get_room_id(room_name)
    remove_user_from_room(actor, room_name)

    response = {
        'status_code': 200,
        'action': 'user_left',
        'actor': actor,
        'target': room_name,
        'group_id': room_id
    }

    send(response, room=room_name)
    emit('response', {'status_code': 200, 'data': 'Left'})


@socketio.on('view', namespace='/chat')
def view_history(data):
    target = data['target']
    origin = data['actor']
    history_list = redis.lrange('%s-%s' % (target, origin), 0, -1)

    pprint(history_list)
    history = list()
    for h in history_list:
        user_id, timestamp, origin, target, message = str(h.decode('utf-8')).split(',', 4)
        history.append({
            'timestamp': timestamp,
            'origin': origin,
            'target': target,
            'msg': message,
            'user_id': user_id
        })

    history.sort(key=lambda x: x['timestamp'])

    response = {
        'status_code': 200,
        'history': history
    }

    emit('history', response)


def remove_user_from_room(user_id, room_name):
    leave_room(room_name)
    redis.srem('room:' + room_name, user_id)
    redis.srem('user:rooms:' + user_id, room_name)


@socketio.on('disconnect', namespace='/chat')
def disconnect():
    print('got disconnect')
    user_id = session["user_id"]
    leave_room(user_id)
    rooms = redis.smembers('user:rooms:' + user_id)

    for room in rooms:
        room_name = room.decode('utf-8')
        remove_user_from_room(user_id, room_name)
        room_id = get_room_id(room_name)

        response = {
            'action': 'user_left',
            'actor': user_id,
            'target': room_name,
            'group_id': room_id
        }

        send(response, room=room_name)
        leave_room(room_name)

    redis.delete('user:rooms:' + user_id)
    redis.srem('users:online', user_id)

    response = {
        'action': 'user-disconnect',
        'target': user_id
    }

    emit('user-disconnected', response, broadcast=True, include_self=False)
    emit('response', {'status_code': 200, 'data': 'Disconnected'})


@socketio.on('text', namespace='/chat')
def on_message(data):
    pprint(data)
    target = data['target']
    origin = data['actor']
    is_private_msg = data['private'] == 'true'
    timestamp = datetime.utcnow()
    timestamp_seconds = timestamp.strftime('%s')
    msg = data['msg']
    msg_id = str(uuid())

    room_id = ''
    if not is_private_msg:
        room_id = get_room_id(target)

    response = {
        'status_code': 200,
        'id': msg_id,
        'timestamp': timestamp_seconds,
        'strftime': timestamp.strftime('%Y-%m-%d %H:%m:%s'),
        'msg': msg,
        'origin': origin,
        'target': target,
        'private': data['private'],
        'group_id': room_id
    }

    redis_value = '%s,%s,%s,%s,%s' % (msg_id, timestamp_seconds, origin, target, msg)

    rkey_origin = '%s-%s' % (origin, target)
    rkey_target = '%s-%s' % (target, origin)

    redis.lpush(rkey_origin, redis_value)
    redis.lpush(rkey_target, redis_value)

    redis.ltrim(rkey_origin, 0, 100)
    redis.ltrim(rkey_target, 0, 100)

    print('sending to room %s' % target)
    pprint(response)

    send(response, json=True, room=target)
    if is_private_msg:
        emit('sent', response)


if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, host='0.0.0.0')
