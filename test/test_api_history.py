from dino import api
from test.utils import BaseTest
from activitystreams import parse as as_parser
from strict_rfc3339 import validate_rfc3339 as validate_timestamp


class ApiHistoryTest(BaseTest):
    def test_history(self):
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(200, response_data[0])

    def test_history_no_actor_id(self):
        response_data = api.on_history(self.activity_for_history(skip={'user_id'}))
        self.assertEqual(400, response_data[0])

    def test_history_no_target_id(self):
        response_data = api.on_history(self.activity_for_history(skip={'target_id'}))
        self.assertEqual(400, response_data[0])

    def test_history_not_allowed_not_owner_not_in_room(self):
        self.leave_room()
        self.remove_owner()
        self.set_acl_single('age', str(int(BaseTest.AGE) + 10) + ':')
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(400, response_data[0])

    def test_history_not_allowed_not_owner_in_room(self):
        self.join_room()
        self.remove_owner()
        self.set_acl_single('age', str(int(BaseTest.AGE) + 10) + ':')
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(400, response_data[0])

    def test_history_not_allowed_owner_not_in_room(self):
        self.leave_room()
        self.set_owner()
        self.set_acl_single('age', str(int(BaseTest.AGE) + 10) + ':')
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(200, response_data[0])

    def test_history_not_allowed_owner_in_room(self):
        self.join_room()
        self.set_owner()
        self.set_acl_single('age', str(int(BaseTest.AGE) + 10) + ':')
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(200, response_data[0])

    def test_history_allowed_not_owner_not_in_room(self):
        self.leave_room()
        self.remove_owner()
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(200, response_data[0])

    def test_history_allowed_not_owner_in_room(self):
        self.join_room()
        self.remove_owner()
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(200, response_data[0])

    def test_history_allowed_owner_not_in_room(self):
        self.leave_room()
        self.set_owner()
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(200, response_data[0])

    def test_history_allowed_owner_in_room(self):
        self.join_room()
        self.set_owner()
        response_data = api.on_history(self.activity_for_history())
        self.assertEqual(200, response_data[0])

    def test_history_contains_one_sent_message(self):
        self.join_room()
        self.remove_owner()

        message = 'my message'
        self.send_message(message)

        response_data = api.on_history(self.activity_for_history())
        activity = as_parser(response_data[1])
        self.assertEqual(1, len(activity.object.attachments))

    def test_history_contains_two_sent_message(self):
        self.join_room()
        self.remove_owner()

        message = 'my message'
        self.send_message(message)
        self.send_message(message)

        response_data = api.on_history(self.activity_for_history())
        activity = as_parser(response_data[1])
        self.assertEqual(2, len(activity.object.attachments))

    def test_history_contains_correct_sent_message(self):
        self.join_room()
        self.remove_owner()

        message = 'my message'
        self.send_message(message)

        response_data = api.on_history(self.activity_for_history())
        activity = as_parser(response_data[1])
        self.assertEqual(message, activity.object.attachments[0].content)

    def test_history_contains_timestamp(self):
        self.join_room()
        self.remove_owner()
        self.send_message('my message')

        response_data = api.on_history(self.activity_for_history())
        activity = as_parser(response_data[1])
        self.assertIsNotNone(activity.object.attachments[0].published)

    def test_history_contains_id(self):
        self.join_room()
        self.remove_owner()
        self.send_message('my message')

        response_data = api.on_history(self.activity_for_history())
        activity = as_parser(response_data[1])
        self.assertIsNotNone(activity.object.attachments[0].id)

    def test_history_contains_correct_user_name(self):
        self.join_room()
        self.remove_owner()
        self.send_message('my message')

        response_data = api.on_history(self.activity_for_history())
        activity = as_parser(response_data[1])
        self.assertEqual(BaseTest.USER_NAME, activity.object.attachments[0].summary)

    def test_history_contains_valid_timestamp(self):
        self.join_room()
        self.remove_owner()
        self.send_message('my message')

        response_data = api.on_history(self.activity_for_history())
        activity = as_parser(response_data[1])
        self.assertTrue(validate_timestamp(activity.object.attachments[0].published))
