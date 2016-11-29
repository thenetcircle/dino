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

import os
os.environ['ENVIRONMENT'] = 'test'

from dino import api
from test.base import BaseTest

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class ApiInviteTest(BaseTest):
    def test_invite(self):
        self.create_and_join_room()
        self.set_owner()
        act = self.activity_for_invite()
        self.assertEqual(200, api.on_invite(act, as_parser(act))[0])

    def activity_for_invite(self):
        return {
            'actor': {
                'id': BaseTest.USER_ID,
                'content': BaseTest.USER_NAME,
                'url': BaseTest.ROOM_ID
            },
            'verb': 'invite',
            'object': {
                'id': BaseTest.OTHER_USER_ID,
                'content': BaseTest.OTHER_USER_NAME,
                'url': BaseTest.CHANNEL_ID
            },
            'target': {
                'id': BaseTest.ROOM_ID,
                'displayName': BaseTest.ROOM_NAME
            }
        }
