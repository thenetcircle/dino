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

from activitystreams import parse as as_parser

from dino.validation import request
from test.base import BaseTest
from dino.config import SessionKeys


class RequestStatusTest(BaseTest):
    def test_status_online(self):
        response_data = request.on_status(as_parser(self.activity_for_status('online')))
        self.assertEqual(True, response_data[0])

    def test_status_invisible(self):
        response_data = request.on_status(as_parser(self.activity_for_status('invisible')))
        self.assertEqual(True, response_data[0])

    def test_status_offline(self):
        response_data = request.on_status(as_parser(self.activity_for_status('offline')))
        self.assertEqual(True, response_data[0])

    def test_status_invalid(self):
        response_data = request.on_status(as_parser(self.activity_for_status('invalid')))
        self.assertEqual(False, response_data[0])

    def test_status_no_user_name_in_session(self):
        self.set_session(SessionKeys.user_name.value, None)
        response_data = request.on_status(as_parser(self.activity_for_status('online')))
        self.assertEqual(False, response_data[0])

    def test_status_change_user_id(self):
        self.set_session(SessionKeys.user_id.value, BaseTest.USER_ID + '123')
        response_data = request.on_status(as_parser(self.activity_for_status('online')))
        self.assertEqual(False, response_data[0])
