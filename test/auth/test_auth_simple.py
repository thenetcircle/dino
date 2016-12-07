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

from unittest import TestCase

from dino.auth.simple import AllowAllAuth
from dino.auth.simple import DenyAllAuth

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class TestAuthSimple(TestCase):
    def test_auth_not_allowed(self):
        auth = DenyAllAuth()
        authenticated, *rest = auth.authenticate_and_populate_session('', '')
        self.assertFalse(authenticated)

    def test_auth_is_allowed(self):
        auth = AllowAllAuth()
        authenticated, *rest = auth.authenticate_and_populate_session('', '')
        self.assertTrue(authenticated)
