import unittest
import fakeredis
from uuid import uuid4 as uuid

from gridchat.env import env, ConfigKeys
from gridchat import rkeys
from gridchat import utils

from test.utils import BaseTest


class UtilsTest(BaseTest):
    def test_get_room_name(self):
        self.set_room_name()
        name = utils.get_room_name(env.config.get(ConfigKeys.REDIS), UtilsTest.ROOM_ID)
        self.assertEqual(name, UtilsTest.ROOM_NAME)

    def test_get_room_name_non_existing(self):
        name = utils.get_room_name(env.config.get(ConfigKeys.REDIS), UtilsTest.ROOM_ID)
        self.assertTrue(isinstance(name, str))
        self.assertEqual(len(UtilsTest.ROOM_NAME), len(name))
