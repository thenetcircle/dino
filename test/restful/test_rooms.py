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
from datetime import datetime
from datetime import timedelta

from dino import environ
from dino.config import ConfigKeys
from dino.rest.resources.banned import BannedResource

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

from dino.rest.resources.rooms import RoomsResource


class FakeDb(object):
    def type_of_rooms_in_channel(self, _):
        return "temporary"

    def set_all_rooms(self):
        pass

    def get_all_rooms(self):
        return [
            {
                'id': '1',
                'status': 'private',
                'name': 'foo',
                'channel': 'foo channel'
            },
            {
                'id': '2',
                'status': 'public',
                'name': 'bar',
                'channel': 'bar channel'
            },
        ]


class RoomsTest(TestCase):
    def setUp(self):
        environ.env.db = FakeDb()
        self.resource = RoomsResource()

    def test_get(self):
        self.assertEqual(2, len(self.resource.do_get()))

    def test_set_last_cleared(self):
        last_cleared = self.resource._get_last_cleared()
        self.resource._set_last_cleared(datetime.utcnow()+timedelta(minutes=5))
        self.assertNotEqual(last_cleared, self.resource._get_last_cleared())
