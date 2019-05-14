from activitystreams import parse as as_parser

from dino.hooks.leave import OnLeaveHooks
from dino.hooks.join import OnJoinHooks
from dino import utils
from dino import environ
from test.base import BaseTest
from test.db import BaseDatabaseTest
from dino.auth.simple import AllowAllAuth
from dino.stats.statsd import MockStatsd
from pymitter import EventEmitter

SESSION_ID_ONE = 'session-one'
SESSION_ID_TWO = 'session-two'


class MultiSessionTest(BaseDatabaseTest):
    def setUp(self):
        self.set_up_env('sqlite')
        self.env.stats = MockStatsd()
        self.env.auth = AllowAllAuth()
        self.env.capture_exception = lambda x: False
        self.env.observer = EventEmitter()

        self.env.request = BaseTest.Request(SESSION_ID_ONE)
        environ.env.request = self.env.request
        self.db.create_channel(BaseTest.CHANNEL_NAME, BaseTest.CHANNEL_ID, BaseTest.USER_ID)
        self.db.create_room(
            BaseTest.ROOM_NAME, BaseTest.ROOM_ID, BaseTest.CHANNEL_ID,
            BaseTest.USER_ID, BaseTest.USER_NAME
        )

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
        OnJoinHooks.join_room((act, as_parser(act)))
        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertTrue(BaseTest.USER_ID in users.keys())

        room_sids = self.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertIn(SESSION_ID_ONE, room_sids.keys())

    def test_one_session_leave(self):
        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertFalse(BaseTest.USER_ID in users.keys())

        act = self.activity_for_join()
        OnJoinHooks.join_room((act, as_parser(act)))

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertTrue(BaseTest.USER_ID in users.keys())

        room_sids = self.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertIn(SESSION_ID_ONE, room_sids.keys())

        act = self.activity_for_leave()
        OnLeaveHooks.leave_room((act, as_parser(act)))

        room_sids = self.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertNotIn(SESSION_ID_ONE, room_sids.keys())

    def test_two_sessions_one_leave(self):
        # first session joins
        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertNotIn(BaseTest.USER_ID, users.keys())

        act = self.activity_for_join()
        OnJoinHooks.join_room((act, as_parser(act)))

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertIn(BaseTest.USER_ID, users.keys())

        # second session joins
        self.env.request = BaseTest.Request(SESSION_ID_TWO)
        environ.env.request = self.env.request
        OnJoinHooks.join_room((act, as_parser(act)))

        room_sids = self.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertIn(SESSION_ID_ONE, room_sids.keys())
        self.assertIn(SESSION_ID_TWO, room_sids.keys())

        # second session leaves
        act = self.act_leave()

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertIn(BaseTest.USER_ID, users.keys())

        OnLeaveHooks.leave_room((act, as_parser(act)))

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertIn(BaseTest.USER_ID, users.keys())

        room_sids = self.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertNotIn(SESSION_ID_TWO, room_sids.keys())
        self.assertIn(SESSION_ID_ONE, room_sids.keys())

        # first session leaves
        self.env.request = BaseTest.Request(SESSION_ID_ONE)
        environ.env.request = self.env.request
        act = self.activity_for_leave()
        OnLeaveHooks.leave_room((act, as_parser(act)))

        room_sids = self.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertNotIn(SESSION_ID_TWO, room_sids.keys())
        self.assertNotIn(SESSION_ID_ONE, room_sids.keys())

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

    def act_leave(self):
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
