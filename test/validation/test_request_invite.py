#!/usr/bin/env python

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
from activitystreams import parse as as_parser

from dino.validation import request

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class RequestInviteTest(TestCase):
    def test_invite(self):
        is_valid, code, msg = request.on_invite(as_parser(self.json_act()))
        self.assertTrue(is_valid)

    def json_act(self):
        return {
            'verb': 'list'
        }
