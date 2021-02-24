#!/usr/bin/env python

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import logging

from activitystreams import parse as as_parser
from uuid import uuid4 as uuid
from datetime import datetime
from zope.interface import implementer

from dino import environ
from dino.stats import IStats
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.config import RedisKeys
from dino.config import RoleKeys
from dino.config import ApiActions
from dino.storage.redis import StorageRedis
from dino.auth.redis import AuthRedis
from dino.db.redis import DatabaseRedis
from dino.cache.miss import CacheAllMiss
from dino.validation.acl import AclStrInCsvValidator
from dino.validation.acl import AclRangeValidator
from dino.validation.acl import AclSameChannelValidator
from dino.validation.acl import AclDisallowValidator
from dino.validation.acl import AclSameRoomValidator
from dino.validation.acl import AclIsSuperUserValidator
from dino.validation.acl import AclIsAdminValidator

environ.env.config.set(ConfigKeys.TESTING, True)
environ.env.config.set(ConfigKeys.SESSION, {'user_id': '1234'})

from dino import api
from dino.utils import b64e

logging.basicConfig(level='DEBUG')
logger = logging.getLogger(__name__)


@implementer(IStats)
class MockStats(object):
    def incr(self, key: str) -> None:
        pass

    def decr(self, key: str) -> None:
        pass

    def timing(self, key: str, ms: int):
        pass

    def gauge(self, key: str, value: int):
        pass


class MockSpam(object):
    def is_spam(self, _):
        return False, ()


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
    OTHER_ROOM_ID = str(uuid())
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
    msgs_sent = dict()
    rendered_template = None
    send_dir = None
    send_file = None
    redirected_to = None

    @staticmethod
    def _mock_publish(message, external=False):
        pass

    @staticmethod
    def _emit(event, *args, **kwargs):
        if len(args) > 0:
            BaseTest.emit_args.append(*args)
        if len(kwargs) > 0:
            BaseTest.emit_args.extend(kwargs)

        if 'room' not in kwargs:
            return
        if kwargs['room'] not in BaseTest.msgs_sent:
            BaseTest.msgs_sent[kwargs['room']] = list()
        BaseTest.msgs_sent[kwargs['room']].append(args[0])

    @staticmethod
    def _disconnect():
        pass

    @staticmethod
    def _join_room(room, sid=None, namespace=None):
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
        if 'room' not in kwargs:
            return
        if kwargs['room'] not in BaseTest.msgs_sent:
            BaseTest.msgs_sent[kwargs['room']] = list()
        BaseTest.msgs_sent[kwargs['room']].append(message)

    @staticmethod
    def _send_from_directory(directory, filename, **options):
        BaseTest.send_dir = directory
        BaseTest.send_file = filename

    class Request(object):
        method = 'GET'
        sid = '124'
        namespace = '/chat'

        def __init__(self, sid=None):
            if sid is not None:
                self.sid = sid

    def setUp(self):
        BaseTest.users_in_room.clear()
        BaseTest.emit_args.clear()
        BaseTest.emit_kwargs.clear()
        BaseTest.msgs_sent.clear()
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
            'token': '66968fad-2336-40c9-bc6d-0ecbcd91f4da'
        }

        environ.env.config = environ.ConfigDict()
        environ.env.config.set(ConfigKeys.TESTING, True)
        environ.env.config = environ.env.config.sub(**self.session)

        all_acls = [
            'age',
            'gender',
            'membership',
            'group',
            'country',
            'city',
            'image',
            'has_webcam',
            'fake_checked',
            'owner',
            'admin',
            'moderator',
            'superuser',
            'crossroom',
            'samechannel',
            'sameroom',
            'disallow'
        ]
        environ.env.config.set(ConfigKeys.ACL, {
                'room': {
                    'join': {
                        'acls': all_acls
                    },
                    'message': {
                        'acls': all_acls
                    },
                    'history': {
                        'acls': all_acls
                    },
                    'crossroom': {
                        'acls': all_acls
                    }
                },
                'channel': {
                    'message': {
                        'acls': all_acls
                    },
                    'list': {
                        'acls': all_acls
                    },
                    'crossroom': {
                        'acls': all_acls
                    },
                    'whisper': {
                        'acls': ['disallow']
                    },
                },
                'available': {
                    'acls': all_acls
                },
                'validation': {
                    'superuser': {
                        'type': 'superuser',
                        'value': AclIsSuperUserValidator()
                    },
                    'admin': {
                        'type': 'admin',
                        'value': AclIsAdminValidator()
                    },
                    'samechannel': {
                        'type': 'samechannel',
                        'value': AclSameChannelValidator()
                    },
                    'sameroom': {
                        'type': 'sameroom',
                        'value': AclSameRoomValidator()
                    },
                    'country': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator()
                    },
                    'disallow': {
                        'type': 'disallow',
                        'value': AclDisallowValidator()
                    },
                    'gender': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('m,f')
                    },
                    'membership': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator()
                    },
                    'city': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator()
                    },
                    'has_webcam': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('y,n')
                    },
                    'fake_checked': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('y,n')
                    },
                    'image': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('y,n')
                    },
                    'group': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('')
                    },
                    'age': {
                        'type': 'range',
                        'value': AclRangeValidator()
                    }
                }
            }
        )

        environ.env.auth = AuthRedis('mock', env=environ.env)
        environ.env.storage = StorageRedis('mock')
        environ.env.db = DatabaseRedis(environ.env, 'mock')
        environ.env.storage.redis = environ.env.auth.redis
        environ.env.db.redis = environ.env.auth.redis
        environ.env.redis = environ.env.auth.redis
        environ.env.publish = BaseTest._mock_publish
        environ.env.disconnect = BaseTest._disconnect
        environ.env.stats = MockStats()
        environ.env.spam = MockSpam()
        environ.env.cache = CacheAllMiss()

        environ.env.auth.redis.flushall()
        environ.env.storage.redis.flushall()
        environ.env.db.redis.flushall()
        environ.env.cache._flushall()

        environ.env.auth.redis.hmset(RedisKeys.auth_key(BaseTest.USER_ID), self.session)
        environ.env.redis.hset(RedisKeys.room_name_for_id(), BaseTest.ROOM_ID, BaseTest.ROOM_NAME)
        environ.env.redis.sadd(RedisKeys.non_ephemeral_rooms(), BaseTest.ROOM_ID)
        environ.env.redis.hset(RedisKeys.channels(), BaseTest.CHANNEL_ID, BaseTest.CHANNEL_NAME)
        environ.env.db.redis.hset(RedisKeys.channels(), BaseTest.CHANNEL_ID, BaseTest.CHANNEL_NAME)
        environ.env.db.redis.hset(RedisKeys.auth_key(BaseTest.USER_ID), SessionKeys.user_name.value, BaseTest.USER_NAME)
        environ.env.db.redis.hset(RedisKeys.channel_for_rooms(), BaseTest.ROOM_ID, BaseTest.CHANNEL_ID)
        environ.env.db.redis.hset(RedisKeys.user_names(), BaseTest.USER_ID, BaseTest.USER_NAME)
        environ.env.db.redis.delete(RedisKeys.room_acl(BaseTest.ROOM_ID))

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
        #  and only have test logic in each test class, separate it
        self.env = environ.env

        self.env.db.set_user_name(BaseTest.USER_ID, BaseTest.USER_NAME)
        self.env.db.set_user_name(BaseTest.OTHER_USER_ID, BaseTest.OTHER_USER_NAME)

    def clear_session(self):
        environ.env.session.clear()

    def set_user_online(self):
        environ.env.db.set_user_online(BaseTest.USER_ID)

    def create_channel_and_room(self, room_id=None, room_name=None):
        self.create_channel(room_id=room_id, room_name=room_name)
        self.create_room(room_id=room_id, room_name=room_name)

    def create_and_join_room(self):
        self.create_channel_and_room()
        self.join_room()

    def create_room(self, room_id: str=None, room_name: str=None):
        if room_id is None:
            room_id = BaseTest.ROOM_ID
        if room_name is None:
            room_name = BaseTest.ROOM_NAME

        environ.env.storage.redis.hset(RedisKeys.rooms(BaseTest.CHANNEL_ID), room_id, room_name)
        environ.env.storage.redis.hset(RedisKeys.room_name_for_id(), room_id, room_name)
        environ.env.storage.redis.hset(RedisKeys.channel_for_rooms(), room_id, BaseTest.CHANNEL_ID)

    def create_channel(self, room_id=None, room_name=None):
        if room_id is None:
            room_id = BaseTest.ROOM_ID
        if room_name is None:
            room_name = BaseTest.ROOM_NAME

        environ.env.db.redis.hset(RedisKeys.rooms(BaseTest.CHANNEL_ID), room_id, room_name)
        environ.env.db.redis.hset(RedisKeys.channels(), BaseTest.CHANNEL_ID, BaseTest.CHANNEL_NAME)
        environ.env.db.redis.hset(RedisKeys.channel_roles(BaseTest.CHANNEL_ID), BaseTest.USER_ID, RoleKeys.OWNER)
        environ.env.db.redis.hset(RedisKeys.auth_key(BaseTest.USER_ID), SessionKeys.user_name.value, BaseTest.USER_NAME)
        environ.env.db.redis.hset(RedisKeys.channel_for_rooms(), room_id, BaseTest.CHANNEL_ID)
        environ.env.db.redis.hset(RedisKeys.room_name_for_id(), room_id, room_name)
        environ.env.cache.set_channel_exists(BaseTest.CHANNEL_ID)

    def create_user(self, user_id, user_name):
        environ.env.db.redis.hset(RedisKeys.user_names(), BaseTest.OTHER_USER_ID, BaseTest.OTHER_USER_NAME)

    def set_owner(self):
        environ.env.db.redis.hset(RedisKeys.user_names(), BaseTest.USER_ID, BaseTest.USER_NAME)
        environ.env.db.redis.hset(RedisKeys.room_roles(BaseTest.ROOM_ID), BaseTest.USER_ID, RoleKeys.OWNER)

    def remove_owner(self):
        environ.env.storage.redis.hdel(RedisKeys.room_roles(BaseTest.ROOM_ID), BaseTest.USER_ID)

    def remove_owner_channel(self):
        environ.env.storage.redis.hdel(RedisKeys.channel_roles(BaseTest.CHANNEL_ID), BaseTest.USER_ID)

    def remove_room(self):
        environ.env.storage.redis.hdel(RedisKeys.room_name_for_id(), BaseTest.ROOM_ID)

    def set_room_name(self, room_id: str=None, room_name: str=None):
        if room_id is None:
            room_id = BaseTest.ROOM_ID
        if room_name is None:
            room_name = BaseTest.ROOM_NAME

        environ.env.storage.redis.hset(RedisKeys.room_name_for_id(), room_id, room_name)

    def join_room(self):
        act = self.activity_for_join()
        api.on_join(act, as_parser(act))

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
        return api.on_leave(data, as_parser(data))

    def assert_join_fails(self):
        self.assertEqual(400, self.response_code_for_joining())
        self.assert_in_room(False)

    def assert_join_succeeds(self):
        self.assertEqual(200, self.response_code_for_joining())
        self.assert_in_room(True)

    def response_code_for_joining(self):
        act = self.activity_for_join()
        return api.on_join(act, as_parser(act))[0]

    def send_message(self, message: str) -> dict:
        act = self.activity_for_message(message)
        return api.on_message(act, as_parser(act))

    def remove_from_session(self, key: str):
        del environ.env.session[key]

    def set_session(self, key: str, value: str=None):
        environ.env.session[key] = value

    def get_emit_status_code(self):
        self.assertTrue(len(BaseTest.emit_args) > 0)
        return BaseTest.emit_args[-1].get('status_code')

    def get_acls(self):
        all_acls = environ.env.storage.redis.hgetall(RedisKeys.room_acl(BaseTest.ROOM_ID))
        cleaned = dict()

        for acl_key, acl_value in all_acls.items():
            api_action, acl_type = str(acl_key, 'utf-8').split('|', 1)
            if api_action not in cleaned:
                cleaned[api_action] = dict()
            cleaned[api_action][acl_type] = str(acl_value, 'utf-8')
        return cleaned

    def get_acls_for_join(self):
        acls = environ.env.db.redis.hgetall(RedisKeys.room_acl(BaseTest.ROOM_ID))
        acls_cleaned = dict()

        for acl_key, acl_value in acls.items():
            acl_action, acl_type = str(acl_key, 'utf-8').split('|', 1)
            if acl_action != ApiActions.JOIN:
                continue
            acls_cleaned[acl_type] = str(acl_value, 'utf-8')

        return acls_cleaned

    def set_acl(self, acls: dict, room_id=ROOM_ID):
        for api_action, acls_items in acls.items():
            for acl_type, acl_value in acls_items.items():
                r_key = '%s|%s' % (api_action, acl_type)
                environ.env.storage.redis.hset(RedisKeys.room_acl(room_id), r_key, acl_value)

    def set_channel_acl(self, acls: dict, channel_id=CHANNEL_ID):
        for api_action, acls_items in acls.items():
            for acl_type, acl_value in acls_items.items():
                r_key = '%s|%s' % (api_action, acl_type)
                environ.env.storage.redis.hset(RedisKeys.channel_acl(channel_id), r_key, acl_value)

    def set_acl_single(self, key: str, acls: str):
        environ.env.storage.redis.hset(RedisKeys.room_acl(BaseTest.ROOM_ID), key, acls)

    def assert_in_room(self, is_in_room):
        self.assertEqual(is_in_room, BaseTest.ROOM_ID in BaseTest.users_in_room and
                         BaseTest.USER_ID in BaseTest.users_in_room[BaseTest.ROOM_ID])

    def activity_for_history(self, skip: set=None):
        data = {
            'actor': {
                'id': BaseTest.USER_ID,
                'url': BaseTest.ROOM_ID
            },
            'object': {
                'url': BaseTest.CHANNEL_ID
            },
            'verb': 'history',
            'target': {
                'id': BaseTest.ROOM_ID,
                'objectType': 'room'
            }
        }

        if skip is not None:
            if 'user_id' in skip:
                del data['actor']['id']
            if 'user_name' in skip:
                del data['actor']['displayName']
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
                'displayName': b64e(BaseTest.ROOM_NAME),
                'objectType': 'room'
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
                'displayName': b64e(BaseTest.USER_NAME),
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
                del data['actor']['displayName']
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
            'target': {
                'objectType': 'room'
            },
            'verb': 'list'
        }

    def activity_for_message(self, msg: str='test message', object_type: str='room'):
        return {
            'actor': {
                'id': BaseTest.USER_ID,
                'url': BaseTest.ROOM_ID
            },
            'provider': {
                'url': BaseTest.CHANNEL_ID
            },
            'verb': 'send',
            'target': {
                'id': BaseTest.ROOM_ID,
                'objectType': object_type
            },
            'id': str(uuid()),
            'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
            'object': {
                'content': b64e(msg),
                'url': BaseTest.CHANNEL_ID
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
                'content': 'm,f',
                'summary': ApiActions.JOIN
            }]

        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'target': {
                'id': BaseTest.ROOM_ID,
                'objectType': 'room'
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

    def activity_for_join(self, user_id=USER_ID, room_id=ROOM_ID):
        return {
            'actor': {
                'id': user_id
            },
            'verb': 'join',
            'object': {
                'url': BaseTest.CHANNEL_ID
            },
            'target': {
                'id': room_id,
                'objectType': 'room'
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
                'id': BaseTest.ROOM_ID,
                'objectType': 'room'
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
