from datetime import datetime
from datetime import timedelta
from uuid import uuid4 as uuid

from dino.auth.redis import AuthRedis
from dino.config import ApiActions, SessionKeys, RedisKeys
from dino.rest.resources.rooms_acl import RoomsAclResource
from test.base import BaseTest
from test.db import BaseDatabaseTest


class RoomsAclTest(BaseDatabaseTest):
    def setUp(self):
        # environ.env.db = FakeDb()
        self.set_up_env('redis')
        self.env.db = self.db
        self.resource = RoomsAclResource()

        self.auth = AuthRedis(env=self.env, host='mock')
        self.session = {
            SessionKeys.user_id.value: BaseTest.USER_ID,
            SessionKeys.user_name.value: BaseTest.USER_NAME,
            SessionKeys.gender.value: BaseTest.GENDER,
        }

        for key, value in self.session.items():
            self.auth.update_session_for_key(BaseTest.USER_ID, key, value)

        self.channel_id = str(uuid())
        self.env.db.create_channel("test name", self.channel_id, BaseTest.OTHER_USER_ID)

        self.env.auth = self.auth
        self.env.session = self.session
        self.resource.env = self.env

    def tearDown(self):
        self.db.redis.flushall()
        self.env.cache._flushall()

    def test_get_one_rooms(self):
        self.env.db.create_room("room name 1", str(uuid()), self.channel_id, BaseTest.OTHER_USER_ID, "user name", False, 999)
        self.assertEqual(1, len(self.resource._do_get(BaseTest.USER_ID)))

    def test_get_three_rooms(self):
        self.env.db.create_room("room name 1", str(uuid()), self.channel_id, BaseTest.OTHER_USER_ID, "user name", False, 999)
        self.env.db.create_room("room name 2", str(uuid()), self.channel_id, BaseTest.OTHER_USER_ID, "user name", False, 999)
        self.env.db.create_room("room name 3", str(uuid()), self.channel_id, BaseTest.OTHER_USER_ID, "user name", False, 999)
        self.assertEqual(3, len(self.resource._do_get(BaseTest.USER_ID)))

    def test_get_two_rooms_one_not_allowed(self):
        room_id_to_forbid = str(uuid())

        self.env.db.create_room("room name 1", str(uuid()), self.channel_id, BaseTest.OTHER_USER_ID, "user name", False, 999)
        self.env.db.create_room("room name 2", room_id_to_forbid, self.channel_id, BaseTest.OTHER_USER_ID, "user name", False, 999)
        self.env.db.create_room("room name 3", str(uuid()), self.channel_id, BaseTest.OTHER_USER_ID, "user name", False, 999)

        self.env.db.add_acls_in_room_for_action(
            room_id_to_forbid,
            ApiActions.JOIN,
            {"gender": "m"}
        )

        rooms = self.resource._do_get(BaseTest.USER_ID)

        self.assertEqual(2, len(rooms))
        self.assertTrue(all((room["room_name"] in {"room name 1", "room name 3"} for room in rooms)))

    def test_get_two_channels_one_not_allowed_two_rooms_one_not_allowed(self):
        room_id_to_forbid = str(uuid())

        self.env.db.create_room("room name 1", str(uuid()), self.channel_id, BaseTest.OTHER_USER_ID, "user name", False, 999)
        self.env.db.create_room("room name 2", room_id_to_forbid, self.channel_id, BaseTest.OTHER_USER_ID, "user name", False, 999)
        self.env.db.create_room("room name 3", str(uuid()), self.channel_id, BaseTest.OTHER_USER_ID, "user name", False, 999)

        self.env.db.add_acls_in_room_for_action(
            room_id_to_forbid,
            ApiActions.JOIN,
            {"gender": "m"}
        )

        channel_id_to_forbid = str(uuid())

        self.env.db.create_channel("test name 2", channel_id_to_forbid, BaseTest.OTHER_USER_ID)
        self.env.db.create_room("room name 4", str(uuid()), channel_id_to_forbid, BaseTest.OTHER_USER_ID, "user name", False, 999)
        self.env.db.add_acls_in_channel_for_action(
            channel_id_to_forbid,
            ApiActions.LIST,
            {"gender": "m"}
        )

        rooms = self.resource._do_get(BaseTest.USER_ID)

        self.assertEqual(2, len(rooms))
        self.assertTrue(all((room["room_name"] in {"room name 1", "room name 3"} for room in rooms)))
        self.assertTrue(all((room["channel_name"] == "test name" for room in rooms)))

    def test_set_last_cleared(self):
        last_cleared = self.resource._get_last_cleared()
        self.resource._set_last_cleared(datetime.utcnow()+timedelta(minutes=5))
        self.assertNotEqual(last_cleared, self.resource._get_last_cleared())
