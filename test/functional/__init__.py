from uuid import uuid4 as uuid

from dino.storage.redis import StorageRedis

from dino import environ
from dino.cache.redis import CacheRedis
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.db.rdbms.handler import DatabaseRdbms
from dino.environ import ConfigDict
from dino.environ import GNEnvironment
from dino.validation.acl import AclDisallowValidator
from dino.validation.acl import AclIsAdminValidator
from dino.validation.acl import AclIsSuperUserValidator
from dino.validation.acl import AclRangeValidator
from dino.validation.acl import AclSameChannelValidator
from dino.validation.acl import AclSameRoomValidator
from dino.validation.acl import AclStrInCsvValidator
from test.base import BaseTest

from dino.hooks.join import *
from dino.hooks.leave import *
from pymitter import EventEmitter

environ.env.config.set(ConfigKeys.TESTING, True)
environ.env.config.set(ConfigKeys.SESSION, {'user_id': '1234'})


class BaseFunctionalTest(BaseTest):
    class FakeRequest(object):
        def __init__(self):
            self.sid = str(uuid())

    class FakeEnv(GNEnvironment):
        def __init__(self):
            super(BaseFunctionalTest.FakeEnv, self).__init__(None, ConfigDict(), skip_init=True)
            self.config = ConfigDict()
            self.cache = CacheRedis(self, 'mock')
            self.storage = StorageRedis(self, 'mock')
            self.session = dict()
            self.node = 'test'
            self.request = BaseFunctionalTest.FakeRequest()

    MESSAGE_ID = str(uuid())

    def set_up_env(self):
        self.env = BaseFunctionalTest.FakeEnv()
        self.env.config.set(ConfigKeys.TESTING, False)
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
        self.env.config.set(ConfigKeys.ACL, {
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
                    }
                },
                'available': {
                    'acls': all_acls
                },
                'validation': {
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
                    },
                    'admin': {
                        'type': 'is_admin',
                        'value': AclIsAdminValidator()
                    },
                    'superuser': {
                        'type': 'is_super_user',
                        'value': AclIsSuperUserValidator()
                    }
                }
            }
        )

        self.env.session[SessionKeys.user_name.value] = BaseTest.USER_NAME
        self.env.request.sid = BaseTest.SESSION_ID
        self.env.config.set(ConfigKeys.DRIVER, 'sqlite', domain=ConfigKeys.DATABASE)
        self.db = DatabaseRdbms(self.env)

        environ.env = self.env
        environ.env.config = self.env.config
        environ.env.db = self.db
        environ.env.join_room = lambda x: None
        environ.env.leave_room = lambda x: None
        environ.env.emit = self.emit

        environ.env.observer = EventEmitter()
        environ.env.db.create_user(BaseFunctionalTest.USER_ID, BaseFunctionalTest.USER_NAME)

    def emit(self, *args, **kwargs):
        pass
