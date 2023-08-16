from datetime import datetime
from datetime import timedelta
from unittest import TestCase

from dino import environ
from dino.config import ConfigKeys
from dino.rest.resources.mute import MuteResource


class FakeDb(object):
    _muted = dict()

    def type_of_rooms_in_channel(self, _):
        return "temporary"

    def get_muted_users(self):
        return FakeDb._muted

    def get_mutes_for_user(self, user_id):
        return  {
            'room': {
                'name': MutedUsersTest.ROOM_NAME,
                'duration': '5m',
                'timestamp': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
            }
        }


class FakeRequest(object):
    _json = dict()

    def get_json(self, silent=False):
        return FakeRequest._json


class MutedUsersTest(TestCase):
    USER_ID = '8888'
    ROOM_ID = '1234'
    ROOM_ID_2 = '4321'
    ROOM_NAME = 'cool guys'
    ROOM_NAME_2 = 'bad guys'
    CHANNEL_ID = '5555'
    CHANNEL_NAME = 'Shanghai'

    def setUp(self):
        environ.env.db = FakeDb()
        FakeDb._muted = {MutedUsersTest.USER_ID}
        self.resource = MuteResource()
        self.resource.request = FakeRequest()
        FakeRequest._json = {
            'users': [MutedUsersTest.USER_ID]
        }

    def test_get(self):
        self.assertEqual(1, len(self.resource.do_get()))

    def test_set_last_cleared(self):
        last_cleared = self.resource._get_last_cleared()
        self.resource._set_last_cleared(datetime.utcnow()+timedelta(minutes=5))
        self.assertNotEqual(last_cleared, self.resource._get_last_cleared())

    def test_get_lru_method(self):
        func = self.resource._get_lru_method()
        self.assertTrue(callable(func))
