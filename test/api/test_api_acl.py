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

import dino
from dino.config import ApiActions

from test.base import BaseTest


class ApiAclTest(BaseTest):
    def setUp(self):
        super(ApiAclTest, self).setUp()
        self.set_owner()

    def test_get_acl(self):
        acl_type = 'gender'
        acl_value = 'm,f'

        self.set_acl({ApiActions.JOIN: {acl_type: acl_value}})

        act = self.activity_for_get_acl()
        response_data = dino.api.on_get_acl(act, as_parser(act))
        self.assertEqual(response_data[0], 200)

        activity = as_parser(response_data[1])  # 0 is the status_code, 1 is the data (activity stream)

        self.assertEqual(activity.object.attachments[0].object_type, acl_type)
        self.assertEqual(activity.object.attachments[0].content, acl_value)

    def test_set_acl_one_acl(self):
        acl_type = 'gender'
        acl_value = 'm,f'

        acls_decoded = self.get_acl_after_set([{
            'objectType': acl_type,
            'content': acl_value,
            'summary': ApiActions.JOIN
        }])

        self.assertEqual(len(acls_decoded), 1)
        self.assertTrue(acl_type in acls_decoded.keys())
        self.assertEqual(acls_decoded[acl_type], acl_value)

    def test_set_acl_two_acl(self):
        acl_tuples = [('gender', 'm,f'), ('image', 'y')]
        attachments = list()
        for acl_type, acl_value in acl_tuples:
            attachments.append({'objectType': acl_type, 'content': acl_value, 'summary': ApiActions.JOIN})

        acls_decoded = self.get_acl_after_set(attachments)

        self.assertEqual(len(acls_decoded), 2)
        for acl_type, acl_value in acl_tuples:
            self.assertTrue(acl_type in acls_decoded.keys())
            self.assertEqual(acls_decoded[acl_type], acl_value)

    def test_set_acl_add_to_existing(self):
        acl_tuples = [('gender', 'm,f'), ('image', 'y'), ('membership', '1,2,3')]
        self.set_acl({ApiActions.JOIN: {'gender': 'm,f', 'image': 'y'}})

        acls_decoded = self.get_acl_after_set([{
            'objectType': 'membership',
            'content': '1,2,3',
            'summary': ApiActions.JOIN
        }])

        self.assertEqual(len(acls_decoded), 3)
        for acl_type, acl_value in acl_tuples:
            self.assertTrue(acl_type in acls_decoded.keys())
            self.assertEqual(acls_decoded[acl_type], acl_value)

    def test_set_acl_remove_from_existing(self):
        acl_tuples = [('gender', 'm,f'), ('image', 'y')]
        self.set_acl({ApiActions.JOIN: {'gender': 'm,f', 'image': 'y', 'membership': '1,2,3'}})

        acls_decoded = self.get_acl_after_set([{
            'objectType': 'membership',
            'content': '',
            'summary': ApiActions.JOIN
        }])

        self.assertEqual(len(acls_decoded), 2)
        for acl_type, acl_value in acl_tuples:
            self.assertTrue(acl_type in acls_decoded.keys())
            self.assertEqual(acls_decoded[acl_type], acl_value)

    def test_set_acl_remove_only_one(self):
        self.set_acl({ApiActions.JOIN: {'gender': 'm,f'}})

        activity = self.activity_for_set_acl([{
            'objectType': 'gender',
            'content': '',
            'summary': ApiActions.JOIN
        }])

        response_data = dino.api.on_set_acl(activity, as_parser(activity))
        self.assertEqual(response_data[0], 200)

        acls = self.get_acls_for_join()
        self.assertEqual(len(acls), 0)

    def test_set_acl_remove_non_existing(self):
        activity = self.activity_for_set_acl([{
            'objectType': 'gender',
            'content': '',
            'summary': ApiActions.JOIN
        }])

        response_data = dino.api.on_set_acl(activity, as_parser(activity))
        self.assertEqual(response_data[0], 200)

        acls = self.get_acls()
        self.assertEqual(len(acls), 0)

    def get_acl_after_set(self, attachments):
        activity = self.activity_for_set_acl(attachments)

        response_data = dino.api.on_set_acl(activity, as_parser(activity))
        self.assertEqual(response_data[0], 200)
        return self.get_acls().get(ApiActions.JOIN)
