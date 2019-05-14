from activitystreams import parse as as_parser

from dino.config import ConfigKeys
from test.base import BaseTest
from dino.hooks import OnJoinHooks, OnLeaveHooks
from test.functional import BaseFunctional
from dino import environ

from dino import utils

SESSION_ID_ONE = 'session-one'
SESSION_ID_TWO = 'session-two'


class MultiSession(BaseFunctional):
    def setUp(self):
        self.set_up_env()

        environ.env.config.set(ConfigKeys.TESTING, True)
        environ.env.config.set(ConfigKeys.SESSION, {'user_id': '1234'})

        self.env.request = BaseTest.Request(SESSION_ID_ONE)
        self.env.db.create_channel(BaseTest.CHANNEL_NAME, BaseTest.CHANNEL_ID, BaseTest.USER_ID)
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

    def one_session_join(self):
        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertFalse(BaseTest.USER_ID in users.keys())

        act = self.activity_for_join()
        OnJoinHooks.join_room((act, as_parser(act)))
        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertTrue(BaseTest.USER_ID in users.keys())

        room_sids = self.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertIn(SESSION_ID_ONE, room_sids.keys())

    def one_session_leave(self):
        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertFalse(BaseTest.USER_ID in users.keys())

        act = self.activity_for_join()
        OnJoinHooks.join_room((act, as_parser(act)))

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertTrue(BaseTest.USER_ID in users.keys())

        room_sids = self.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertIn(SESSION_ID_ONE, room_sids.keys())

        act = self.activity_for_leave()
        OnLeaveHooks.leave_room((act, as_parser(act)))

        room_sids = self.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertNotIn(SESSION_ID_ONE, room_sids.keys())

    def two_sessions_one_leave(self):
        # first session joins
        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertNotIn(BaseTest.USER_ID, users.keys())

        act = self.activity_for_join()
        OnJoinHooks.join_room((act, as_parser(act)))

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertIn(BaseTest.USER_ID, users.keys())

        # second session joins
        self.env.request = BaseTest.Request(SESSION_ID_TWO)
        OnJoinHooks.join_room((act, as_parser(act)))

        room_sids = self.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertIn(SESSION_ID_ONE, room_sids.keys())
        self.assertIn(SESSION_ID_TWO, room_sids.keys())

        # second session leaves
        act = self.act_leave()

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertIn(BaseTest.USER_ID, users.keys())

        OnLeaveHooks.leave_room((act, as_parser(act)))

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertIn(BaseTest.USER_ID, users.keys())

        room_sids = self.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertNotIn(SESSION_ID_TWO, room_sids.keys())
        self.assertIn(SESSION_ID_ONE, room_sids.keys())

        # first session leaves
        self.env.request = BaseTest.Request(SESSION_ID_ONE)
        act = self.activity_for_leave()
        OnLeaveHooks.leave_room((act, as_parser(act)))

        room_sids = self.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
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
