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

from test.base import BaseTest
from dino import api
import time
from activitystreams import parse as as_parser

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class SendMessageTest(BaseTest):
    def setUp(self):
        super(SendMessageTest, self).setUp()

        act = self.activity_for_join(BaseTest.USER_ID, BaseTest.ROOM_ID)
        api.on_join(act, as_parser(act))

    def test_send_private_message(self):
        act = self.activity_for_join(BaseTest.OTHER_USER_ID, BaseTest.ROOM_ID)
        api.on_join(act, as_parser(act))

        act = self.activity_for_message('this is a message')
        act['actor']['id'] = BaseTest.OTHER_USER_ID
        act['target']['id'] = BaseTest.ROOM_ID
        act['target']['objectType'] = 'private'

        api.on_message(act, as_parser(act))

        # make sure hooks have fired, async
        time.sleep(0.05)

        self.assertIsNotNone(self.msgs_sent.get(BaseTest.ROOM_ID))

    def test_send_room_message(self):
        act = self.activity_for_join(BaseTest.OTHER_USER_ID, BaseTest.ROOM_ID)
        api.on_join(act, as_parser(act))

        act = self.activity_for_message('this is a message')
        act['actor']['id'] = BaseTest.OTHER_USER_ID
        act['target']['objectType'] = 'room'

        api.on_message(act, as_parser(act))

        # make sure hooks have fired, async
        time.sleep(0.05)

        self.assertIsNotNone(self.msgs_sent.get(BaseTest.ROOM_ID))
