from uuid import uuid4 as uuid

from activitystreams import parse as as_parser

from dino.config import ConfigKeys
from test.base import BaseTest
from dino.hooks import OnJoinHooks, OnLeaveHooks
from test.functional import BaseFunctionalTest
from dino import environ

environ.env.config.set(ConfigKeys.TESTING, True)
environ.env.config.set(ConfigKeys.SESSION, {'user_id': '1234'})

from dino import api
from dino import utils


class MultiSessionTest(BaseFunctionalTest):
    def setUp(self):
        self.set_up_env()

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

    def test_one_session_join(self):
        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertFalse(BaseTest.USER_ID in users.keys())

        act = self.activity_for_join()
        OnJoinHooks.join_room((act, as_parser(act)))
        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertTrue(BaseTest.USER_ID in users.keys())

        room_sids = self.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertIn(BaseTest.SESSION_ID, room_sids.keys())

    def test_one_session_leave(self):
        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertFalse(BaseTest.USER_ID in users.keys())

        act = self.activity_for_join()
        OnJoinHooks.join_room((act, as_parser(act)))

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertTrue(BaseTest.USER_ID in users.keys())

        from test.base import SESSION_ID
        room_sids = self.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertIn(SESSION_ID, room_sids.keys())

        act = self.activity_for_leave()
        OnLeaveHooks.leave_room((act, as_parser(act)))

        room_sids = self.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertNotIn(SESSION_ID, room_sids.keys())

    def test_two_sessions_one_leave(self):
        # first session joins
        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertNotIn(BaseTest.USER_ID, users.keys())

        session_one = BaseTest.SESSION_ID
        act = self.activity_for_join()
        OnJoinHooks.join_room((act, as_parser(act)))

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertIn(BaseTest.USER_ID, users.keys())

        # second session joins
        session_two = str(uuid())
        self.env.request = BaseTest.Request(session_two)
        OnJoinHooks.join_room((act, as_parser(act)))

        room_sids = self.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertIn(session_one, room_sids.keys())
        self.assertIn(session_two, room_sids.keys())

        # second session leaves
        act = self.act_leave()

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertIn(BaseTest.USER_ID, users.keys())

        OnLeaveHooks.leave_room((act, as_parser(act)))

        users = utils.get_users_in_room(BaseTest.ROOM_ID, skip_cache=True)
        self.assertIn(BaseTest.USER_ID, users.keys())

        room_sids = self.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
        self.assertNotIn(session_two, room_sids.keys())
        self.assertIn(session_one, room_sids.keys())

        # first session leaves
        self.env.request = BaseTest.Request(session_one)
        act = self.activity_for_leave()
        OnLeaveHooks.leave_room((act, as_parser(act)))

        room_sids = self.env.db.get_rooms_with_sid(user_id=BaseTest.USER_ID)
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
