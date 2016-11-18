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

from uuid import uuid4 as uuid
from activitystreams import parse as as_parser

from dino import api
from dino.validation import request
from test.base import BaseTest


class RequestLeaveTest(BaseTest):
    def test_leave_when_not_in_room_is_okay(self):
        self.assert_in_room(False)
        self.assert_leave_succeeds()
        self.assert_in_room(False)

    def test_leave_when_in_room_is_okay(self):
        act = self.activity_for_join()
        api.on_join(act, as_parser(act))
        self.assert_in_room(True)
        self.assert_leave_succeeds()

    def test_leave_without_target_id(self):
        act = self.activity_for_join()
        self.assert_in_room(False)
        api.on_join(act, as_parser(act))

        act = self.activity_for_leave(skip={'target'})
        self.assertFalse(request.on_leave(as_parser(act))[0])

    def assert_leave_succeeds(self):
        self.assertTrue(request.on_leave(as_parser(self.activity_for_leave()))[0])

    def response_code_for_leave(self, data=None):
        return self.leave_room(data)[0]
