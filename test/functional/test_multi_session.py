import os
from uuid import uuid4 as uuid

from activitystreams import parse as as_parser
from dino.config import ConfigKeys
from pymitter import EventEmitter

from test.base import BaseTest
from test.db import BaseDatabaseTest

from dino import environ

environ.env.config.set(ConfigKeys.TESTING, True)
environ.env.config.set(ConfigKeys.SESSION, {'user_id': '1234'})

from dino import api
from dino import utils


class CreateRoomTest(BaseDatabaseTest):
    def setUp(self):
        os.environ['DINO_ENVIRONMENT'] = 'test'
        self.set_up_env('sqlite')

        from dino.stats.statsd import MockStatsd
        self.env.stats = MockStatsd()

        from dino.auth.simple import AllowAllAuth
        self.env.auth = AllowAllAuth()
        self.env.capture_exception = lambda x: False
        self.env.observer = EventEmitter()

        self.db.create_channel(BaseTest.CHANNEL_NAME, BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        act = self.activity_for_create()
        act['target']['id'] = BaseTest.ROOM_ID
        act['target']['objectType'] = 'room'

        from dino.hooks.create import OnCreateHooks
        OnCreateHooks.create_room((act, as_parser(act)))

    def tearDown(self):
        from dino.db.rdbms.dbman import Database
        from dino.db.rdbms.dbman import DeclarativeBase
        db = Database(self.env)
        con = db.engine.connect()
        trans = con.begin()
        for table in reversed(DeclarativeBase.metadata.sorted_tables):
            con.execute(table.delete())
        trans.commit()
        con.close()

        self.env.cache._flushall()

    def test_one_session_join(self):
        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertFalse(BaseTest.USER_ID in users.keys())

        act = self.activity_for_join()
        api.on_join(act, as_parser(act))

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertTrue(BaseTest.USER_ID in users.keys())

        from test.base import SESSION_ID
        room_sids = environ.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertIn(SESSION_ID, room_sids.keys())

    def test_one_session_leave(self):
        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertFalse(BaseTest.USER_ID in users.keys())

        act = self.activity_for_join()
        api.on_join(act, as_parser(act))

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertTrue(BaseTest.USER_ID in users.keys())

        from test.base import SESSION_ID
        room_sids = environ.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertIn(SESSION_ID, room_sids.keys())

        act = self.activity_for_leave()
        api.on_leave(act, as_parser(act))

        room_sids = environ.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertNotIn(SESSION_ID, room_sids.keys())

    def test_two_sessions_one_leave(self):
        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertNotIn(BaseTest.USER_ID, users.keys())

        session_one = BaseTest.SESSION_ID
        act = self.activity_for_join()
        api.on_join(act, as_parser(act))

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertIn(BaseTest.USER_ID, users.keys())

        # second session
        session_two = str(uuid())
        environ.env.request = BaseTest.Request(session_two)
        api.on_join(act, as_parser(act))

        room_sids = environ.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertIn(session_one, room_sids.keys())
        self.assertIn(session_two, room_sids.keys())

        act = self.activity_for_leave()
        api.on_leave(act, as_parser(act))

        room_sids = environ.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertNotIn(session_two, room_sids.keys())
        self.assertIn(session_one, room_sids.keys())

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertIn(BaseTest.USER_ID, users.keys())

        environ.env.request = BaseTest.Request(session_one)
        act = self.activity_for_leave()
        api.on_leave(act, as_parser(act))

        room_sids = environ.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertNotIn(session_two, room_sids.keys())
        self.assertNotIn(session_one, room_sids.keys())

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertNotIn(BaseTest.USER_ID, users.keys())

    def activity_for_join(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'verb': 'join',
            'object': {
                'url': BaseTest.CHANNEL_ID
            },
            'target': {
                'id': BaseTest.ROOM_ID,
                'objectType': 'room'
            }
        }

    def activity_for_leave(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID
            },
            'target': {
                'id': BaseTest.ROOM_ID
            },
            'verb': 'leave'
        }

    def activity_for_create(self):
        from dino.utils import b64e
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
