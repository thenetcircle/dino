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

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

from uuid import uuid4 as uuid
from activitystreams import parse as as_parser

from dino import api
from test.utils import BaseTest


class ApiLeaveTest(BaseTest):
    def test_leave_when_not_in_room_is_okay(self):
        self.assert_in_room(False)
        self.assert_leave_succeeds()
        self.assert_in_room(False)

    def test_leave_when_in_room_is_okay(self):
        act = self.activity_for_join()
        api.on_join(act, as_parser(act))
        self.assert_in_room(True)
        self.assert_leave_succeeds()
        self.assert_in_room(False)

    def test_leave_without_target_id(self):
        self.assert_in_room(False)
        act = self.activity_for_join()
        api.on_join(act, as_parser(act))
        self.assert_in_room(True)

        act = self.activity_for_leave(skip={'target'})
        try:
            api.on_leave(act, as_parser(act))
            self.fail('should raise exception, not target')
        except AttributeError:
            pass

    def test_leave_different_room_stays_in_current(self):
        self.assert_in_room(False)
        act = self.activity_for_join()
        api.on_join(act, as_parser(act))
        self.assert_in_room(True)

        tmp_room_id = str(uuid())
        self.set_room_name(tmp_room_id, tmp_room_id)
        data = self.activity_for_leave()
        data['target']['id'] = tmp_room_id
        response_data = api.on_leave(data, as_parser(data))

        self.assertEqual(200, response_data[0])
        self.assert_in_room(True)

    def assert_leave_succeeds(self):
        self.assertEqual(200, self.response_code_for_leave())

    def response_code_for_leave(self, data=None):
        return self.leave_room(data)[0]
