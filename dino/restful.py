import os

from flask import Flask
from flask_restful import Api
from flask_socketio import SocketIO
from werkzeug.contrib.fixers import ProxyFix

from dino.hooks import *
from dino.rest.resources.acl import AclResource
from dino.rest.resources.ban import BanResource
from dino.rest.resources.banned import BannedResource
from dino.rest.resources.blacklist import BlacklistResource
from dino.rest.resources.broadcast import BroadcastResource
from dino.rest.resources.clear_history import ClearHistoryResource
from dino.rest.resources.create import CreateRoomResource
from dino.rest.resources.full_history import FullHistoryResource
from dino.rest.resources.heartbeat import HeartbeatResource
from dino.rest.resources.history import HistoryResource
from dino.rest.resources.joins import JoinsInRoomResource
from dino.rest.resources.kick import KickResource
from dino.rest.resources.latest_history import LatestHistoryResource
from dino.rest.resources.remove_admin import RemoveAdminResource
from dino.rest.resources.roles import RolesResource
from dino.rest.resources.rooms import RoomsResource
from dino.rest.resources.rooms_acl import RoomsAclResource
from dino.rest.resources.rooms_for_users import RoomsForUsersResource
from dino.rest.resources.send import SendResource
from dino.rest.resources.set_admin import SetAdminResource
from dino.rest.resources.status import SetStatusResource
from dino.rest.resources.users_in_rooms import UsersInRoomsResource

logger = logging.getLogger(__name__)
logging.getLogger('amqp').setLevel(logging.INFO)
logging.getLogger('kafka.conn').setLevel(logging.INFO)


def create_app():
    _app = Flask(__name__)

    # used for encrypting cookies for handling sessions
    _app.config['SECRET_KEY'] = 'abc492ee-9739-11e6-a174-07f6b92d4a4b'

    message_queue_type = environ.env.config.get(ConfigKeys.TYPE, domain=ConfigKeys.COORDINATOR, default=None)
    if message_queue_type is None and not (len(environ.env.config) == 0 or environ.env.config.get(ConfigKeys.TESTING)):
        raise RuntimeError('no message queue type specified')

    queue_host = environ.env.config.get(ConfigKeys.HOST, domain=ConfigKeys.COORDINATOR, default='')
    message_channel = ''
    message_queue = None

    if message_queue_type == 'redis':
        message_db = environ.env.config.get(ConfigKeys.DB, domain=ConfigKeys.COORDINATOR, default=0)
        message_env = environ.env.config.get(ConfigKeys.ENVIRONMENT, default='test')
        message_channel = 'dino_{}_{}'.format(message_env, message_db)
        message_queue = 'redis://{}'.format(queue_host)

    elif message_queue_type == 'amqp':
        message_channel = 'dino_%s' % environ.env.config.get(ConfigKeys.ENVIRONMENT, default='test')
        message_queue = ';'.join(['amqp://%s:%s@%s:%s%s' % (
            environ.env.config.get(ConfigKeys.USER, domain=ConfigKeys.COORDINATOR, default=''),
            environ.env.config.get(ConfigKeys.PASSWORD, domain=ConfigKeys.COORDINATOR, default=''),
            host,
            environ.env.config.get(ConfigKeys.PORT, domain=ConfigKeys.COORDINATOR, default=''),
            environ.env.config.get(ConfigKeys.VHOST, domain=ConfigKeys.COORDINATOR, default=''),
        ) for host in queue_host.split(';')])

    logger.info('message_queue: %s' % message_queue)

    _api = Api(_app)

    _socketio = SocketIO(
            _app,
            logger=logger,
            engineio_logger=os.environ.get('DINO_DEBUG', '0') == '1',
            async_mode='eventlet',
            message_queue=message_queue,
            channel=message_channel)

    # preferably "emit" should be set during env creation, but the socketio object is not created until after env is
    environ.env.out_of_scope_emit = _socketio.emit

    _app.wsgi_app = ProxyFix(_app.wsgi_app)
    return _app, _api, _socketio


app, api, socketio = create_app()

api.add_resource(ClearHistoryResource, '/delete-messages')
api.add_resource(RolesResource, '/roles')
api.add_resource(BannedResource, '/banned')
api.add_resource(BanResource, '/ban')
api.add_resource(HistoryResource, '/history')
api.add_resource(LatestHistoryResource, '/latest-history')
api.add_resource(KickResource, '/kick')
api.add_resource(RoomsForUsersResource, '/rooms-for-users')
api.add_resource(SetAdminResource, '/set-admin')
api.add_resource(RemoveAdminResource, '/remove-admin')
api.add_resource(BlacklistResource, '/blacklist')
api.add_resource(BroadcastResource, '/broadcast')
api.add_resource(SendResource, '/send')
api.add_resource(SetStatusResource, '/status')
api.add_resource(FullHistoryResource, '/full-history')
api.add_resource(HeartbeatResource, '/heartbeat')
api.add_resource(AclResource, '/acl')
api.add_resource(RoomsResource, '/rooms')
api.add_resource(RoomsAclResource, '/rooms-acl')
api.add_resource(UsersInRoomsResource, '/users-in-rooms')
api.add_resource(JoinsInRoomResource, '/count-joins')
api.add_resource(CreateRoomResource, '/create')
