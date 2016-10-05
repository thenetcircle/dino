import unittest
import fakeredis
from uuid import uuid4 as uuid

from dino.env import env, ConfigKeys
from dino import rkeys
from dino import utils

from test.utils import BaseTest

"""
class UtilsTest(BaseTest):
    def test_get_room_name(self):
        self.set_room_name()
        name = utils.get_room_name(env.config.get(ConfigKeys.REDIS), UtilsTest.ROOM_ID)
        self.assertEqual(name, UtilsTest.ROOM_NAME)

    def test_get_room_name_non_existing(self):
        self.remove_room()
        name = utils.get_room_name(env.config.get(ConfigKeys.REDIS), UtilsTest.ROOM_ID)
        self.assertTrue(isinstance(name, str))
        self.assertEqual(len(str(uuid())), len(name))
"""
