from uuid import uuid4 as uuid

from activitystreams import parse as as_parser

from dino.db.rdbms.models import Rooms
from dino.hooks.create import OnCreateHooks
from dino.utils import b64e
from test.base import BaseTest
from test.db import BaseDatabaseTest
from dino.auth.simple import AllowAllAuth
from dino.stats.statsd import MockStatsd
from pymitter import EventEmitter


class CreateRoomTest(BaseDatabaseTest):
    def setUp(self):
        self.set_up_env('sqlite')
        self.env.stats = MockStatsd()
        self.env.auth = AllowAllAuth()
        self.env.capture_exception = lambda x: False
        self.env.observer = EventEmitter()

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

    def test_create_private_room(self):
        self.db.create_channel(BaseTest.CHANNEL_NAME, BaseTest.CHANNEL_ID, BaseTest.USER_ID)

        act = self.activity_for_create()
        act['target']['id'] = str(uuid())
        act['target']['objectType'] = 'private'
        OnCreateHooks.create_room((act, as_parser(act)))

        session = self.db._session()
        rooms = session.query(Rooms).all()
        print(len(rooms))
        room = session.query(Rooms).filter(Rooms.name == BaseTest.ROOM_NAME).first()
        self.assertFalse(room.ephemeral)

    def test_create_ephemeral_room(self):
        self.db.create_channel(BaseTest.CHANNEL_NAME, BaseTest.CHANNEL_ID, BaseTest.USER_ID)

        act = self.activity_for_create()
        act['target']['id'] = str(uuid())
        act['target']['objectType'] = 'room'
        OnCreateHooks.create_room((act, as_parser(act)))

        session = self.db._session()
        rooms = session.query(Rooms).all()
        print(len(rooms))
        room = session.query(Rooms).filter(Rooms.name == BaseTest.ROOM_NAME).first()
        self.assertTrue(room.ephemeral)

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
