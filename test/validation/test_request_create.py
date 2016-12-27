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
from activitystreams import parse as as_parser
from uuid import uuid4 as uuid

from dino.validation import request
from dino.config import ErrorCodes
from dino.utils import b64e

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class RequestCreateTest(BaseTest):
    def test_create(self):
        is_valid, code, msg = request.on_create(as_parser(self.activity_for_create()))
        self.assertTrue(is_valid)

    def test_create_missing_target_display_name(self):
        activity = self.activity_for_create()
        del activity['target']
        is_valid, code, msg = request.on_create(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.MISSING_TARGET_DISPLAY_NAME)

    def test_create_display_name_not_base64(self):
        activity = self.activity_for_create()
        activity['target']['displayName'] = 'this is not base64'
        is_valid, code, msg = request.on_create(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.NOT_BASE64)

    def test_create_no_object_url(self):
        activity = self.activity_for_create()
        del activity['object']
        is_valid, code, msg = request.on_create(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.MISSING_OBJECT_URL)

    def test_create_no_such_channel(self):
        activity = self.activity_for_create()
        activity['object']['url'] = str(uuid())
        is_valid, code, msg = request.on_create(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.NO_SUCH_CHANNEL)

    def test_create_restricted_name(self):
        activity = self.activity_for_create()
        activity['target']['displayName'] = b64e('admins')
        is_valid, code, msg = request.on_create(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.NOT_ALLOWED)

    def test_create_blank_name(self):
        activity = self.activity_for_create()
        activity['target']['displayName'] = ''
        is_valid, code, msg = request.on_create(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.MISSING_TARGET_DISPLAY_NAME)

    def test_create_name_exists(self):
        self.create_channel_and_room()
        activity = self.activity_for_create()
        is_valid, code, msg = request.on_create(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.ROOM_ALREADY_EXISTS)

    def test_create_missing_actor_id(self):
        activity = self.activity_for_create()
        del activity['actor']['id']
        is_valid, code, msg = request.on_create(as_parser(activity))
        self.assertFalse(is_valid)
