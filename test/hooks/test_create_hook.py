from datetime import datetime, timedelta
from activitystreams import parse as as_parser
from uuid import uuid4 as uuid

from dino.db.manager.users import UserManager
from dino.hooks.create import OnCreateHooks
from dino.exceptions import NoSuchChannelException
from dino.exceptions import NoSuchRoomException
from dino.exceptions import UnknownBanTypeException
from dino.utils import b64d

from test.db import BaseDatabaseTest


class CreateHookTest(BaseDatabaseTest):
    _act = None

    @staticmethod
    def _publish(activity: dict, external=False) -> None:
        CreateHookTest._act = activity

    def setUp(self):
        self.set_up_env('redis')
        self.env.publish = CreateHookTest._publish
        self._act = None
        self.env.db = self.db
        self.manager = UserManager(self.env)

    def tearDown(self):
        self.db.redis.flushall()
        self.env.cache._flushall()

    def test_create_room_two_owners(self):
        self._create_channel()
        act = self.activity_for_create()
        act['target']['id'] = BaseDatabaseTest.ROOM_ID
        act['target']['attachments'] = [
            {
                'objectType': 'owners',
                'summary': ','.join([BaseDatabaseTest.USER_ID, BaseDatabaseTest.OTHER_USER_ID])
            }
        ]
        OnCreateHooks.create_room((act, as_parser(act)))
        self.assertTrue(self.db.is_owner(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.USER_ID))
        self.assertTrue(self.db.is_owner(BaseDatabaseTest.ROOM_ID, BaseDatabaseTest.OTHER_USER_ID))

    def test_get_owners(self):
        real_owners = {BaseDatabaseTest.USER_ID, BaseDatabaseTest.OTHER_USER_ID}
        act = self.activity_for_create()
        act['target']['attachments'] = [
            {
                'objectType': 'owners',
                'summary': ','.join(real_owners)
            }
        ]
        found_owners = OnCreateHooks._get_owners(as_parser(act))
        self.assertEqual(2, len(found_owners))
        self.assertIn(BaseDatabaseTest.USER_ID, found_owners)
        self.assertIn(BaseDatabaseTest.OTHER_USER_ID, found_owners)
