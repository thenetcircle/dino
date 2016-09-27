import unittest
import fakeredis
from uuid import uuid4 as uuid

from gridchat.env import env, ConfigKeys
from gridchat import rkeys
from gridchat import utils

redis = fakeredis.FakeStrictRedis()
env.config = dict()
env.config[ConfigKeys.REDIS] = redis
env.config[ConfigKeys.TESTING] = True
env.config[ConfigKeys.SESSION] = dict()
env.config[ConfigKeys.SESSION]['user_id'] = '1234'


class UtilsTest(unittest.TestCase):
    ROOM_ID = str(uuid())
    ROOM_NAME = 'Shanghai'

    def setUp(self):
        redis.flushall()
        env.config[ConfigKeys.REDIS] = redis

    def test_get_room_name(self):
        self.set_room_name()
        name = utils.get_room_name(env.config.get(ConfigKeys.REDIS), UtilsTest.ROOM_ID)
        self.assertEqual(name, UtilsTest.ROOM_NAME)

    def test_get_room_name_non_existing(self):
        name = utils.get_room_name(env.config.get(ConfigKeys.REDIS), UtilsTest.ROOM_ID)
        self.assertTrue(isinstance(name, str))
        self.assertEqual(len(str(uuid())), len(name))

    def set_room_name(self):
        redis.set(rkeys.room_name_for_id(UtilsTest.ROOM_ID), UtilsTest.ROOM_NAME)
