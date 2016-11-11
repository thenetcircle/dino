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


class RequestHistoryTest(BaseTest):
    def setUp(self):
        super(RequestHistoryTest, self).setUp()
        self.create_channel_and_room()

    def test_history(self):
        act = self.activity_for_history()
        response_data = request.on_history(as_parser(act))
        self.assertEqual(True, response_data[0])

    def test_history_no_target_id(self):
        act = self.activity_for_history(skip={'target_id'})
        response_data = request.on_history(as_parser(act))
        self.assertEqual(False, response_data[0])

    def test_history_not_allowed_not_owner_not_in_room_age(self):
        self.leave_room()
        self.remove_owner()
        self.remove_owner_channel()
        self.set_acl_single('history|age', str(int(BaseTest.AGE) + 10) + ':')
        act = self.activity_for_history()
        response_data = request.on_history(as_parser(act))
        self.assertEqual(False, response_data[0])

    def test_history_not_allowed_not_owner_in_room(self):
        self.join_room()
        self.remove_owner()
        self.remove_owner_channel()
        self.set_acl_single('history|age', str(int(BaseTest.AGE) + 10) + ':')
        act = self.activity_for_history()
        response_data = request.on_history(as_parser(act))
        self.assertEqual(False, response_data[0])

    def test_history_allowed_owner_not_in_room(self):
        self.leave_room()
        self.set_owner()
        self.set_acl_single('history|sameroom', '')
        act = self.activity_for_history()
        response_data = request.on_history(as_parser(act))
        self.assertEqual(True, response_data[0])

    def test_history_not_allowed_not_owner_not_in_room_sameroom(self):
        self.leave_room()
        self.remove_owner()
        self.remove_owner_channel()
        self.set_acl_single('history|sameroom', '')
        act = self.activity_for_history()
        response_data = request.on_history(as_parser(act))
        self.assertEqual(False, response_data[0])

    def test_history_not_allowed_owner_in_room(self):
        self.join_room()
        self.set_owner()
        self.set_acl_single('history|age', str(int(BaseTest.AGE) + 10) + ':')
        act = self.activity_for_history()
        response_data = request.on_history(as_parser(act))
        self.assertEqual(True, response_data[0])

    def test_history_allowed_not_owner_not_in_room(self):
        self.leave_room()
        self.remove_owner()
        self.remove_owner_channel()
        act = self.activity_for_history()
        response_data = request.on_history(as_parser(act))
        self.assertEqual(True, response_data[0])

    def test_history_allowed_not_owner_in_room(self):
        self.join_room()
        self.remove_owner()
        self.remove_owner_channel()
        act = self.activity_for_history()
        response_data = request.on_history(as_parser(act))
        self.assertEqual(True, response_data[0])

    def test_history_allowed_owner_in_room(self):
        self.join_room()
        self.set_owner()
        act = self.activity_for_history()
        response_data = request.on_history(as_parser(act))
        self.assertEqual(True, response_data[0])
