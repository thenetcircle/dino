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

from dino import api
from test.utils import BaseTest


class ApiStatusTest(BaseTest):
    def test_status_online(self):
        response_data = api.on_status(self.activity_for_status('online'))
        self.assertEqual(200, response_data[0])

    def test_status_invisible(self):
        response_data = api.on_status(self.activity_for_status('invisible'))
        self.assertEqual(200, response_data[0])

    def test_status_offline(self):
        response_data = api.on_status(self.activity_for_status('offline'))
        self.assertEqual(200, response_data[0])
