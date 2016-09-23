import unittest
import fakeredis
from pprint import pprint
from uuid import uuid4 as uuid

from gridchat.env import env, ConfigKeys
from gridchat import rkeys
from activitystreams import parse as as_parser

redis = fakeredis.FakeStrictRedis()
env.config = dict()
env.config[ConfigKeys.REDIS] = redis
env.config[ConfigKeys.TESTING] = True
env.config[ConfigKeys.SESSION] = dict()
env.config[ConfigKeys.SESSION]['user_id'] = '1234'

from gridchat import api


class ApiAclTest(unittest.TestCase):
    USER_ID = '1234'
    ROOM_ID = str(uuid())
    ROOM_NAME = 'Shanghai'

    def setUp(self):
        redis.flushall()
        redis.set(rkeys.room_name_for_id(ApiAclTest.ROOM_ID), ApiAclTest.ROOM_NAME)
        redis.sadd(rkeys.room_owners(ApiAclTest.ROOM_ID), ApiAclTest.USER_ID)

    def test_get_acl(self):
        acl_type = 'gender'
        acl_value = 'm,f'

        redis.hmset(rkeys.room_acl(ApiAclTest.ROOM_ID), {acl_type: acl_value})

        response_data = api.on_get_acl({
            'actor': {
                'id': ApiAclTest.USER_ID
            },
            'target': {
                'id': ApiAclTest.ROOM_ID
            },
            'verb': 'list'
        })

        self.assertEqual(response_data[0], 200)

        activity = as_parser(response_data[1])  # 0 is the status_code, 1 is the data (activity stream)

        self.assertEqual(activity.object.attachments[0].object_type, acl_type)
        self.assertEqual(activity.object.attachments[0].content, acl_value)

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
        redis.hmset(rkeys.room_acl(ApiAclTest.ROOM_ID), {'gender': 'm,f', 'image': 'y'})

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
        redis.hmset(rkeys.room_acl(ApiAclTest.ROOM_ID), {'gender': 'm,f', 'image': 'y', 'membership': '1,2,3'})

        acls_decoded = self.get_acl_after_set([{
            'objectType': 'membership',
            'content': ''
        }])

        self.assertEqual(len(acls_decoded), 2)
        for acl_type, acl_value in acl_tuples:
            self.assertTrue(acl_type in acls_decoded.keys())
            self.assertEqual(acls_decoded[acl_type], acl_value)

    def test_set_acl_remove_only_one(self):
        redis.hmset(rkeys.room_acl(ApiAclTest.ROOM_ID), {'gender': 'm,f'})

        activity = self.activity_for([{
            'objectType': 'gender',
            'content': ''
        }])

        response_data = api.on_set_acl(activity)
        self.assertEqual(response_data[0], 200)

        acls = redis.hgetall(rkeys.room_acl(ApiAclTest.ROOM_ID))
        self.assertEqual(len(acls), 0)

    def test_set_acl_remove_non_existing(self):
        activity = self.activity_for([{
            'objectType': 'gender',
            'content': ''
        }])

        response_data = api.on_set_acl(activity)
        self.assertEqual(response_data[0], 200)

        acls = redis.hgetall(rkeys.room_acl(ApiAclTest.ROOM_ID))
        self.assertEqual(len(acls), 0)

    def activity_for(self, attachments):
        return {
            'actor': {
                'id': ApiAclTest.USER_ID
            },
            'target': {
                'id': ApiAclTest.ROOM_ID
            },
            'verb': 'set',
            'object': {
                'objectType': 'acl',
                'attachments': attachments
            }
        }

    def get_acl_after_set(self, attachments):
        activity = self.activity_for(attachments)

        response_data = api.on_set_acl(activity)
        self.assertEqual(response_data[0], 200)

        acls = redis.hgetall(rkeys.room_acl(ApiAclTest.ROOM_ID))

        # need to decode since redis will store in byte arrays
        acls_decoded = dict()
        for acl_key, acl_val in acls.items():
            acls_decoded[str(acl_key, 'utf-8')] = str(acl_val, 'utf-8')

        return acls_decoded
