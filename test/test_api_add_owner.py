from test.utils import BaseTest


class ApiAddOwnerTest(BaseTest):
    def test_add_owner(self):
        self.create_and_join_room()
        self.set_owner()
        self.assert_add_succeeds()

    """
    def test_set_owner_when_not_owner(self):
        self.create_and_join_room()
        self.assert_add_fails()

    def test_set_owner_when_owner_but_room_doesnt_exist(self):
        self.set_owner()
        self.assert_add_fails()

    def test_set_owner_when_not_owner_and_room_doesnt_exist(self):
        self.assert_add_fails()
    """
