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

from dino.stats.statsd import StatsdService
from dino.config import ConfigKeys
from dino.environ import ConfigDict

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class FakeEnv(object):
    def __init__(self):
        self.config = ConfigDict({
            ConfigKeys.STATS_SERVICE: {
                ConfigKeys.HOST: 'mock'
            }
        })


class StatsdTest(TestCase):
    def setUp(self):
        self.statsd = StatsdService(FakeEnv())

    def test_integration(self):
        # statsd is fire-and-forget UDP so doesn't matter if nothing is listening here
        env = FakeEnv()
        env.config = ConfigDict({
            ConfigKeys.STATS_SERVICE: {
                ConfigKeys.HOST: '0.0.0.0',
                ConfigKeys.INCLUDE_HOST_NAME: 'true',
                ConfigKeys.PORT: 20500,
                ConfigKeys.PREFIX: 'dino'
            }
        })
        self.statsd = StatsdService(env)
        self.statsd.incr('foo')

    def test_gauge(self):
        self.statsd.gauge('foo', 12)
        self.assertEqual(12, self.statsd.statsd.vals['foo'])

    def test_set(self):
        self.statsd.set('foo', 12)
        self.assertEqual(12, self.statsd.statsd.vals['foo'])

    def test_incr(self):
        self.statsd.incr('foo')
        self.assertEqual(1, self.statsd.statsd.vals['foo'])
        self.statsd.incr('foo')
        self.assertEqual(2, self.statsd.statsd.vals['foo'])

    def test_decr(self):
        self.statsd.decr('foo')
        self.assertEqual(-1, self.statsd.statsd.vals['foo'])
        self.statsd.decr('foo')
        self.assertEqual(-2, self.statsd.statsd.vals['foo'])

    def test_timing(self):
        self.statsd.timing('foo', 1234)
        self.assertEqual(1234, self.statsd.statsd.timings['foo'])
