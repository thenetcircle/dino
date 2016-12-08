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

from dino.rest.resources.base import BaseResource

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class TestBaseResource(TestCase):
    def setUp(self):
        self.resource = BaseResource()

    def test_do_get(self):
        self.assertRaises(NotImplementedError, self.resource.do_get)

    def test_get_lru_method(self):
        self.assertRaises(NotImplementedError, self.resource._get_lru_method)

    def test_get_last_cleared(self):
        self.assertRaises(NotImplementedError, self.resource._get_last_cleared)

    def test_set_last_cleared(self):
        self.assertRaises(NotImplementedError, self.resource._set_last_cleared, 1234)
