from unittest import TestCase

from uuid import uuid4 as uuid
from dino import environ
from dino.cache.redis import CacheRedis
from dino.db.redis import DatabaseRedis
from dino.rest.resources.create import CreateRoomResource


class FakeRequest(object):
    should_fail = False

    def get_json(*args, **kwargs):
        if FakeRequest.should_fail:
            raise RuntimeError('testing')

        return {
            'users': [
                CreateRoomTest.USER_ID
            ]
        }


class FakeObserver:
    def __init__(self):
        self.events = list()

    def emit(self, event_name, data_act):
        act = data_act[1]
        self.events.append((event_name, act))

class CreateRoomTest(TestCase):
    USER_ID = '8888'
    ROOM_ID = '1234'
    ROOM_ID_2 = '4321'
    ROOM_NAME = 'cool guys'
    ROOM_NAME_2 = 'bad guys'
    CHANNEL_ID = '5555'
    CHANNEL_NAME = 'Shanghai'

    def setUp(self):
        self.cache = CacheRedis(environ.env, host="mock")
        self.db = DatabaseRedis(environ.env, host="mock")
        self.observer = FakeObserver()

        self.orig_db = environ.env.db
        self.orig_cache = environ.env.cache
        self.orig_observer = environ.env.observer

        environ.env.cache = self.cache
        environ.env.db = self.db
        environ.env.observer = self.observer

        self.resource = CreateRoomResource()
        self.resource.request = FakeRequest()
        FakeRequest.should_fail = False

        self.online_users = {
            CreateRoomTest.USER_ID: [str(uuid())]
        }
        self.original_get_sids_for_user = self.db.get_sids_for_user
        self.db.get_sids_for_user = lambda uid: self.online_users[uid]

    def tearDown(self) -> None:
        """
        need to monkey patch the originals back again, otherwise it'll mess up upcoming tests
        """
        self.db.get_sids_for_user = self.original_get_sids_for_user

        environ.env.db = self.orig_db
        environ.env.cache = self.orig_cache
        environ.env.observer = self.orig_observer

    def test_do_get_no_cache(self):
        self.assertEqual(0, len(self.observer.events))

        room_id = self.resource._do_post(
            room_name=CreateRoomTest.ROOM_NAME,
            user_ids=[CreateRoomTest.USER_ID],
            owner_id=CreateRoomTest.USER_ID,
            owner_name="admin",
            channel_id=None
        )

        # should be created
        self.assertIsNotNone(room_id)

        # join event should have been sent
        self.assertEqual(1, len(self.observer.events))
