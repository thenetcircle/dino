import unittest
from uuid import uuid4 as uuid
import logging

from dino import environ
from dino.config import ConfigKeys
from dino.config import RedisKeys
from dino.storage.redis import StorageRedis
from dino.auth.redis import AuthRedis
from dino.db.redis import DatabaseRedis
from dino.cache.miss import CacheAllMiss

environ.env.config.set(ConfigKeys.TESTING, True)
environ.env.config.set(ConfigKeys.SESSION, {'user_id': '1234'})

from dino import api

logging.basicConfig(level='DEBUG')
logger = logging.getLogger(__name__)


class Form(object):
    data = None

    def __init__(self, label=None, validators=None, filters=tuple(),
                 description='', id=None, default=None, widget=None,
                 render_kw=None, _form=None, _name=None, _prefix='',
                 _translations=None, _meta=None):
        if label is not None:
            value = environ.env.session.get('field:' + label, None)
            if value is not None:
                self.data = value


class SubmitField(Form):
    def __init__(self, label=None, validators=None, coerce=None, choices=None, **kwargs):
        super(SubmitField, self).__init__(label, validators, **kwargs)


class SelectField(Form):
    def __init__(self, label=None, validators=None, coerce=None, choices=None, **kwargs):
        super(SelectField, self).__init__(label, validators, **kwargs)


class StringField(Form):
    def __init__(self, label=None, validators=None, coerce=None, choices=None, **kwargs):
        super(StringField, self).__init__(label, validators, **kwargs)


class DataRequired(Form):
    def __init__(self, label=None, validators=None, coerce=None, choices=None, **kwargs):
        super(DataRequired, self).__init__(label, validators, **kwargs)


class BaseTest(unittest.TestCase):
    OTHER_USER_ID = '8888'
    OTHER_USER_NAME = 'pleb'
    USER_ID = '1234'
    USER_NAME = 'Joe'
    ROOM_ID = str(uuid())
    CHANNEL_ID = str(uuid())
    CHANNEL_NAME = 'Best Channel'
    ROOM_NAME = 'Shanghai'
    AGE = '30'
    GENDER = 'f'
    MEMBERSHIP = '0'
    IMAGE = 'y'
    HAS_WEBCAM = 'y'
    FAKE_CHECKED = 'n'
    COUNTRY = 'cn'
    CITY = 'Shanghai'

    users_in_room = dict()

    emit_args = list()
    emit_kwargs = dict()
    rendered_template = None
    send_dir = None
    send_file = None
    redirected_to = None

    @staticmethod
    def _mock_publish(message):
        pass

    @staticmethod
    def _emit(event, *args, **kwargs):
        if len(args) > 0:
            BaseTest.emit_args.append(*args)
        if len(kwargs) > 0:
            BaseTest.emit_args.extend(kwargs)

    @staticmethod
    def _join_room(room):
        if room not in BaseTest.users_in_room:
            BaseTest.users_in_room[room] = list()
        BaseTest.users_in_room[room].append(BaseTest.USER_ID)

    @staticmethod
    def _leave_room(room):
        if room not in BaseTest.users_in_room:
            return

        if BaseTest.USER_ID in BaseTest.users_in_room[room]:
            BaseTest.users_in_room[room].remove(BaseTest.USER_ID)

    @staticmethod
    def _render_template(template_name_or_list, **context):
        return template_name_or_list

    @staticmethod
    def _redirect(location, code=302, Response=None):
        return location

    @staticmethod
    def _url_for(endpoint, **values):
        return endpoint

    @staticmethod
    def _send(message, **kwargs):
        pass

    @staticmethod
    def _send_from_directory(directory, filename, **options):
        BaseTest.send_dir = directory
        BaseTest.send_file = filename

    class Request(object):
        method = 'GET'
        sid = '124'
        namespace = '/chat'

    def setUp(self):
        BaseTest.users_in_room.clear()
        BaseTest.emit_args.clear()
        BaseTest.emit_kwargs.clear()
        BaseTest.rendered_template = None

        self.session = {
            'user_id': BaseTest.USER_ID,
            'user_name': BaseTest.USER_NAME,
            'age': BaseTest.AGE,
            'gender': BaseTest.GENDER,
            'membership': BaseTest.MEMBERSHIP,
            'image': BaseTest.IMAGE,
            'fake_checked': BaseTest.FAKE_CHECKED,
            'has_webcam': BaseTest.HAS_WEBCAM,
            'city': BaseTest.CITY,
            'country': BaseTest.COUNTRY,
            'token': str(uuid())
        }

        environ.env.config.set(ConfigKeys.TESTING, True)
        environ.env.config = environ.env.config.sub(**self.session)
        environ.env.auth = AuthRedis('mock')
        environ.env.storage = StorageRedis('mock')
        environ.env.db = DatabaseRedis(environ.env, 'mock')
        environ.env.storage.redis = environ.env.auth.redis
        environ.env.db.redis = environ.env.auth.redis
        environ.env.redis = environ.env.auth.redis
        environ.env.publish = BaseTest._mock_publish
        environ.env.cache = CacheAllMiss()

        environ.env.auth.redis.flushall()
        environ.env.storage.redis.flushall()
        environ.env.db.redis.flushall()
        environ.env.cache.flushall()

        environ.env.auth.redis.hmset(RedisKeys.auth_key(BaseTest.USER_ID), self.session)
        environ.env.redis.set(RedisKeys.room_name_for_id(BaseTest.ROOM_ID), BaseTest.ROOM_NAME)
        environ.env.redis.hset(RedisKeys.channels(), BaseTest.CHANNEL_ID, BaseTest.CHANNEL_NAME)
        environ.env.db.redis.hset(RedisKeys.channels(), BaseTest.CHANNEL_ID, BaseTest.CHANNEL_NAME)

        environ.env.render_template = BaseTest._render_template
        environ.env.emit = BaseTest._emit
        environ.env.join_room = BaseTest._join_room
        environ.env.send = BaseTest._send
        environ.env.leave_room = BaseTest._leave_room
        environ.env.redirect = BaseTest._redirect
        environ.env.url_for = BaseTest._url_for
        environ.env.send_from_directory = BaseTest._send_from_directory
        environ.env.request = BaseTest.Request()

        environ.env.SelectField = SelectField
        environ.env.SubmitField = SubmitField
        environ.env.StringField = StringField
        environ.env.DataRequired = DataRequired
        environ.env.Form = Form

        environ.env.logger = logger
        environ.env.session = self.session

        # TODO: don't do this here, but too many tests that doesn't do it themselves... should remove this base class
        # and only have test logic in each test class, separate it
        environ.env.storage.redis.hset(RedisKeys.channel_for_rooms(), BaseTest.ROOM_ID, BaseTest.CHANNEL_ID)
        self.env = environ.env

    def clear_session(self):
        environ.env.session.clear()

    def assert_add_fails(self):
        self.assertEqual(400, self.get_response_code_for_add())

    def assert_add_succeeds(self):
        self.assertEqual(200, self.get_response_code_for_add())

    def get_response_code_for_add(self):
        return api.on_add_owner(self.activity_for_add_owner())[0]

    def create_channel_and_room(self):
        self.create_channel()
        self.create_room()

    def create_and_join_room(self):
        self.create_channel_and_room()
        self.join_room()

    def create_channel(self):
        environ.env.storage.redis.hset(RedisKeys.rooms(BaseTest.CHANNEL_ID), BaseTest.ROOM_ID, BaseTest.ROOM_NAME)
        environ.env.storage.redis.hset(RedisKeys.channels(), BaseTest.CHANNEL_ID, BaseTest.CHANNEL_NAME)
        environ.env.storage.redis.hset(RedisKeys.channel_roles(BaseTest.CHANNEL_ID), BaseTest.USER_ID, 'owner')
        self.env.cache.set_channel_exists(BaseTest.CHANNEL_ID)

    def set_owner(self):
        environ.env.storage.redis.hset(RedisKeys.room_owners(BaseTest.ROOM_ID), BaseTest.USER_ID, BaseTest.USER_NAME)

    def remove_owner(self):
        environ.env.storage.redis.hdel(RedisKeys.room_owners(BaseTest.ROOM_ID), BaseTest.USER_ID)

    def remove_room(self):
        environ.env.storage.redis.delete(RedisKeys.room_name_for_id(BaseTest.ROOM_ID))

    def set_room_name(self, room_id: str=None, room_name: str=None):
        if room_id is None:
            room_id = BaseTest.ROOM_ID
        if room_name is None:
            room_name = BaseTest.ROOM_NAME

        environ.env.storage.redis.set(RedisKeys.room_name_for_id(room_id), room_name)

    def join_room(self):
        api.on_join(self.activity_for_join())

    def clear_emit_args(self):
        self.emit_kwargs.clear()
        self.emit_args.clear()

    def assert_in_session(self, key, expected):
        self.assertTrue(key in environ.env.session)
        self.assertEqual(expected, environ.env.session[key])

    def assert_not_in_session(self, key, expected):
        self.assertFalse(key in environ.env.session)

    def leave_room(self, data=None):
        if data is None:
            data = self.activity_for_leave()
        return api.on_leave(data)

    def create_room(self, room_id: str=None, room_name: str=None):
        if room_id is None:
            room_id = BaseTest.ROOM_ID
        if room_name is None:
            room_name = BaseTest.ROOM_NAME

        environ.env.storage.redis.hset(RedisKeys.rooms(BaseTest.CHANNEL_ID), room_id, room_name)

    def assert_join_fails(self):
        self.assertEqual(400, self.response_code_for_joining())
        self.assert_in_room(False)

    def assert_join_succeeds(self):
        self.assertEqual(200, self.response_code_for_joining())
        self.assert_in_room(True)

    def response_code_for_joining(self):
        return api.on_join(self.activity_for_join())[0]

    def send_message(self, message: str) -> dict:
        return api.on_message(self.activity_for_message(message))

    def remove_from_session(self, key: str):
        del environ.env.session[key]

    def set_session(self, key: str, value: str=None):
        environ.env.session[key] = value

    def get_emit_status_code(self):
        self.assertTrue(len(BaseTest.emit_args) > 0)
        return BaseTest.emit_args[-1].get('status_code')

    def get_acls(self):
        return environ.env.storage.redis.hgetall(RedisKeys.room_acl(BaseTest.ROOM_ID))

    def set_acl(self, acls: dict):
        environ.env.storage.redis.hmset(RedisKeys.room_acl(BaseTest.ROOM_ID), acls)

    def set_acl_single(self, key: str, acls: str):
        environ.env.storage.redis.hset(RedisKeys.room_acl(BaseTest.ROOM_ID), key, acls)

    def assert_in_room(self, is_in_room):
        self.assertEqual(is_in_room, BaseTest.ROOM_ID in BaseTest.users_in_room and
                         BaseTest.USER_ID in BaseTest.users_in_room[BaseTest.ROOM_ID])

    def assert_in_own_room(self, is_in_room):
        self.assertEqual(is_in_room, BaseTest.USER_ID in BaseTest.users_in_room and
                         BaseTest.USER_ID in BaseTest.users_in_room[BaseTest.USER_ID])

    def activity_for_history(self, skip: set=None):
        data = {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'verb': 'history',
            'target': {
                'id': BaseTest.ROOM_ID,
            }
        }

        if skip is not None:
            if 'user_id' in skip:
                del data['actor']['id']
            if 'user_name' in skip:
                del data['actor']['summary']
            if 'target_id' in skip:
                del data['target']['id']

        return data

    def activity_for_create(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'object': {
                'url': BaseTest.CHANNEL_ID
            },
            'verb': 'create',
            'target': {
                'displayName': BaseTest.ROOM_NAME,
                'objectType': 'group'
            }
        }

    def activity_for_users_in_room(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'verb': 'list',
            'target': {
                'id': BaseTest.ROOM_ID
            }
        }

    def activity_for_login(self, skip: set=None):
        data = {
            'actor': {
                'id': BaseTest.USER_ID,
                'summary': BaseTest.USER_NAME,
                'image': {
                    'url': 'http://some-url.com/image.jpg',
                    'width': '120',
                    'height': '120'
                },
                'attachments': list()
            },
            'verb': 'login'
        }

        if skip is not None:
            if 'user_id' in skip:
                del data['actor']['id']
            if 'user_name' in skip:
                del data['actor']['summary']
            if 'image' in skip:
                del data['actor']['image']

        infos = {
            'gender': BaseTest.GENDER,
            'age': BaseTest.AGE,
            'membership': BaseTest.MEMBERSHIP,
            'fake_checked': BaseTest.FAKE_CHECKED,
            'has_webcam': BaseTest.HAS_WEBCAM,
            'country': BaseTest.COUNTRY,
            'city': BaseTest.CITY,
            'token': '66968fad-2336-40c9-bc6d-0ecbcd91f4da'
        }

        for key, val in infos.items():
            if skip is None or key not in skip:
                data['actor']['attachments'].append({'objectType': key, 'content': val})

        return data

    def activity_for_list_rooms(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'object': {
                'url': BaseTest.CHANNEL_ID
            },
            'verb': 'list'
        }

    def activity_for_message(self, msg: str='test message'):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'verb': 'send',
            'target': {
                'id': BaseTest.ROOM_ID
            },
            'object': {
                'content': msg
            }
        }

    def activity_for_leave(self, skip: set=None):
        data = {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'target': {
                'id': BaseTest.ROOM_ID
            },
            'verb': 'leave'
        }

        if skip is not None:
            for s in list(skip):
                del data[s]

        return data

    def activity_for_set_acl(self, attachments: list=None):
        if attachments is None:
            attachments = [{
                'objectType': 'gender',
                'content': 'm,f'
            }]

        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'target': {
                'id': BaseTest.ROOM_ID
            },
            'verb': 'set',
            'object': {
                'objectType': 'acl',
                'attachments': attachments
            }
        }

    def activity_for_add_owner(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'verb': 'add',
            'object': {
                'objectType': 'user',
                'content': BaseTest.OTHER_USER_ID
            },
            'target': {
                'id': BaseTest.ROOM_ID
            }
        }

    def activity_for_join(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'verb': 'join',
            'target': {
                'id': BaseTest.ROOM_ID
            }
        }

    def activity_for_kick(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'verb': 'join',
            'target': {
                'id': BaseTest.ROOM_ID,
                'displayName': BaseTest.OTHER_USER_ID
            }
        }

    def activity_for_get_acl(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'target': {
                'id': BaseTest.ROOM_ID
            },
            'verb': 'list'
        }

    def activity_for_status(self, verb: str):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'verb': verb
        }
