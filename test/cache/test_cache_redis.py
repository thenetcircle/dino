#!/usr/bin/env python

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest import TestCase
from dino.environ import GNEnvironment, ConfigDict, ConfigKeys
from dino.cache.redis import CacheRedis

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class CacheRedisTest(TestCase):
    class FakeEnv(GNEnvironment):
        def __init__(self):
            super(CacheRedisTest.FakeEnv, self).__init__(None, ConfigDict(), skip_init=True)
            self.config = ConfigDict()
            self.config.set(ConfigKeys.TESTING, True)
            self.cache = CacheRedis(self, 'mock')
            self.session = dict()

    USER_ID = '8888'

    def setUp(self):
        self.env = CacheRedisTest.FakeEnv()
        self.cache = self.env.cache

    def test_set_user_status(self):
        self.cache.set_user_status(CacheRedisTest.USER_ID, '1')
        self.assertEqual('1', self.cache.get_user_status(CacheRedisTest.USER_ID))
