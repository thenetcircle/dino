import threading
import time
from typing import Union

import activitystreams as as_parser
from activitystreams.exception import ActivityException
from activitystreams.models.activity import Activity
from dino import api
from dino import environ
from dino import utils
from dino.config import ConfigKeys
from dino.forms import LoginForm
from dino.server import app, socketio
from dino.utils.handlers import GracefulInterruptHandler
from functools import wraps
from kombu import Connection
from kombu.mixins import ConsumerMixin
from flask_socketio import disconnect

logger = environ.env.logger


def respond_with(gn_event_name=None):
    def factory(view_func):
        @wraps(view_func)
        def decorator(*args, **kwargs):
            status_code, data = view_func(*args, **kwargs)
            if status_code != 200:
                logger.info('in decorator, status_code: %s, data: %s' % (status_code, str(data)))
            if data is None:
                environ.env.emit(gn_event_name, {'status_code': status_code})
            else:
                environ.env.emit(gn_event_name, {'status_code': status_code, 'data': data})

        return decorator

    return factory


class Worker(ConsumerMixin):
    def __init__(self, connection, signal_handler: GracefulInterruptHandler):
        self.connection = connection
        self.signal_handler = signal_handler

    def get_consumers(self, consumer, channel):
        return [consumer(queues=[environ.env.queue], callbacks=[self.process_task])]

    def on_iteration(self):
        if self.signal_handler.interrupted:
            self.should_stop = True

    def process_task(self, body, message):
        try:
            handle_server_activity(as_parser.parse(body))
        except (ActivityException, AttributeError) as e:
            logger.error('could not parse server message: "%s", message was: %s' % (str(e), body))
        message.ack()


def handle_server_activity(activity: Activity):
    def _kick(_room_id, _user_id, _user_sid):
        _users = socketio.server.manager.rooms[namespace][_room_id]
        if _user_id in _users:
            try:
                socketio.server.leave_room(_user_sid, '/chat', _room_id)
            except Exception as e:
                logger.error('could not kick user %s from room %s: %s' % (_user_id, _room_id, str(e)))
                return
            environ.env.out_of_scope_emit('gn_user_kicked', activity_json, room=_room_id, broadcast=True)

    if activity.verb == 'kick':
        kicker_id = activity.actor.id
        kicker_name = activity.actor.summary
        kicked_id = activity.object.id
        kicked_name = activity.object.summary
        kicked_sid = utils.get_sid_for_user_id(activity.object.id)
        room_id = activity.target.id
        room_name = activity.target.display_name
        namespace = activity.target.url

        if kicked_sid is None or kicked_sid == '':
            logger.info('no sid found for user id %s' % kicked_id)
            return

        activity_json = utils.activity_for_user_kicked(
                kicker_id, kicker_name, kicked_id, kicked_name, room_id, room_name)

        try:
            # user just got banned globally, kick from all rooms
            if room_id is None or room_id == '':
                for room_key in socketio.server.manager.rooms[namespace].keys():
                    _kick(room_key, kicked_id, kicked_sid)
            else:
                _kick(room_id, kicked_id, kicked_sid)
        except KeyError:
            pass

    else:
        environ.env.logger.error('unknown server activity verb "%s"' % activity.verb)


def consume():
    with GracefulInterruptHandler() as interrupt_handler:
        while True:
            with Connection(environ.env.config.get(ConfigKeys.HOST, domain=ConfigKeys.QUEUE)) as conn:
                try:
                    environ.env.consume_worker = Worker(conn, interrupt_handler)
                    environ.env.consume_worker.run()
                except KeyboardInterrupt:
                    return

            if interrupt_handler.interrupted or environ.env.consume_worker.should_stop:
                return

            time.sleep(1)


if not environ.env.config.get(ConfigKeys.TESTING, False):
    # preferably "emit" should be set during env creation, but the socketio object is not created until after env is
    environ.env.out_of_scope_emit = socketio.emit

    environ.env.consume_thread = threading.Thread(target=consume)
    environ.env.consume_thread.start()


@app.route('/', methods=['GET', 'POST'])
def index():
    form = LoginForm.create()
    if form.validate_on_submit():
        # temporary until we get ID from community
        environ.env.session['user_name'] = form.user_name.data
        environ.env.session['user_id'] = int(float(''.join([str(ord(x)) for x in form.user_name.data])) % 1000000)
        environ.env.session['age'] = form.age.data
        environ.env.session['gender'] = form.gender.data
        environ.env.session['membership'] = form.membership.data
        environ.env.session['fake_checked'] = form.fake_checked.data
        environ.env.session['has_webcam'] = form.has_webcam.data
        environ.env.session['image'] = form.image.data
        environ.env.session['country'] = form.country.data
        environ.env.session['city'] = form.city.data
        return environ.env.redirect(environ.env.url_for('.chat'))
    elif environ.env.request.method == 'GET':
        form.user_name.data = environ.env.session.get('user_name', '')
        form.age.data = environ.env.session.get('age', '')
        form.gender.data = environ.env.session.get('gender', '')
        form.membership.data = environ.env.session.get('membership', '')
        form.fake_checked.data = environ.env.session.get('fake_checked', '')
        form.has_webcam.data = environ.env.session.get('has_webcam', '')
        form.image.data = environ.env.session.get('image', '')
        form.country.data = environ.env.session.get('country', '')
        form.city.data = environ.env.session.get('city', '')
    return environ.env.render_template('index.html', form=form)


@app.route('/chat')
def chat():
    user_id = environ.env.session.get('user_id', '')
    user_name = environ.env.session.get('user_name', '')
    if user_id == '':
        return environ.env.redirect(environ.env.url_for('.index'))

    return environ.env.render_template(
            'chat.html', name=user_id, room=user_id, user_id=user_id, user_name=user_name,
            gender=environ.env.session.get('gender', ''),
            age=environ.env.session.get('age', ''),
            membership=environ.env.session.get('membership', ''),
            fake_checked=environ.env.session.get('fake_checked', ''),
            has_webcam=environ.env.session.get('has_webcam', ''),
            image=environ.env.session.get('image', ''),
            country=environ.env.session.get('country', ''),
            city=environ.env.session.get('city', ''),
            version=environ.env.config.get(ConfigKeys.VERSION))


@app.route('/js/<path:path>')
def send_js(path):
    return environ.env.send_from_directory('templates/js', path)


@app.route('/css/<path:path>')
def send_css(path):
    return environ.env.send_from_directory('templates/css', path)


@socketio.on('connect', namespace='/chat')
@respond_with('gn_connect')
def connect() -> (int, None):
    try:
        return api.on_connect()
    except Exception as e:
        logger.error('connect: %s' % str(e))
        return 500, str(e)


@socketio.on('login', namespace='/chat')
@respond_with('gn_login')
def on_login(data: dict) -> (int, str):
    try:
        status_code, msg = api.on_login(data)
        if status_code != 200:
            disconnect()
        return status_code, msg
    except Exception as e:
        logger.error('login: %s' % str(e))
        return 500, str(e)


@socketio.on('message', namespace='/chat')
@respond_with('gn_message')
def on_message(data):
    try:
        return api.on_message(data)
    except Exception as e:
        logger.error('message: %s' % str(e))
        return 500, str(e)


@socketio.on('create', namespace='/chat')
@respond_with('gn_create')
def on_create(data):
    try:
        return api.on_create(data)
    except Exception as e:
        logger.error('create: %s' % str(e))
        return 500, str(e)


@socketio.on('kick', namespace='/chat')
@respond_with('gn_kick')
def on_create(data):
    try:
        return api.on_kick(data)
    except Exception as e:
        logger.error('kick: %s' % str(e))
        return 500, str(e)


@socketio.on('set_acl', namespace='/chat')
@respond_with('gn_set_acl')
def on_set_acl(data: dict) -> (int, str):
    try:
        return api.on_set_acl(data)
    except Exception as e:
        logger.error('set_acl: %s' % str(e))
        return 500, str(e)


@socketio.on('get_acl', namespace='/chat')
@respond_with('gn_get_acl')
def on_get_acl(data: dict) -> (int, Union[str, dict]):
    try:
        return api.on_get_acl(data)
    except Exception as e:
        logger.error('get_acl: %s' % str(e))
        return 500, str(e)


@socketio.on('status', namespace='/chat')
@respond_with('gn_status')
def on_status(data: dict) -> (int, Union[str, None]):
    try:
        return api.on_status(data)
    except Exception as e:
        logger.error('status: %s' % str(e))
        return 500, str(e)


@socketio.on('history', namespace='/chat')
@respond_with('gn_history')
def on_history(data: dict) -> (int, Union[str, None]):
    try:
        return api.on_history(data)
    except Exception as e:
        logger.error('history: %s' % str(e))
        return 500, str(e)


@socketio.on('join', namespace='/chat')
@respond_with('gn_join')
def on_join(data: dict) -> (int, Union[str, None]):
    try:
        return api.on_join(data)
    except Exception as e:
        logger.error('join: %s' % str(e))
        return 500, str(e)


@socketio.on('users_in_room', namespace='/chat')
@respond_with('gn_users_in_room')
def on_users_in_room(data: dict) -> (int, Union[dict, str]):
    try:
        return api.on_users_in_room(data)
    except Exception as e:
        logger.error('users_in_room: %s' % str(e))
        return 500, str(e)


@socketio.on('list_rooms', namespace='/chat')
@respond_with('gn_list_rooms')
def on_list_rooms(data: dict) -> (int, Union[dict, str]):
    try:
        return api.on_list_rooms(data)
    except Exception as e:
        logger.error('list_rooms: %s' % str(e))
        return 500, str(e)


@socketio.on('leave', namespace='/chat')
@respond_with('gn_leave')
def on_leave(data: dict) -> (int, Union[str, None]):
    try:
        return api.on_leave(data)
    except Exception as e:
        logger.error('leave: %s' % str(e))
        return 500, str(e)


@socketio.on('disconnect', namespace='/chat')
@respond_with('gn_disconnect')
def on_disconnect() -> (int, None):
    try:
        return api.on_disconnect()
    except Exception as e:
        logger.error('disconnect: %s' % str(e))
        return 500, str(e)
