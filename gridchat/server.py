__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

from flask import Flask, render_template
from flask import session, redirect, url_for, render_template, request
from forms import LoginForm
from flask_socketio import SocketIO, emit, join_room, leave_room, send
from flask import Blueprint
from pprint import pprint

async_mode = 'gevent_uwsgi'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode, message_queue='redis://maggie-kafka-3')


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
    pprint(request)
    emit('response', {'data': 'Connected'})


@socketio.on('user_connection', namespace='/chat')
def user_connection(data):
    pprint(data)
    user_id = data['user_id']
    join_room(user_id)
    emit('response', {'data': 'Connected'})


@socketio.on('disconnect', namespace='/chat')
def disconnect():
    pprint(request)
    #user_id = data['user_id']
    #leave_room(user_id)


@socketio.on('text', namespace='/chat')
def on_message(data):
    def callback(**kwargs):
        print('callback arguments: ')
        pprint(kwargs)

    from uuid import uuid4 as uuid
    pprint(data)
    target = data['target']
    send(data, json=True, namespace='/chat', room=target)#, callback=callback, broadcast=False)
    emit('response', {'status': 'OK', 'id': str(uuid())})


if __name__ == '__main__':
    socketio.run(app, debug=True)