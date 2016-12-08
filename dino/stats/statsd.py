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

from zope.interface import implementer

from dino.stats import IStats
from dino.config import ConfigKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


@implementer(IStats)
class MockStatsd(object):
    def __init__(self):
        self.vals = dict()
        self.timings = dict()

    def incr(self, key: str) -> None:
        if key not in self.vals:
            self.vals[key] = 1
        else:
            self.vals[key] += 1

    def decr(self, key: str) -> None:
        if key not in self.vals:
            self.vals[key] = -1
        else:
            self.vals[key] -= 1

    def timing(self, key: str, ms: int):
        self.timings[key] = ms

    def gauge(self, key: str, value: int):
        self.vals[key] = value


@implementer(IStats)
class StatsdService(object):
    def __init__(self, env):
        self.env = env

        conf = env.config.get(ConfigKeys.STATS_SERVICE)
        host = conf.get(ConfigKeys.HOST)

        if env.config.get(ConfigKeys.TESTING, False) or host == 'mock':
            self.statsd = MockStatsd()
        else:
            import statsd

            port = conf.get(ConfigKeys.PORT)
            prefix = 'dino'
            if ConfigKeys.PREFIX in conf:
                prefix = conf.get(ConfigKeys.PREFIX)
            if ConfigKeys.INCLUDE_HOST_NAME in conf:
                include_host_name = conf.get(ConfigKeys.INCLUDE_HOST_NAME)
                if include_host_name is not None and str(include_host_name).strip().lower() in ['yes', '1', 'true']:
                    import socket
                    prefix = '%s.%s' % (prefix, socket.gethostname())

            self.statsd = statsd.StatsClient(host, int(port), prefix=prefix)

    def incr(self, key: str) -> None:
        self.statsd.incr(key)

    def decr(self, key: str) -> None:
        self.statsd.decr(key)

    def timing(self, key: str, ms: float):
        self.statsd.timing(key, ms)

    def gauge(self, key: str, value: int):
        self.statsd.gauge(key, value)
