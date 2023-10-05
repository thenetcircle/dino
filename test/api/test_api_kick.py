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

from test.base import BaseTest

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class ApiKickTest(BaseTest):
    def test_kick(self):
        from dino import api
        self.create_and_join_room()
        self.set_owner()
        act = self.activity_for_kick()
        self.assertEqual(200, api.on_kick(act, as_parser(act))[0])

    def activity_for_kick(self):
        return {
            'actor': {
                'id': ApiKickTest.USER_ID,
                'content': ApiKickTest.USER_NAME
            },
            'verb': 'kick',
            'object': {
                'id': ApiKickTest.OTHER_USER_ID,
                'content': ApiKickTest.OTHER_USER_NAME
            },
            'target': {
                'id': ApiKickTest.ROOM_ID,
                'displayName': ApiKickTest.ROOM_NAME
            }
        }
