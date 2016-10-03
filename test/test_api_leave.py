from uuid import uuid4 as uuid

from gridchat import api
from test.utils import BaseTest


class ApiLeaveTest(BaseTest):
    def test_leave_when_not_in_room_is_okay(self):
        self.assert_in_room(False)
        self.assert_leave_succeeds()
        self.assert_in_room(False)

    def test_leave_when_in_room_is_okay(self):
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)
        self.assert_leave_succeeds()
        self.assert_in_room(False)

    def test_leave_without_actor_id_status_code_400(self):
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        activity = self.activity_for_leave()
        del activity['actor']['id']
        response_data = api.on_leave(activity)
        self.assertEqual(400, response_data[0])

    def test_leave_without_actor_status_code_400(self):
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        activity = self.activity_for_leave(skip={'actor'})
        response_data = api.on_leave(activity)
        self.assertEqual(400, response_data[0])

    def test_leave_without_target_id(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        data = self.activity_for_leave(skip={'target'})
        response_data = api.on_leave(data)

        self.assertEqual(400, response_data[0])
        self.assert_in_room(True)

    def test_leave_different_room_stays_in_current(self):
        self.assert_in_room(False)
        api.on_join(self.activity_for_join())
        self.assert_in_room(True)

        tmp_room_id = str(uuid())
        self.set_room_name(tmp_room_id, tmp_room_id)
        data = self.activity_for_leave()
        data['target']['id'] = tmp_room_id
        response_data = api.on_leave(data)

        self.assertEqual(200, response_data[0])
        self.assert_in_room(True)

    def assert_leave_succeeds(self):
        self.assertEqual(200, self.response_code_for_leave())

    def response_code_for_leave(self, data=None):
        return self.leave_room(data)[0]
