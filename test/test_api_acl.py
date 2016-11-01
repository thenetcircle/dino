from activitystreams import parse as as_parser

from dino import api
from test.utils import BaseTest


class ApiAclTest(BaseTest):
    def setUp(self):
        super(ApiAclTest, self).setUp()
        self.set_owner()

    def test_get_acl(self):
        acl_type = 'gender'
        acl_value = 'm,f'

        self.set_acl({acl_type: acl_value})

        response_data = api.on_get_acl(self.activity_for_get_acl())
        self.assertEqual(response_data[0], 200)

        activity = as_parser(response_data[1])  # 0 is the status_code, 1 is the data (activity stream)

        self.assertEqual(activity.object.attachments[0].object_type, acl_type)
        self.assertEqual(activity.object.attachments[0].content, acl_value)

    def test_get_acl_missing_actor_id(self):
        acl_type = 'gender'
        acl_value = 'm,f'

        self.set_acl({acl_type: acl_value})

        response_data = api.on_get_acl({
            'actor': {
            },
            'target': {
                'id': ApiAclTest.ROOM_ID,
                'objectType': 'room'
            },
            'verb': 'list'
        })

        self.assertEqual(response_data[0], 400)

    def test_set_acl_one_acl(self):
        acl_type = 'gender'
        acl_value = 'm,f'

        acls_decoded = self.get_acl_after_set([{
            'objectType': acl_type,
            'content': acl_value
        }])

        self.assertEqual(len(acls_decoded), 1)
        self.assertTrue(acl_type in acls_decoded.keys())
        self.assertEqual(acls_decoded[acl_type], acl_value)

    def test_set_acl_missing_actor_id_returns_400(self):
        acl_type = 'gender'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value
        }])

        del activity['actor']['id']
        response_data = api.on_set_acl(activity)
        self.assertEqual(response_data[0], 400)

    def test_set_acl_not_owner_returns_code_400(self):
        acl_type = 'gender'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value
        }])

        self.remove_owner()
        response_data = api.on_set_acl(activity)
        self.assertEqual(response_data[0], 400)

    def test_set_acl_unknown_type(self):
        acl_type = 'unknown'
        acl_value = 'm,f'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value
        }])

        response_data = api.on_set_acl(activity)
        self.assertEqual(response_data[0], 400)

    def test_set_acl_invalid_value(self):
        acl_type = 'gender'
        acl_value = 'm,999'

        activity = self.activity_for_set_acl([{
            'objectType': acl_type,
            'content': acl_value
        }])

        response_data = api.on_set_acl(activity)
        self.assertEqual(response_data[0], 400)

    def test_set_acl_two_acl(self):
        acl_tuples = [('gender', 'm,f'), ('image', 'y')]
        attachments = list()
        for acl_type, acl_value in acl_tuples:
            attachments.append({'objectType': acl_type, 'content': acl_value})

        acls_decoded = self.get_acl_after_set(attachments)

        self.assertEqual(len(acls_decoded), 2)
        for acl_type, acl_value in acl_tuples:
            self.assertTrue(acl_type in acls_decoded.keys())
            self.assertEqual(acls_decoded[acl_type], acl_value)

    def test_set_acl_add_to_existing(self):
        acl_tuples = [('gender', 'm,f'), ('image', 'y'), ('membership', '1,2,3')]
        self.set_acl({'gender': 'm,f', 'image': 'y'})

        acls_decoded = self.get_acl_after_set([{
            'objectType': 'membership',
            'content': '1,2,3'
        }])

        self.assertEqual(len(acls_decoded), 3)
        for acl_type, acl_value in acl_tuples:
            self.assertTrue(acl_type in acls_decoded.keys())
            self.assertEqual(acls_decoded[acl_type], acl_value)

    def test_set_acl_remove_from_existing(self):
        acl_tuples = [('gender', 'm,f'), ('image', 'y')]
        self.set_acl({'gender': 'm,f', 'image': 'y', 'membership': '1,2,3'})

        acls_decoded = self.get_acl_after_set([{
            'objectType': 'membership',
            'content': ''
        }])

        self.assertEqual(len(acls_decoded), 2)
        for acl_type, acl_value in acl_tuples:
            self.assertTrue(acl_type in acls_decoded.keys())
            self.assertEqual(acls_decoded[acl_type], acl_value)

    def test_set_acl_remove_only_one(self):
        self.set_acl({'gender': 'm,f'})

        activity = self.activity_for_set_acl([{
            'objectType': 'gender',
            'content': ''
        }])

        response_data = api.on_set_acl(activity)
        self.assertEqual(response_data[0], 200)

        acls = self.get_acls()
        self.assertEqual(len(acls), 0)

    def test_set_acl_remove_non_existing(self):
        activity = self.activity_for_set_acl([{
            'objectType': 'gender',
            'content': ''
        }])

        response_data = api.on_set_acl(activity)
        self.assertEqual(response_data[0], 200)

        acls = self.get_acls()
        self.assertEqual(len(acls), 0)

    def get_acl_after_set(self, attachments):
        activity = self.activity_for_set_acl(attachments)

        response_data = api.on_set_acl(activity)
        self.assertEqual(response_data[0], 200)

        acls = self.get_acls()

        # need to decode since redis will store in byte arrays
        acls_decoded = dict()
        for acl_key, acl_val in acls.items():
            acls_decoded[str(acl_key, 'utf-8')] = str(acl_val, 'utf-8')

        return acls_decoded
