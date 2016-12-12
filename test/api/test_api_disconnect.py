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
from dino.config import SessionKeys
from dino.config import ErrorCodes


class ApiDisconnectTest(BaseTest):
    def test_disconnect(self):
        response_data = api.on_disconnect()
        self.assertEqual(ErrorCodes.OK, response_data[0])

    def test_disconnect_leaves_joined_room(self):
        self.join_room()
        self.assert_in_room(True)

        api.on_disconnect()
        self.assert_in_room(False)
