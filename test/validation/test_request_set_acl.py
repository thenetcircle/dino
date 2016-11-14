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

from activitystreams import parse as as_parser

from dino.config import ApiActions
from dino.validation import request

from test.utils import BaseTest


class RequestSetAclTest(BaseTest):
    def setUp(self):
        super(RequestSetAclTest, self).setUp()
        self.set_owner()

    def test_get_acl(self):
        act = self.activity_for_get_acl()
        self.assertTrue(request.on_get_acl(as_parser(act))[0])

    def test_set_acl_not_owner_returns_code_400(self):
        acl_type = 'gender'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value,
            'summary': ApiActions.JOIN
        }])

        self.remove_owner()
        self.assertFalse(request.on_set_acl(as_parser(activity))[0])

    def test_set_acl_unknown_type(self):
        acl_type = 'unknown'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value
        }])

        self.assertFalse(request.on_set_acl(as_parser(activity))[0])

    def test_set_acl_invalid_value(self):
        acl_type = 'gender'
        acl_value = 'm,999'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value,
            'summary': ApiActions.JOIN
        }])

        self.assertFalse(request.on_set_acl(as_parser(activity))[0])

    def test_set_acl_two_acl(self):
        acl_tuples = [('gender', 'm,f'), ('image', 'y')]
        attachments = list()
        for acl_type, acl_value in acl_tuples:
            attachments.append({'objectType': acl_type, 'content': acl_value, 'summary': ApiActions.JOIN})

        self.assertTrue(request.on_set_acl(as_parser(self.activity_for_set_acl(attachments)))[0])

    def test_set_acl_remove(self):
        activity = self.activity_for_set_acl([{
            'objectType': 'membership',
            'content': '',
            'summary': ApiActions.JOIN
        }])

        self.assertTrue(request.on_set_acl(as_parser(activity))[0])
