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

from test.utils import BaseTest
from activitystreams import parse as as_parser

from dino.validation import request

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class RequestCreateTest(BaseTest):
    def test_create(self):
        response_data = request.on_create(as_parser(self.activity_for_create()))
        self.assertEqual(True, response_data[0])

    def test_create_missing_target_display_name(self):
        activity = self.activity_for_create()
        del activity['target']['displayName']
        response_data = request.on_create(as_parser(activity))
        self.assertEqual(False, response_data[0])

    def test_create_missing_actor_id(self):
        activity = self.activity_for_create()
        del activity['actor']['id']
        response_data = request.on_create(as_parser(activity))
        self.assertEqual(True, response_data[0])
