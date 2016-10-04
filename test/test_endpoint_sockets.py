from dino.endpoint import sockets
from dino.env import SessionKeys

from test.utils import BaseTest


class EndpointSocketsTest(BaseTest):
    def setUp(self):
        super(EndpointSocketsTest, self).setUp()
        self.assertTrue(len(BaseTest.emit_args) == 0)
        self.assertTrue(len(BaseTest.emit_kwargs) == 0)

    def test_connect(self):
        sockets.connect()
        self.assertEqual(200, self.get_emit_status_code())

    def test_disconnect(self):
        sockets.on_disconnect()
        self.assertEqual(200, self.get_emit_status_code())

    def test_join(self):
        sockets.on_join(self.activity_for_join())
        self.assertEqual(200, self.get_emit_status_code())

    def test_leave(self):
        sockets.on_join(self.activity_for_join())
        self.clear_emit_args()
        sockets.on_leave(self.activity_for_leave())
        self.assertEqual(200, self.get_emit_status_code())

    def test_history(self):
        sockets.on_history(self.activity_for_history())
        self.assertEqual(200, self.get_emit_status_code())

    def test_create(self):
        sockets.on_create(self.activity_for_create())
        self.assertEqual(200, self.get_emit_status_code())

    def test_message(self):
        self.create_and_join_room()
        sockets.on_message(self.activity_for_message())
        self.assertEqual(200, self.get_emit_status_code())

    def test_get_acl(self):
        self.create_and_join_room()
        sockets.on_get_acl(self.activity_for_get_acl())
        self.assertEqual(200, self.get_emit_status_code())

    def test_set_acl(self):
        self.create_and_join_room()
        self.set_owner()
        sockets.on_get_acl(self.activity_for_set_acl())
        self.assertEqual(200, self.get_emit_status_code())

    def test_list_rooms(self):
        sockets.on_list_rooms(self.activity_for_list_rooms())
        self.assertEqual(200, self.get_emit_status_code())

    def test_index_without_user_name_set(self):
        self.assertEqual('index.html', sockets.index())

    def test_index_with_user_name_set(self):
        self.set_session('field:User name', BaseTest.USER_NAME)
        self.assertEqual('.chat', sockets.index())

    def test_chat_without_user_id_set(self):
        self.remove_from_session(SessionKeys.user_id.value)
        self.assertEqual('.index', sockets.chat())

    def test_chat_with_user_id_set(self):
        self.set_session(SessionKeys.user_id.value, BaseTest.USER_ID)
        self.assertEqual('chat.html', sockets.chat())

    def test_clear_emit_args(self):
        sockets.on_join(self.activity_for_join())
        self.assertTrue(len(self.emit_args) > 0)
        self.clear_emit_args()
        self.assertTrue(len(self.emit_args) == 0)
